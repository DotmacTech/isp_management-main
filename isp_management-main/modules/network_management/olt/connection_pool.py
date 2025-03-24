"""
OLT Connection Pool Module

This module provides a connection pooling implementation for OLT adapters
to efficiently manage and reuse connections to OLT devices.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from .adapters.base import OLTAdapter
from .exceptions import PoolExhaustedError, OLTConnectionError

logger = logging.getLogger(__name__)

class ConnectionPoolItem:
    """
    Represents a connection in the connection pool.
    
    This class tracks the state of a connection, including when it was
    last used and whether it's currently in use.
    """
    
    def __init__(self, adapter: OLTAdapter):
        """
        Initialize a connection pool item.
        
        Args:
            adapter: The OLT adapter instance
        """
        self.adapter = adapter
        self.in_use = False
        self.last_used = time.time()
        self.created_at = time.time()
    
    def acquire(self) -> None:
        """Mark this connection as in use."""
        self.in_use = True
        self.last_used = time.time()
    
    def release(self) -> None:
        """Mark this connection as not in use."""
        self.in_use = False
        self.last_used = time.time()


class OLTConnectionPool:
    """
    Connection pool for OLT adapters.
    
    This class manages a pool of connections to OLT devices, allowing
    efficient reuse of connections and limiting the number of concurrent
    connections.
    """
    
    def __init__(self, factory_method: Callable[..., OLTAdapter], 
                max_connections: int = 10, 
                connection_timeout: int = 300,
                max_idle_time: int = 600):
        """
        Initialize the connection pool.
        
        Args:
            factory_method: Function that creates a new OLT adapter
            max_connections: Maximum number of connections in the pool
            connection_timeout: Timeout for acquiring a connection (seconds)
            max_idle_time: Maximum time a connection can be idle before being closed (seconds)
        """
        self.factory_method = factory_method
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.max_idle_time = max_idle_time
        self.pool: List[ConnectionPoolItem] = []
        self.lock = threading.RLock()
        self.cleanup_timer = None
        self._start_cleanup_timer()
    
    def _start_cleanup_timer(self) -> None:
        """Start a timer to periodically clean up idle connections."""
        self.cleanup_timer = threading.Timer(60.0, self._cleanup_idle_connections)
        self.cleanup_timer.daemon = True
        self.cleanup_timer.start()
    
    def _cleanup_idle_connections(self) -> None:
        """Clean up idle connections that have exceeded the max idle time."""
        try:
            with self.lock:
                current_time = time.time()
                idle_connections = [
                    conn for conn in self.pool 
                    if not conn.in_use and (current_time - conn.last_used) > self.max_idle_time
                ]
                
                for conn in idle_connections:
                    logger.info(f"Closing idle connection to {conn.adapter.__class__.__name__}")
                    try:
                        conn.adapter.disconnect()
                    except Exception as e:
                        logger.warning(f"Error disconnecting idle connection: {e}")
                    
                    self.pool.remove(conn)
        except Exception as e:
            logger.error(f"Error during idle connection cleanup: {e}")
        finally:
            # Schedule the next cleanup
            self._start_cleanup_timer()
    
    def get_connection(self, **kwargs) -> OLTAdapter:
        """
        Get a connection from the pool.
        
        If an idle connection is available, it will be returned.
        Otherwise, a new connection will be created if the pool is not full.
        If the pool is full, this method will wait for a connection to become
        available or until the timeout is reached.
        
        Args:
            **kwargs: Arguments to pass to the factory method when creating a new connection
            
        Returns:
            OLTAdapter: An OLT adapter instance
            
        Raises:
            PoolExhaustedError: If no connection could be acquired within the timeout
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                # Look for an available connection
                for conn in self.pool:
                    if not conn.in_use:
                        conn.acquire()
                        
                        # Ensure the connection is still valid
                        try:
                            if not conn.adapter.is_connected():
                                logger.info("Reconnecting stale connection")
                                conn.adapter.connect()
                        except Exception as e:
                            logger.warning(f"Error reconnecting: {e}")
                            # Create a new adapter instead
                            try:
                                conn.adapter = self.factory_method(**kwargs)
                                conn.adapter.connect()
                            except Exception as e2:
                                logger.error(f"Failed to create new connection: {e2}")
                                conn.release()
                                raise OLTConnectionError(f"Failed to establish connection: {e2}")
                        
                        return conn.adapter
                
                # If the pool is not full, create a new connection
                if len(self.pool) < self.max_connections:
                    try:
                        adapter = self.factory_method(**kwargs)
                        if not adapter.connect():
                            raise OLTConnectionError("Failed to connect to OLT device")
                        
                        conn = ConnectionPoolItem(adapter)
                        conn.acquire()
                        self.pool.append(conn)
                        return adapter
                    except Exception as e:
                        logger.error(f"Error creating new connection: {e}")
                        raise OLTConnectionError(f"Failed to establish connection: {e}")
            
            # Check if we've timed out
            if time.time() - start_time > self.connection_timeout:
                raise PoolExhaustedError(
                    f"Could not acquire connection within {self.connection_timeout} seconds"
                )
            
            # Wait a bit before trying again
            time.sleep(0.5)
    
    def release_connection(self, adapter: OLTAdapter) -> None:
        """
        Release a connection back to the pool.
        
        Args:
            adapter: The adapter to release
        """
        with self.lock:
            for conn in self.pool:
                if conn.adapter is adapter:
                    conn.release()
                    return
    
    def close_all_connections(self) -> None:
        """Close all connections in the pool."""
        with self.lock:
            for conn in self.pool:
                try:
                    conn.adapter.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting: {e}")
            
            self.pool.clear()
            
            if self.cleanup_timer:
                self.cleanup_timer.cancel()
                self.cleanup_timer = None
