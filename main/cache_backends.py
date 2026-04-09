"""
Custom Cache Backends with Redis Connection Error Handling

This module provides a Redis cache backend wrapper that gracefully handles
connection errors, allowing the application to continue functioning even when
Redis is unavailable.
"""

import logging
import socket
from django.core.cache.backends.redis import RedisCache
from django.core.cache.backends.base import DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)

# Try to import redis exceptions for better error detection
try:
    import redis.exceptions as redis_exceptions
    CONNECTION_ERRORS = (socket.gaierror, OSError, redis_exceptions.ConnectionError, redis_exceptions.TimeoutError)
except ImportError:
    CONNECTION_ERRORS = (socket.gaierror, OSError)


class ResilientRedisCache(RedisCache):
    """
    Redis cache backend that gracefully handles connection errors.
    
    When Redis is unavailable, cache operations will:
    - Return None for cache.get() calls (cache miss)
    - Silently fail for cache.set() and cache.delete() calls
    - Log warnings about cache unavailability
    
    This allows the application to continue functioning without Redis,
    though caching features will be disabled until Redis is restored.
    """
    
    def __init__(self, server, params):
        """Initialize the cache backend"""
        super().__init__(server, params)
        self._connection_error = False
    
    def _handle_connection_error(self, operation, key=None):
        """
        Handle Redis connection errors gracefully
        
        Args:
            operation: The cache operation being performed ('get', 'set', 'delete', etc.)
            key: Optional cache key being accessed
        """
        if not self._connection_error:
            # Only log the first error to avoid log spam
            logger.warning(
                f"Redis cache unavailable for {operation} operation"
                + (f" (key: {key})" if key else "")
                + ". Application will continue without caching."
            )
            self._connection_error = True
    
    def _reset_connection_error(self):
        """Reset connection error flag when connection is restored"""
        if self._connection_error:
            logger.info("Redis cache connection restored")
            self._connection_error = False
    
    def get(self, key, default=None, version=None):
        """
        Get a value from cache, handling connection errors gracefully
        
        Returns default value if Redis is unavailable
        """
        try:
            self._reset_connection_error()
            return super().get(key, default, version)
        except CONNECTION_ERRORS as e:
            # Handle connection errors gracefully
            self._handle_connection_error('get', key)
            return default
        except Exception as e:
            # Check if it's a connection error by string matching (fallback)
            error_str = str(e).lower()
            if 'connection' in error_str or 'redis' in error_str or 'gaierror' in error_str:
                self._handle_connection_error('get', key)
                return default
            # Re-raise non-connection errors
            raise
    
    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Set a value in cache, handling connection errors gracefully
        
        Silently fails if Redis is unavailable
        """
        try:
            self._reset_connection_error()
            return super().set(key, value, timeout, version)
        except CONNECTION_ERRORS as e:
            # Handle connection errors gracefully
            self._handle_connection_error('set', key)
            return False
        except Exception as e:
            # Check if it's a connection error by string matching (fallback)
            error_str = str(e).lower()
            if 'connection' in error_str or 'redis' in error_str or 'gaierror' in error_str:
                self._handle_connection_error('set', key)
                return False
            # Re-raise non-connection errors
            raise
    
    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Add a value to cache only if key doesn't exist, handling connection errors gracefully
        
        Silently fails if Redis is unavailable (returns False)
        """
        try:
            self._reset_connection_error()
            return super().add(key, value, timeout, version)
        except Exception as e:
            # Check if it's a connection error - catch all exceptions and check
            error_str = str(e).lower()
            error_type = type(e).__name__.lower()
            error_repr = repr(e).lower()
            
            # Check if it's a known connection error type
            is_connection_error = (
                isinstance(e, CONNECTION_ERRORS) or
                any(keyword in error_str for keyword in [
                    'connection', 'redis', 'gaierror', 'temporary failure', 
                    'name resolution', 'error -3', 'connecting to'
                ]) or
                any(keyword in error_type for keyword in ['connection', 'gaierror', 'oserror']) or
                any(keyword in error_repr for keyword in ['connection', 'redis', 'gaierror'])
            )
            
            if is_connection_error:
                self._handle_connection_error('add', key)
                return False
            
            # Re-raise non-connection errors
            raise
    
    def delete(self, key, version=None):
        """
        Delete a value from cache, handling connection errors gracefully
        
        Silently fails if Redis is unavailable
        """
        try:
            self._reset_connection_error()
            return super().delete(key, version)
        except CONNECTION_ERRORS as e:
            # Handle connection errors gracefully
            self._handle_connection_error('delete', key)
            return False
        except Exception as e:
            # Check if it's a connection error by string matching (fallback)
            error_str = str(e).lower()
            if 'connection' in error_str or 'redis' in error_str or 'gaierror' in error_str:
                self._handle_connection_error('delete', key)
                return False
            # Re-raise non-connection errors
            raise
    
    def get_many(self, keys, version=None):
        """
        Get multiple values from cache, handling connection errors gracefully
        
        Returns a dict with only successfully retrieved keys if Redis is unavailable
        """
        try:
            self._reset_connection_error()
            return super().get_many(keys, version)
        except CONNECTION_ERRORS as e:
            # Handle connection errors gracefully
            self._handle_connection_error('get_many', str(keys))
            return {}
        except Exception as e:
            # Check if it's a connection error by string matching (fallback)
            error_str = str(e).lower()
            if 'connection' in error_str or 'redis' in error_str or 'gaierror' in error_str:
                self._handle_connection_error('get_many', str(keys))
                return {}
            # Re-raise non-connection errors
            raise
    
    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Set multiple values in cache, handling connection errors gracefully
        
        Silently fails if Redis is unavailable
        """
        try:
            self._reset_connection_error()
            return super().set_many(data, timeout, version)
        except CONNECTION_ERRORS as e:
            # Handle connection errors gracefully
            self._handle_connection_error('set_many', str(list(data.keys())))
            return []
        except Exception as e:
            # Check if it's a connection error by string matching (fallback)
            error_str = str(e).lower()
            if 'connection' in error_str or 'redis' in error_str or 'gaierror' in error_str:
                self._handle_connection_error('set_many', str(list(data.keys())))
                return []
            # Re-raise non-connection errors
            raise
    
    def delete_many(self, keys, version=None):
        """
        Delete multiple values from cache, handling connection errors gracefully
        
        Silently fails if Redis is unavailable
        """
        try:
            self._reset_connection_error()
            return super().delete_many(keys, version)
        except CONNECTION_ERRORS as e:
            # Handle connection errors gracefully
            self._handle_connection_error('delete_many', str(keys))
            return False
        except Exception as e:
            # Check if it's a connection error by string matching (fallback)
            error_str = str(e).lower()
            if 'connection' in error_str or 'redis' in error_str or 'gaierror' in error_str:
                self._handle_connection_error('delete_many', str(keys))
                return False
            # Re-raise non-connection errors
            raise
    
    def clear(self):
        """
        Clear all cache, handling connection errors gracefully
        
        Silently fails if Redis is unavailable
        """
        try:
            self._reset_connection_error()
            return super().clear()
        except CONNECTION_ERRORS as e:
            # Handle connection errors gracefully
            self._handle_connection_error('clear')
            return False
        except Exception as e:
            # Check if it's a connection error by string matching (fallback)
            error_str = str(e).lower()
            if 'connection' in error_str or 'redis' in error_str or 'gaierror' in error_str:
                self._handle_connection_error('clear')
                return False
            # Re-raise non-connection errors
            raise
    
    def has_key(self, key, version=None):
        """
        Check if a key exists in cache, handling connection errors gracefully
        
        Returns False if Redis is unavailable
        """
        try:
            self._reset_connection_error()
            return super().has_key(key, version)
        except CONNECTION_ERRORS as e:
            # Handle connection errors gracefully
            self._handle_connection_error('has_key', key)
            return False
        except Exception as e:
            # Check if it's a connection error by string matching (fallback)
            error_str = str(e).lower()
            if 'connection' in error_str or 'redis' in error_str or 'gaierror' in error_str:
                self._handle_connection_error('has_key', key)
                return False
            # Re-raise non-connection errors
            raise
    
    def incr(self, key, delta=1, version=None):
        """
        Increment a cache value, handling connection errors gracefully
        
        Returns None if Redis is unavailable
        """
        try:
            self._reset_connection_error()
            return super().incr(key, delta, version)
        except CONNECTION_ERRORS as e:
            # Handle connection errors gracefully
            self._handle_connection_error('incr', key)
            return None
        except Exception as e:
            # Check if it's a connection error by string matching (fallback)
            error_str = str(e).lower()
            if 'connection' in error_str or 'redis' in error_str or 'gaierror' in error_str:
                self._handle_connection_error('incr', key)
                return None
            # Re-raise non-connection errors
            raise
    
    def decr(self, key, delta=1, version=None):
        """
        Decrement a cache value, handling connection errors gracefully
        
        Returns None if Redis is unavailable
        """
        try:
            self._reset_connection_error()
            return super().decr(key, delta, version)
        except CONNECTION_ERRORS as e:
            # Handle connection errors gracefully
            self._handle_connection_error('decr', key)
            return None
        except Exception as e:
            # Check if it's a connection error by string matching (fallback)
            error_str = str(e).lower()
            if 'connection' in error_str or 'redis' in error_str or 'gaierror' in error_str:
                self._handle_connection_error('decr', key)
                return None
            # Re-raise non-connection errors
            raise

