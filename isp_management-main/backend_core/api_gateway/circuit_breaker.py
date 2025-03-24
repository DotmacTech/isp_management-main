"""
Circuit breaker implementation for the API Gateway.

This module provides circuit breaking functionality to prevent cascading failures
during service outages by temporarily disabling calls to failing services.
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from redis.exceptions import RedisError
from backend_core.cache import redis_client


class CircuitState(str, Enum):
    """Possible states for a circuit breaker."""
    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Service unavailable, requests blocked
    HALF_OPEN = "half_open"  # Testing if service is back, limited requests


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    path: str
    failure_threshold: int
    recovery_time: int  # in seconds


@dataclass
class CircuitBreakerMetrics:
    """Metrics for a circuit breaker."""
    path: str
    state: CircuitState
    failure_count: int
    last_failure_time: Optional[float]
    success_count: int
    failure_threshold: int
    recovery_time: int


class CircuitBreaker:
    """
    Circuit breaker for preventing cascading failures.
    
    This class implements the circuit breaker pattern to temporarily disable
    calls to failing services, allowing them time to recover.
    """
    
    def __init__(self):
        """Initialize the circuit breaker."""
        self.logger = logging.getLogger("circuit_breaker")
        self.redis = redis_client
        self.configs: Dict[str, CircuitBreakerConfig] = {}
        
        # In-memory storage for when Redis is not available
        self.memory_states: Dict[str, CircuitState] = {}
        self.memory_failure_counts: Dict[str, int] = {}
        self.memory_last_failure_times: Dict[str, float] = {}
        self.memory_success_counts: Dict[str, int] = {}
        
        # Default configuration
        self.default_failure_threshold = 5
        self.default_recovery_time = 60  # 1 minute
    
    def configure(self, path: str, failure_threshold: int, recovery_time: int):
        """
        Configure a circuit breaker for a specific path.
        
        Args:
            path: The API path to protect
            failure_threshold: Number of failures before opening circuit
            recovery_time: Time in seconds before attempting recovery
        """
        self.configs[path] = CircuitBreakerConfig(
            path=path,
            failure_threshold=failure_threshold,
            recovery_time=recovery_time
        )
    
    def is_service_available(self, path: str) -> bool:
        """
        Check if a service is available based on circuit breaker state.
        
        Args:
            path: The API path being requested
            
        Returns:
            bool: True if the service is available, False if the circuit is open
        """
        # Get the circuit state
        state = self._get_circuit_state(path)
        
        if state == CircuitState.CLOSED:
            # Circuit is closed, service is available
            return True
        
        if state == CircuitState.OPEN:
            # Circuit is open, check if recovery time has elapsed
            last_failure_time = self._get_last_failure_time(path)
            config = self._get_config(path)
            
            if last_failure_time and (time.time() - last_failure_time) > config.recovery_time:
                # Recovery time has elapsed, transition to half-open
                self._set_circuit_state(path, CircuitState.HALF_OPEN)
                self.logger.info(f"Circuit for {path} transitioning from OPEN to HALF_OPEN")
                return True
            
            # Still in recovery period
            return False
        
        if state == CircuitState.HALF_OPEN:
            # In half-open state, allow a test request
            return True
        
        # Default to available if state is unknown
        return True
    
    async def check_circuit(self, path: str) -> bool:
        """
        Asynchronous version of is_service_available for compatibility with tests.
        
        Args:
            path: The API path being requested
            
        Returns:
            bool: True if the service is available, False if the circuit is open
        """
        return self.is_service_available(path)
    
    def record_success(self, path: str):
        """
        Record a successful request to a service.
        
        Args:
            path: The API path that was successfully called
        """
        state = self._get_circuit_state(path)
        
        if state == CircuitState.HALF_OPEN:
            # Service is recovering, close the circuit
            self._set_circuit_state(path, CircuitState.CLOSED)
            self._reset_failure_count(path)
            self.logger.info(f"Circuit for {path} closed after successful request in HALF_OPEN state")
        
        # Increment success count for metrics
        self._increment_success_count(path)
    
    def record_failure(self, path: str):
        """
        Record a failed request to a service.
        
        Args:
            path: The API path that failed
        """
        state = self._get_circuit_state(path)
        config = self._get_config(path)
        
        # Update last failure time
        self._set_last_failure_time(path, time.time())
        
        if state == CircuitState.HALF_OPEN:
            # Service is still failing during recovery, back to open
            self._set_circuit_state(path, CircuitState.OPEN)
            self.logger.warning(f"Circuit for {path} reopened after failure in HALF_OPEN state")
            return
        
        # Increment failure count
        failure_count = self._increment_failure_count(path)
        
        if state == CircuitState.CLOSED and failure_count >= config.failure_threshold:
            # Too many failures, open the circuit
            self._set_circuit_state(path, CircuitState.OPEN)
            self.logger.warning(f"Circuit for {path} opened after {failure_count} failures")
    
    def get_metrics(self) -> List[CircuitBreakerMetrics]:
        """
        Get metrics for all circuit breakers.
        
        Returns:
            List[CircuitBreakerMetrics]: Circuit breaker metrics
        """
        metrics = []
        
        # Get all paths with circuit breaker activity
        all_paths = set(self.configs.keys())
        
        # Add paths from Redis if available
        if self.redis:
            try:
                for key in self.redis.keys("circuit_breaker:*:state"):
                    path = key.split(":")[1]
                    all_paths.add(path)
            except RedisError as e:
                self.logger.warning(f"Failed to get circuit breaker keys from Redis: {e}")
        
        # Add paths from in-memory storage
        all_paths.update(self.memory_states.keys())
        
        # Build metrics for each path
        for path in all_paths:
            config = self._get_config(path)
            state = self._get_circuit_state(path)
            failure_count = self._get_failure_count(path)
            last_failure_time = self._get_last_failure_time(path)
            success_count = self._get_success_count(path)
            
            metrics.append(CircuitBreakerMetrics(
                path=path,
                state=state,
                failure_count=failure_count,
                last_failure_time=last_failure_time,
                success_count=success_count,
                failure_threshold=config.failure_threshold,
                recovery_time=config.recovery_time
            ))
        
        return metrics
    
    def _get_config(self, path: str) -> CircuitBreakerConfig:
        """Get the configuration for a path."""
        # Check for exact path match
        if path in self.configs:
            return self.configs[path]
        
        # Check for prefix matches
        for config_path, config in self.configs.items():
            if path.startswith(config_path):
                return config
        
        # Use default configuration
        return CircuitBreakerConfig(
            path=path,
            failure_threshold=self.default_failure_threshold,
            recovery_time=self.default_recovery_time
        )
    
    def _get_circuit_state(self, path: str) -> CircuitState:
        """Get the current state of a circuit."""
        # Try Redis first if available
        if self.redis:
            try:
                state_key = f"circuit_breaker:{path}:state"
                state = self.redis.get(state_key)
                if state:
                    return CircuitState(state)
            except RedisError as e:
                self.logger.warning(f"Failed to get circuit state from Redis: {e}")
        
        # Fall back to in-memory storage
        return self.memory_states.get(path, CircuitState.CLOSED)
    
    def _set_circuit_state(self, path: str, state: CircuitState):
        """Set the state of a circuit."""
        # Try Redis first if available
        if self.redis:
            try:
                state_key = f"circuit_breaker:{path}:state"
                self.redis.set(state_key, state.value)
            except RedisError as e:
                self.logger.warning(f"Failed to set circuit state in Redis: {e}")
        
        # Always update in-memory storage
        self.memory_states[path] = state
    
    def _get_failure_count(self, path: str) -> int:
        """Get the current failure count for a path."""
        # Try Redis first if available
        if self.redis:
            try:
                count_key = f"circuit_breaker:{path}:failure_count"
                count = self.redis.get(count_key)
                if count is not None:
                    return int(count)
            except RedisError as e:
                self.logger.warning(f"Failed to get failure count from Redis: {e}")
        
        # Fall back to in-memory storage
        return self.memory_failure_counts.get(path, 0)
    
    def _increment_failure_count(self, path: str) -> int:
        """Increment the failure count for a path and return the new count."""
        # Try Redis first if available
        if self.redis:
            try:
                count_key = f"circuit_breaker:{path}:failure_count"
                count = self.redis.incr(count_key)
                # Update in-memory storage for consistency
                self.memory_failure_counts[path] = int(count)
                return int(count)
            except RedisError as e:
                self.logger.warning(f"Failed to increment failure count in Redis: {e}")
        
        # Fall back to in-memory storage
        current_count = self.memory_failure_counts.get(path, 0)
        new_count = current_count + 1
        self.memory_failure_counts[path] = new_count
        return new_count
    
    def _reset_failure_count(self, path: str):
        """Reset the failure count for a path."""
        # Try Redis first if available
        if self.redis:
            try:
                count_key = f"circuit_breaker:{path}:failure_count"
                self.redis.set(count_key, 0)
            except RedisError as e:
                self.logger.warning(f"Failed to reset failure count in Redis: {e}")
        
        # Always update in-memory storage
        self.memory_failure_counts[path] = 0
    
    def _get_last_failure_time(self, path: str) -> Optional[float]:
        """Get the timestamp of the last failure for a path."""
        # Try Redis first if available
        if self.redis:
            try:
                time_key = f"circuit_breaker:{path}:last_failure_time"
                time_str = self.redis.get(time_key)
                if time_str:
                    return float(time_str)
            except RedisError as e:
                self.logger.warning(f"Failed to get last failure time from Redis: {e}")
        
        # Fall back to in-memory storage
        return self.memory_last_failure_times.get(path)
    
    def _set_last_failure_time(self, path: str, timestamp: float):
        """Set the timestamp of the last failure for a path."""
        # Try Redis first if available
        if self.redis:
            try:
                time_key = f"circuit_breaker:{path}:last_failure_time"
                self.redis.set(time_key, str(timestamp))
            except RedisError as e:
                self.logger.warning(f"Failed to set last failure time in Redis: {e}")
        
        # Always update in-memory storage
        self.memory_last_failure_times[path] = timestamp
    
    def _get_success_count(self, path: str) -> int:
        """Get the success count for a path."""
        # Try Redis first if available
        if self.redis:
            try:
                success_key = f"circuit_breaker:{path}:success_count"
                count = self.redis.get(success_key)
                if count is not None:
                    return int(count)
            except RedisError as e:
                self.logger.warning(f"Failed to get success count from Redis: {e}")
        
        # Fall back to in-memory storage
        return self.memory_success_counts.get(path, 0)
    
    def _increment_success_count(self, path: str) -> int:
        """Increment the success count for a path and return the new count."""
        # Try Redis first if available
        if self.redis:
            try:
                success_key = f"circuit_breaker:{path}:success_count"
                count = self.redis.incr(success_key)
                # Update in-memory storage for consistency
                self.memory_success_counts[path] = int(count)
                return int(count)
            except RedisError as e:
                self.logger.warning(f"Failed to increment success count in Redis: {e}")
        
        # Fall back to in-memory storage
        current_count = self.memory_success_counts.get(path, 0)
        new_count = current_count + 1
        self.memory_success_counts[path] = new_count
        return new_count
