"""
Context management utilities for the AI Chatbot Integration Module.

This module provides functions for managing conversation context, including
context tracking, session management, and context-aware response generation.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

import redis
from fastapi import HTTPException, status

from core.config import settings
from ..config.settings import chatbot_settings

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize Redis client if available
redis_client = None
if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
    try:
        redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Redis client initialized for context management")
    except Exception as e:
        logger.error(f"Failed to initialize Redis client: {str(e)}")


class ContextManager:
    """
    Manager for conversation context.
    
    This class handles:
    - Storing and retrieving conversation context
    - Managing conversation sessions
    - Providing context-aware information for responses
    """
    
    def __init__(self, tenant_id: int, user_id: int):
        """
        Initialize the Context Manager.
        
        Args:
            tenant_id: The ID of the tenant
            user_id: The ID of the user
        """
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.session_ttl = chatbot_settings.CACHE_TTL_SECONDS
    
    def _get_session_key(self, session_id: str) -> str:
        """
        Get the Redis key for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            The Redis key
        """
        return f"chatbot:context:{self.tenant_id}:{self.user_id}:{session_id}"
    
    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get the context for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            The context data
        """
        if not redis_client or not chatbot_settings.ENABLE_CONTEXT_TRACKING:
            return {}
        
        try:
            key = self._get_session_key(session_id)
            context_data = redis_client.get(key)
            
            if context_data:
                return json.loads(context_data)
            
            return {}
            
        except Exception as e:
            logger.error(
                f"Error getting context: {str(e)}",
                extra={
                    "tenant_id": self.tenant_id,
                    "user_id": self.user_id,
                    "session_id": session_id
                },
                exc_info=True
            )
            return {}
    
    async def update_context(self, session_id: str, context_data: Dict[str, Any]) -> bool:
        """
        Update the context for a session.
        
        Args:
            session_id: The session ID
            context_data: The context data to store
            
        Returns:
            Whether the update was successful
        """
        if not redis_client or not chatbot_settings.ENABLE_CONTEXT_TRACKING:
            return False
        
        try:
            key = self._get_session_key(session_id)
            
            # Get existing context
            existing_context = await self.get_context(session_id)
            
            # Merge with new context
            merged_context = {**existing_context, **context_data}
            
            # Store the merged context
            redis_client.setex(
                key,
                self.session_ttl,
                json.dumps(merged_context)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Error updating context: {str(e)}",
                extra={
                    "tenant_id": self.tenant_id,
                    "user_id": self.user_id,
                    "session_id": session_id
                },
                exc_info=True
            )
            return False
    
    async def clear_context(self, session_id: str) -> bool:
        """
        Clear the context for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            Whether the clear was successful
        """
        if not redis_client or not chatbot_settings.ENABLE_CONTEXT_TRACKING:
            return False
        
        try:
            key = self._get_session_key(session_id)
            redis_client.delete(key)
            
            return True
            
        except Exception as e:
            logger.error(
                f"Error clearing context: {str(e)}",
                extra={
                    "tenant_id": self.tenant_id,
                    "user_id": self.user_id,
                    "session_id": session_id
                },
                exc_info=True
            )
            return False
    
    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the conversation history for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            The conversation history
        """
        context = await self.get_context(session_id)
        return context.get("conversation_history", [])
    
    async def add_to_conversation_history(
        self,
        session_id: str,
        query: str,
        response: str,
        max_history: int = 10
    ) -> bool:
        """
        Add a query-response pair to the conversation history.
        
        Args:
            session_id: The session ID
            query: The user query
            response: The chatbot response
            max_history: Maximum number of conversation turns to keep
            
        Returns:
            Whether the update was successful
        """
        if not redis_client or not chatbot_settings.ENABLE_CONTEXT_TRACKING:
            return False
        
        try:
            # Get existing context
            context = await self.get_context(session_id)
            
            # Get conversation history
            history = context.get("conversation_history", [])
            
            # Add new conversation turn
            history.append({
                "query": query,
                "response": response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Limit history size
            if len(history) > max_history:
                history = history[-max_history:]
            
            # Update context
            context["conversation_history"] = history
            
            # Store updated context
            return await self.update_context(session_id, context)
            
        except Exception as e:
            logger.error(
                f"Error adding to conversation history: {str(e)}",
                extra={
                    "tenant_id": self.tenant_id,
                    "user_id": self.user_id,
                    "session_id": session_id
                },
                exc_info=True
            )
            return False
    
    async def get_entity_memory(self, session_id: str) -> Dict[str, Any]:
        """
        Get the entity memory for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            The entity memory
        """
        context = await self.get_context(session_id)
        return context.get("entity_memory", {})
    
    async def update_entity_memory(
        self,
        session_id: str,
        entity_type: str,
        entity_value: str,
        entity_data: Dict[str, Any]
    ) -> bool:
        """
        Update the entity memory for a session.
        
        Args:
            session_id: The session ID
            entity_type: The type of entity
            entity_value: The value of the entity
            entity_data: The data to store for the entity
            
        Returns:
            Whether the update was successful
        """
        if not redis_client or not chatbot_settings.ENABLE_CONTEXT_TRACKING:
            return False
        
        try:
            # Get existing context
            context = await self.get_context(session_id)
            
            # Get entity memory
            entity_memory = context.get("entity_memory", {})
            
            # Update entity memory
            if entity_type not in entity_memory:
                entity_memory[entity_type] = {}
            
            entity_memory[entity_type][entity_value] = {
                **entity_data,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Update context
            context["entity_memory"] = entity_memory
            
            # Store updated context
            return await self.update_context(session_id, context)
            
        except Exception as e:
            logger.error(
                f"Error updating entity memory: {str(e)}",
                extra={
                    "tenant_id": self.tenant_id,
                    "user_id": self.user_id,
                    "session_id": session_id,
                    "entity_type": entity_type,
                    "entity_value": entity_value
                },
                exc_info=True
            )
            return False
