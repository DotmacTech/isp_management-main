"""
Tests for the Circuit Breaker component of the API Gateway.

This module contains tests for the CircuitBreaker class, which prevents
cascading failures during service outages by temporarily disabling calls
to failing services.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch

from backend_core.api_gateway.circuit_breaker import CircuitBreaker, CircuitState


@pytest.fixture
def circuit_breaker():
    """Create a CircuitBreaker instance for testing."""
    return CircuitBreaker()


class TestCircuitBreaker:
    """Tests for the CircuitBreaker class."""
    
    def test_initialization(self):
        """Test CircuitBreaker initialization."""
        breaker = CircuitBreaker()
        assert hasattr(breaker, 'configs')
        assert breaker.configs == {}
        assert hasattr(breaker, 'memory_states')
        assert breaker.memory_states == {}
        assert hasattr(breaker, 'memory_failure_counts')
        assert breaker.memory_failure_counts == {}
    
    def test_configure(self, circuit_breaker):
        """Test configuring a circuit breaker for a path."""
        path = "/api/test"
        threshold = 5
        recovery_time = 30
        
        circuit_breaker.configure(path, threshold, recovery_time)
        
        assert path in circuit_breaker.configs
        assert circuit_breaker.configs[path].failure_threshold == threshold
        assert circuit_breaker.configs[path].recovery_time == recovery_time
    
    def test_record_success(self, circuit_breaker):
        """Test recording a successful request."""
        path = "/api/test"
        
        # Configure circuit breaker
        circuit_breaker.configure(path, 5, 30)
        
        # Add some failures
        circuit_breaker.memory_failure_counts[path] = 3
        
        # Record a success
        circuit_breaker.record_success(path)
        
        # Check that success was recorded
        assert circuit_breaker._get_success_count(path) == 1
    
    def test_record_failure(self, circuit_breaker):
        """Test recording a failed request."""
        path = "/api/test"
        
        # Configure circuit breaker
        circuit_breaker.configure(path, 5, 30)
        
        # Record a failure
        circuit_breaker.record_failure(path)
        
        # Check that failure was recorded
        assert circuit_breaker._get_failure_count(path) == 1
        assert circuit_breaker._get_last_failure_time(path) is not None
        
        # Record more failures to reach the threshold
        for _ in range(4):
            circuit_breaker.record_failure(path)
        
        # Check that circuit is open
        assert circuit_breaker._get_circuit_state(path) == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_check_circuit_closed(self, circuit_breaker):
        """Test checking a closed circuit."""
        path = "/api/test"
        
        # Configure circuit breaker
        circuit_breaker.configure(path, 5, 30)
        
        # Check availability
        is_available = circuit_breaker.is_service_available(path)
        
        # Circuit should be closed by default
        assert is_available is True
        assert circuit_breaker._get_circuit_state(path) == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_check_circuit_open(self, circuit_breaker):
        """Test checking an open circuit."""
        path = "/api/test"
        
        # Configure circuit breaker
        circuit_breaker.configure(path, 5, 30)
        
        # Record failures to open the circuit
        for _ in range(5):
            circuit_breaker.record_failure(path)
        
        # Check availability
        is_available = circuit_breaker.is_service_available(path)
        
        # Circuit should be open
        assert is_available is False
        assert circuit_breaker._get_circuit_state(path) == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_recovery(self, circuit_breaker):
        """Test circuit recovery after recovery time."""
        path = "/api/test"
        
        # Configure circuit breaker with short recovery time
        circuit_breaker.configure(path, 5, 1)  # 1 second recovery
        
        # Record failures to open the circuit
        for _ in range(5):
            circuit_breaker.record_failure(path)
        
        # Circuit should be open
        assert circuit_breaker.is_service_available(path) is False
        
        # Wait for recovery time
        await asyncio.sleep(1.1)
        
        # Circuit should transition to half-open
        is_available = circuit_breaker.is_service_available(path)
        assert is_available is True
        assert circuit_breaker._get_circuit_state(path) == CircuitState.HALF_OPEN
        
        # Record a success to close the circuit
        circuit_breaker.record_success(path)
        
        # Circuit should be closed
        assert circuit_breaker._get_circuit_state(path) == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_check_circuit_no_config(self, circuit_breaker):
        """Test checking circuit with no configuration."""
        path = "/api/test"
        
        # No configuration for this path
        is_available = circuit_breaker.is_service_available(path)
        
        # Default should be available
        assert is_available is True
    
    def test_get_metrics(self, circuit_breaker):
        """Test getting circuit breaker metrics."""
        # Configure some circuit breakers
        circuit_breaker.configure("/api/test1", 5, 30)
        circuit_breaker.configure("/api/test2", 10, 60)
        
        # Add some failures
        circuit_breaker.memory_failure_counts["/api/test1"] = 3
        circuit_breaker._set_last_failure_time("/api/test1", time.time())
        
        # Get metrics
        metrics = circuit_breaker.get_metrics()
        
        # Check metrics
        assert len(metrics) == 2
        
        # Find metrics for /api/test1
        test1_metrics = next(m for m in metrics if m.path == "/api/test1")
        assert test1_metrics.failure_count == 3
        assert test1_metrics.failure_threshold == 5
        assert test1_metrics.recovery_time == 30
        
        # Find metrics for /api/test2
        test2_metrics = next(m for m in metrics if m.path == "/api/test2")
        assert test2_metrics.failure_count == 0
        assert test2_metrics.failure_threshold == 10
        assert test2_metrics.recovery_time == 60
