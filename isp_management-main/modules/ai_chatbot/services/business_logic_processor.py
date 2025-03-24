"""
Business Logic Processor for the AI Chatbot Integration Module.

This service translates AI interpretations into platform actions, interacts with
relevant modules, and manages conversation context.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.config import settings
from core.metrics import MetricsCollector
from core.security import get_current_user
from ..models.chatbot import ChatbotQuery, ChatbotAction
from ..schemas.chatbot import (
    AIModelResponse, ChatbotResponse, SuggestedAction,
    ChatbotQueryCreate, ChatbotActionCreate
)

# Initialize metrics collector
metrics = MetricsCollector("ai_chatbot.business_logic_processor")

# Initialize logger
logger = logging.getLogger(__name__)


class BusinessLogicProcessor:
    """
    Business Logic Processor for the AI Chatbot.
    
    This class handles:
    - Translating AI interpretations into platform actions
    - Interacting with relevant modules (Billing, Customer Management, etc.)
    - Managing conversation context
    - Generating structured responses
    """
    
    def __init__(self, db: Session):
        """Initialize the Business Logic Processor."""
        self.db = db
        
        # Module connectors - these will be initialized on demand
        self._customer_connector = None
        self._billing_connector = None
        self._radius_connector = None
        self._crm_connector = None
    
    async def process_intent(
        self, 
        ai_response: AIModelResponse,
        query: ChatbotQueryCreate,
        user_id: int,
        tenant_id: int,
        processing_time_ms: float,
        ai_service_name: str,
        ai_model_version: Optional[str] = None
    ) -> Tuple[ChatbotResponse, ChatbotQuery]:
        """
        Process the intent from an AI response and generate a structured response.
        
        Args:
            ai_response: The response from the AI service
            query: The original query
            user_id: The ID of the user making the query
            tenant_id: The ID of the tenant
            processing_time_ms: The processing time in milliseconds
            ai_service_name: The name of the AI service used
            ai_model_version: The version of the AI model used
            
        Returns:
            Tuple[ChatbotResponse, ChatbotQuery]: The structured response and the stored query
        """
        try:
            # Store the query in the database
            db_query = ChatbotQuery(
                user_id=user_id,
                tenant_id=tenant_id,
                query_text=query.query,
                response_text=ai_response.response,
                context_data=query.context,
                intent=ai_response.intent,
                confidence_score=ai_response.confidence,
                entities=json.loads(json.dumps([entity.dict() for entity in ai_response.entities])),
                processing_time_ms=int(processing_time_ms),
                ai_service_name=ai_service_name,
                ai_model_version=ai_model_version,
                is_successful=True
            )
            self.db.add(db_query)
            self.db.commit()
            self.db.refresh(db_query)
            
            # Process the intent and generate a structured response
            structured_data, suggested_actions = await self._get_structured_data_for_intent(
                ai_response.intent,
                ai_response.entities,
                query.context,
                db_query.id
            )
            
            # Create the response
            response = ChatbotResponse(
                response=ai_response.response,
                data=structured_data,
                follow_up_questions=ai_response.suggested_queries or [],
                suggested_actions=suggested_actions,
                intent=ai_response.intent,
                confidence_score=ai_response.confidence,
                entities=ai_response.entities,
                processing_time_ms=int(processing_time_ms),
                query_id=db_query.id
            )
            
            # Record metrics
            metrics.increment(
                "intent_processed",
                tags={
                    "tenant_id": str(tenant_id),
                    "intent": ai_response.intent,
                    "has_structured_data": "true" if structured_data else "false",
                    "has_suggested_actions": "true" if suggested_actions else "false"
                }
            )
            
            return response, db_query
            
        except Exception as e:
            logger.error(
                f"Error processing intent: {str(e)}",
                extra={
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "intent": ai_response.intent,
                    "query": query.query
                },
                exc_info=True
            )
            
            # If we've already created a query record, update it with the error
            if 'db_query' in locals() and db_query.id:
                db_query.is_successful = False
                db_query.error_message = str(e)
                self.db.commit()
            
            # Record metrics
            metrics.increment(
                "intent_processing_error",
                tags={
                    "tenant_id": str(tenant_id),
                    "intent": ai_response.intent
                }
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing intent: {str(e)}"
            )
    
    async def _get_structured_data_for_intent(
        self,
        intent: str,
        entities: List[Any],
        context: Optional[Dict[str, Any]],
        query_id: int
    ) -> Tuple[Optional[Dict[str, Any]], List[SuggestedAction]]:
        """
        Get structured data and suggested actions for an intent.
        
        Args:
            intent: The intent from the AI service
            entities: The entities extracted from the query
            context: The context of the query
            query_id: The ID of the stored query
            
        Returns:
            Tuple[Optional[Dict[str, Any]], List[SuggestedAction]]: 
                The structured data and suggested actions
        """
        # Initialize empty results
        structured_data = None
        suggested_actions = []
        
        # Extract entity values for easier access
        entity_values = {
            entity.entity_type: entity.value for entity in entities
        }
        
        # Process different intents
        if intent.startswith("customer_"):
            structured_data, actions = await self._process_customer_intent(
                intent, entity_values, context, query_id
            )
            suggested_actions.extend(actions)
            
        elif intent.startswith("billing_"):
            structured_data, actions = await self._process_billing_intent(
                intent, entity_values, context, query_id
            )
            suggested_actions.extend(actions)
            
        elif intent.startswith("service_"):
            structured_data, actions = await self._process_service_intent(
                intent, entity_values, context, query_id
            )
            suggested_actions.extend(actions)
            
        elif intent.startswith("ticket_"):
            structured_data, actions = await self._process_ticket_intent(
                intent, entity_values, context, query_id
            )
            suggested_actions.extend(actions)
            
        # Record the action in the database if we have structured data
        if structured_data:
            action_type = intent.split("_")[0]
            module_name = self._get_module_name_for_intent(intent)
            
            db_action = ChatbotAction(
                query_id=query_id,
                action_type=action_type,
                module_name=module_name,
                parameters=entity_values,
                result=structured_data,
                is_successful=True
            )
            self.db.add(db_action)
            self.db.commit()
        
        return structured_data, suggested_actions
    
    def _get_module_name_for_intent(self, intent: str) -> str:
        """
        Get the module name for an intent.
        
        Args:
            intent: The intent from the AI service
            
        Returns:
            str: The module name
        """
        if intent.startswith("customer_"):
            return "customer_management"
        elif intent.startswith("billing_"):
            return "billing"
        elif intent.startswith("service_"):
            return "radius"
        elif intent.startswith("ticket_"):
            return "crm"
        else:
            return "unknown"
    
    async def _process_customer_intent(
        self,
        intent: str,
        entity_values: Dict[str, str],
        context: Optional[Dict[str, Any]],
        query_id: int
    ) -> Tuple[Optional[Dict[str, Any]], List[SuggestedAction]]:
        """
        Process customer-related intents.
        
        Args:
            intent: The intent from the AI service
            entity_values: The extracted entity values
            context: The context of the query
            query_id: The ID of the stored query
            
        Returns:
            Tuple[Optional[Dict[str, Any]], List[SuggestedAction]]: 
                The structured data and suggested actions
        """
        # Initialize the customer connector if needed
        if not self._customer_connector:
            # This would be a proper connector to the Customer Management Module
            # For now, we'll just simulate it
            pass
        
        structured_data = None
        suggested_actions = []
        
        # Process different customer intents
        if intent == "customer_info":
            # Get customer information
            customer_id = entity_values.get("customer_id") or context.get("customer_id")
            if customer_id:
                # In a real implementation, this would call the Customer Management Module
                structured_data = {
                    "customer_id": customer_id,
                    "name": f"Simulated Customer {customer_id}",
                    "email": f"customer{customer_id}@example.com",
                    "phone": f"+1234567890{customer_id}",
                    "status": "active"
                }
                
                # Add suggested actions
                suggested_actions.append(
                    SuggestedAction(
                        action_type="view",
                        module="billing",
                        description="View billing history",
                        endpoint=f"/api/billing/customers/{customer_id}/history",
                        parameters={"customer_id": customer_id}
                    )
                )
                suggested_actions.append(
                    SuggestedAction(
                        action_type="view",
                        module="radius",
                        description="Check service status",
                        endpoint=f"/api/radius/customers/{customer_id}/services",
                        parameters={"customer_id": customer_id}
                    )
                )
        
        elif intent == "customer_search":
            # Search for customers
            search_term = entity_values.get("search_term")
            if search_term:
                # In a real implementation, this would call the Customer Management Module
                structured_data = {
                    "results": [
                        {
                            "customer_id": "123",
                            "name": f"Simulated Customer 123",
                            "email": "customer123@example.com",
                            "match_field": "name"
                        },
                        {
                            "customer_id": "456",
                            "name": f"Simulated Customer 456",
                            "email": "customer456@example.com",
                            "match_field": "email"
                        }
                    ],
                    "count": 2,
                    "search_term": search_term
                }
                
                # Add suggested actions
                for result in structured_data["results"]:
                    suggested_actions.append(
                        SuggestedAction(
                            action_type="view",
                            module="customer_management",
                            description=f"View customer {result['name']}",
                            endpoint=f"/api/customers/{result['customer_id']}",
                            parameters={"customer_id": result["customer_id"]}
                        )
                    )
        
        return structured_data, suggested_actions
    
    async def _process_billing_intent(
        self,
        intent: str,
        entity_values: Dict[str, str],
        context: Optional[Dict[str, Any]],
        query_id: int
    ) -> Tuple[Optional[Dict[str, Any]], List[SuggestedAction]]:
        """
        Process billing-related intents.
        
        Args:
            intent: The intent from the AI service
            entity_values: The extracted entity values
            context: The context of the query
            query_id: The ID of the stored query
            
        Returns:
            Tuple[Optional[Dict[str, Any]], List[SuggestedAction]]: 
                The structured data and suggested actions
        """
        # Initialize the billing connector if needed
        if not self._billing_connector:
            # This would be a proper connector to the Billing Module
            # For now, we'll just simulate it
            pass
        
        structured_data = None
        suggested_actions = []
        
        # Process different billing intents
        if intent == "billing_history":
            # Get billing history
            customer_id = entity_values.get("customer_id") or context.get("customer_id")
            if customer_id:
                # In a real implementation, this would call the Billing Module
                structured_data = {
                    "customer_id": customer_id,
                    "invoices": [
                        {
                            "invoice_id": "INV-001",
                            "date": "2025-02-01",
                            "amount": 49.99,
                            "status": "paid"
                        },
                        {
                            "invoice_id": "INV-002",
                            "date": "2025-03-01",
                            "amount": 49.99,
                            "status": "due"
                        }
                    ],
                    "total_paid": 49.99,
                    "total_due": 49.99
                }
                
                # Add suggested actions
                suggested_actions.append(
                    SuggestedAction(
                        action_type="view",
                        module="billing",
                        description="View latest invoice",
                        endpoint=f"/api/billing/invoices/INV-002",
                        parameters={"invoice_id": "INV-002"}
                    )
                )
                suggested_actions.append(
                    SuggestedAction(
                        action_type="create",
                        module="billing",
                        description="Create payment",
                        endpoint=f"/api/billing/customers/{customer_id}/payments",
                        parameters={"customer_id": customer_id, "amount": 49.99},
                        requires_confirmation=True
                    )
                )
        
        return structured_data, suggested_actions
    
    async def _process_service_intent(
        self,
        intent: str,
        entity_values: Dict[str, str],
        context: Optional[Dict[str, Any]],
        query_id: int
    ) -> Tuple[Optional[Dict[str, Any]], List[SuggestedAction]]:
        """
        Process service-related intents.
        
        Args:
            intent: The intent from the AI service
            entity_values: The extracted entity values
            context: The context of the query
            query_id: The ID of the stored query
            
        Returns:
            Tuple[Optional[Dict[str, Any]], List[SuggestedAction]]: 
                The structured data and suggested actions
        """
        # Initialize the radius connector if needed
        if not self._radius_connector:
            # This would be a proper connector to the RADIUS Module
            # For now, we'll just simulate it
            pass
        
        structured_data = None
        suggested_actions = []
        
        # Process different service intents
        if intent == "service_status":
            # Get service status
            customer_id = entity_values.get("customer_id") or context.get("customer_id")
            if customer_id:
                # In a real implementation, this would call the RADIUS Module
                structured_data = {
                    "customer_id": customer_id,
                    "services": [
                        {
                            "service_id": "SVC-001",
                            "type": "internet",
                            "plan": "50 Mbps",
                            "status": "active",
                            "last_online": "2025-03-15T05:45:12Z",
                            "ip_address": "192.168.1.100"
                        }
                    ],
                    "active_count": 1,
                    "suspended_count": 0
                }
                
                # Add suggested actions
                suggested_actions.append(
                    SuggestedAction(
                        action_type="update",
                        module="radius",
                        description="Reset connection",
                        endpoint=f"/api/radius/services/SVC-001/reset",
                        parameters={"service_id": "SVC-001"},
                        requires_confirmation=True
                    )
                )
                suggested_actions.append(
                    SuggestedAction(
                        action_type="view",
                        module="radius",
                        description="View usage statistics",
                        endpoint=f"/api/radius/services/SVC-001/usage",
                        parameters={"service_id": "SVC-001"}
                    )
                )
        
        return structured_data, suggested_actions
    
    async def _process_ticket_intent(
        self,
        intent: str,
        entity_values: Dict[str, str],
        context: Optional[Dict[str, Any]],
        query_id: int
    ) -> Tuple[Optional[Dict[str, Any]], List[SuggestedAction]]:
        """
        Process ticket-related intents.
        
        Args:
            intent: The intent from the AI service
            entity_values: The extracted entity values
            context: The context of the query
            query_id: The ID of the stored query
            
        Returns:
            Tuple[Optional[Dict[str, Any]], List[SuggestedAction]]: 
                The structured data and suggested actions
        """
        # Initialize the CRM connector if needed
        if not self._crm_connector:
            # This would be a proper connector to the CRM Module
            # For now, we'll just simulate it
            pass
        
        structured_data = None
        suggested_actions = []
        
        # Process different ticket intents
        if intent == "ticket_history":
            # Get ticket history
            customer_id = entity_values.get("customer_id") or context.get("customer_id")
            if customer_id:
                # In a real implementation, this would call the CRM Module
                structured_data = {
                    "customer_id": customer_id,
                    "tickets": [
                        {
                            "ticket_id": "TKT-001",
                            "subject": "Internet connection issue",
                            "status": "closed",
                            "created_at": "2025-02-20T14:30:00Z",
                            "closed_at": "2025-02-21T09:15:00Z"
                        },
                        {
                            "ticket_id": "TKT-002",
                            "subject": "Billing inquiry",
                            "status": "open",
                            "created_at": "2025-03-14T16:45:00Z",
                            "closed_at": None
                        }
                    ],
                    "open_count": 1,
                    "closed_count": 1
                }
                
                # Add suggested actions
                suggested_actions.append(
                    SuggestedAction(
                        action_type="view",
                        module="crm",
                        description="View open ticket",
                        endpoint=f"/api/crm/tickets/TKT-002",
                        parameters={"ticket_id": "TKT-002"}
                    )
                )
                suggested_actions.append(
                    SuggestedAction(
                        action_type="create",
                        module="crm",
                        description="Create new ticket",
                        endpoint=f"/api/crm/customers/{customer_id}/tickets",
                        parameters={"customer_id": customer_id},
                        requires_confirmation=True
                    )
                )
        
        return structured_data, suggested_actions
