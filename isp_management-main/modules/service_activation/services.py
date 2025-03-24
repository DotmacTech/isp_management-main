"""
Service layer for the Service Activation Module.

This module contains the business logic for service activation, including
integration with other modules like Billing, RADIUS, and Customer Management.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from backend_core.exceptions import ServiceException, NotFoundException
from modules.service_activation.models import (
    ServiceActivation,
    ActivationStep,
    ActivationStatus,
    StepStatus
)
from modules.service_activation.schemas import (
    ServiceActivationCreate,
    ServiceActivationUpdate,
    WorkflowDefinition,
    PrerequisiteCheckResult
)
from modules.service_activation.workflow_engine import WorkflowEngine


class ActivationService:
    """
    Service for managing service activations.
    
    This class provides methods for:
    - Creating and managing service activations
    - Defining and executing workflows
    - Integrating with other modules (Billing, RADIUS, Customer)
    - Handling notifications for activation events
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize the activation service with a database session."""
        self.session = session
        self.logger = logging.getLogger(__name__)
        self.workflow_engine = WorkflowEngine(session)
        
        # Register step handlers
        self._register_workflow_handlers()
    
    def _register_workflow_handlers(self):
        """Register handlers for all workflow steps."""
        # Payment verification
        self.workflow_engine.register_step_handler(
            "verify_payment", self._handle_payment_verification
        )
        self.workflow_engine.register_rollback_handler(
            "verify_payment", self._rollback_payment_verification
        )
        
        # RADIUS account creation
        self.workflow_engine.register_step_handler(
            "create_radius_account", self._handle_radius_account_creation
        )
        self.workflow_engine.register_rollback_handler(
            "create_radius_account", self._rollback_radius_account_creation
        )
        
        # NAS configuration
        self.workflow_engine.register_step_handler(
            "configure_nas", self._handle_nas_configuration
        )
        self.workflow_engine.register_rollback_handler(
            "configure_nas", self._rollback_nas_configuration
        )
        
        # Service provisioning
        self.workflow_engine.register_step_handler(
            "provision_service", self._handle_service_provisioning
        )
        self.workflow_engine.register_rollback_handler(
            "provision_service", self._rollback_service_provisioning
        )
        
        # Customer notification
        self.workflow_engine.register_step_handler(
            "notify_customer", self._handle_customer_notification
        )
        self.workflow_engine.register_rollback_handler(
            "notify_customer", self._rollback_customer_notification
        )
        
        # Update customer status
        self.workflow_engine.register_step_handler(
            "update_customer_status", self._handle_customer_status_update
        )
        self.workflow_engine.register_rollback_handler(
            "update_customer_status", self._rollback_customer_status_update
        )
    
    async def create_activation(
        self, activation_data: ServiceActivationCreate
    ) -> ServiceActivation:
        """
        Create a new service activation.
        
        Args:
            activation_data: Data for the new activation
            
        Returns:
            The created ServiceActivation instance
        """
        # Create the activation record
        activation = ServiceActivation(
            customer_id=activation_data.customer_id,
            service_id=activation_data.service_id,
            tariff_id=activation_data.tariff_id,
            status=ActivationStatus.PENDING,
            metadata=activation_data.metadata
        )
        
        self.session.add(activation)
        await self.session.commit()
        await self.session.refresh(activation)
        
        # Create the workflow steps
        workflow = await self._get_workflow_for_service(activation_data.service_id)
        
        for i, step_def in enumerate(workflow.steps):
            step = ActivationStep(
                activation_id=activation.id,
                step_name=step_def["name"],
                step_order=i,
                description=step_def.get("description"),
                max_retries=step_def.get("max_retries", 3),
                depends_on_step_id=step_def.get("depends_on")
            )
            self.session.add(step)
        
        # Add rollback steps if defined
        if workflow.rollback_steps:
            for i, step_def in enumerate(workflow.rollback_steps):
                step = ActivationStep(
                    activation_id=activation.id,
                    step_name=step_def["name"],
                    step_order=i,
                    description=step_def.get("description"),
                    max_retries=step_def.get("max_retries", 3),
                    is_rollback_step=True,
                    depends_on_step_id=step_def.get("depends_on")
                )
                self.session.add(step)
        
        await self.session.commit()
        
        return activation
    
    async def get_activation(self, activation_id: int) -> ServiceActivation:
        """
        Get a service activation by ID.
        
        Args:
            activation_id: ID of the activation to retrieve
            
        Returns:
            The ServiceActivation instance
            
        Raises:
            NotFoundException: If the activation is not found
        """
        result = await self.session.execute(
            select(ServiceActivation).where(ServiceActivation.id == activation_id)
        )
        activation = result.scalars().first()
        
        if not activation:
            raise NotFoundException(f"Service activation with ID {activation_id} not found")
        
        return activation
    
    async def update_activation(
        self, activation_id: int, update_data: ServiceActivationUpdate
    ) -> ServiceActivation:
        """
        Update a service activation.
        
        Args:
            activation_id: ID of the activation to update
            update_data: Data to update
            
        Returns:
            The updated ServiceActivation instance
            
        Raises:
            NotFoundException: If the activation is not found
        """
        activation = await self.get_activation(activation_id)
        
        # Update fields
        if update_data.status is not None:
            activation.status = update_data.status
        
        if update_data.payment_verified is not None:
            activation.payment_verified = update_data.payment_verified
        
        if update_data.prerequisites_checked is not None:
            activation.prerequisites_checked = update_data.prerequisites_checked
        
        if update_data.metadata is not None:
            activation.metadata = update_data.metadata
        
        activation.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(activation)
        
        return activation
    
    async def delete_activation(self, activation_id: int) -> None:
        """
        Delete a service activation.
        
        Args:
            activation_id: ID of the activation to delete
            
        Raises:
            NotFoundException: If the activation is not found
        """
        activation = await self.get_activation(activation_id)
        
        await self.session.delete(activation)
        await self.session.commit()
    
    async def start_activation(self, activation_id: int) -> bool:
        """
        Start the activation workflow.
        
        Args:
            activation_id: ID of the activation to start
            
        Returns:
            bool: True if the workflow started successfully, False otherwise
            
        Raises:
            NotFoundException: If the activation is not found
            ServiceException: If the activation is not in a valid state
        """
        activation = await self.get_activation(activation_id)
        
        if activation.status != ActivationStatus.PENDING:
            raise ServiceException(
                f"Cannot start activation with status {activation.status}. Must be PENDING."
            )
        
        # Execute the workflow asynchronously
        return await self.workflow_engine.execute_workflow(activation_id)
    
    async def check_prerequisites(self, activation_id: int) -> PrerequisiteCheckResult:
        """
        Check prerequisites for a service activation.
        
        Args:
            activation_id: ID of the activation to check
            
        Returns:
            PrerequisiteCheckResult: Result of the prerequisite check
            
        Raises:
            NotFoundException: If the activation is not found
        """
        activation = await self.get_activation(activation_id)
        
        # Implement prerequisite checks here
        # This could include checking customer eligibility, location serviceability, etc.
        
        # For now, we'll return a simple success result
        return PrerequisiteCheckResult(
            passed=True,
            message="All prerequisites checked successfully"
        )
    
    async def get_activation_steps(self, activation_id: int) -> List[ActivationStep]:
        """
        Get all steps for a service activation.
        
        Args:
            activation_id: ID of the activation
            
        Returns:
            List of ActivationStep instances
            
        Raises:
            NotFoundException: If the activation is not found
        """
        # Verify activation exists
        await self.get_activation(activation_id)
        
        result = await self.session.execute(
            select(ActivationStep)
            .where(ActivationStep.activation_id == activation_id)
            .order_by(ActivationStep.step_order)
        )
        
        return result.scalars().all()
    
    async def get_customer_activations(self, customer_id: int) -> List[ServiceActivation]:
        """
        Get all activations for a customer.
        
        Args:
            customer_id: ID of the customer
            
        Returns:
            List of ServiceActivation instances
        """
        result = await self.session.execute(
            select(ServiceActivation)
            .where(ServiceActivation.customer_id == customer_id)
            .order_by(ServiceActivation.created_at.desc())
        )
        
        return result.scalars().all()
    
    async def _get_workflow_for_service(self, service_id: int) -> WorkflowDefinition:
        """
        Get the workflow definition for a service.
        
        Args:
            service_id: ID of the service
            
        Returns:
            WorkflowDefinition for the service
        """
        # In a real implementation, this would fetch the workflow from a database
        # or configuration based on the service type
        
        # For now, we'll return a default workflow
        return WorkflowDefinition(
            name="Standard Service Activation",
            description="Standard workflow for activating ISP services",
            steps=[
                {
                    "name": "verify_payment",
                    "description": "Verify payment for the service",
                    "max_retries": 3
                },
                {
                    "name": "create_radius_account",
                    "description": "Create RADIUS account for the customer",
                    "max_retries": 3,
                    "depends_on": None  # This will be set to the ID of the verify_payment step
                },
                {
                    "name": "configure_nas",
                    "description": "Configure network access server",
                    "max_retries": 2,
                    "depends_on": None  # This will be set to the ID of the create_radius_account step
                },
                {
                    "name": "provision_service",
                    "description": "Provision the service",
                    "max_retries": 3,
                    "depends_on": None  # This will be set to the ID of the configure_nas step
                },
                {
                    "name": "update_customer_status",
                    "description": "Update customer status to active",
                    "max_retries": 3,
                    "depends_on": None  # This will be set to the ID of the provision_service step
                },
                {
                    "name": "notify_customer",
                    "description": "Send activation notification to customer",
                    "max_retries": 3,
                    "depends_on": None  # This will be set to the ID of the update_customer_status step
                }
            ],
            rollback_steps=[
                {
                    "name": "notify_customer",
                    "description": "Send activation failure notification to customer",
                    "max_retries": 3
                },
                {
                    "name": "update_customer_status",
                    "description": "Revert customer status",
                    "max_retries": 3
                },
                {
                    "name": "provision_service",
                    "description": "Deprovision the service",
                    "max_retries": 3
                },
                {
                    "name": "configure_nas",
                    "description": "Remove NAS configuration",
                    "max_retries": 2
                },
                {
                    "name": "create_radius_account",
                    "description": "Remove RADIUS account",
                    "max_retries": 3
                },
                {
                    "name": "verify_payment",
                    "description": "Refund payment if necessary",
                    "max_retries": 3
                }
            ]
        )
    
    # Step handlers
    
    async def _handle_payment_verification(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Handle payment verification step."""
        self.logger.info(f"Verifying payment for activation {step.activation_id}")
        
        # In a real implementation, this would call the billing module
        # to verify payment for the service
        
        # For now, we'll simulate success
        return True
    
    async def _rollback_payment_verification(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Rollback payment verification step."""
        self.logger.info(f"Rolling back payment for activation {step.activation_id}")
        
        # In a real implementation, this would call the billing module
        # to refund the payment if necessary
        
        # For now, we'll simulate success
        return True
    
    async def _handle_radius_account_creation(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Handle RADIUS account creation step."""
        self.logger.info(f"Creating RADIUS account for activation {step.activation_id}")
        
        # In a real implementation, this would call the RADIUS module
        # to create a user account
        
        # For now, we'll simulate success
        return True
    
    async def _rollback_radius_account_creation(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Rollback RADIUS account creation step."""
        self.logger.info(f"Removing RADIUS account for activation {step.activation_id}")
        
        # In a real implementation, this would call the RADIUS module
        # to remove the user account
        
        # For now, we'll simulate success
        return True
    
    async def _handle_nas_configuration(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Handle NAS configuration step."""
        self.logger.info(f"Configuring NAS for activation {step.activation_id}")
        
        # In a real implementation, this would call the NAS module
        # to configure the network access server
        
        # For now, we'll simulate success
        return True
    
    async def _rollback_nas_configuration(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Rollback NAS configuration step."""
        self.logger.info(f"Removing NAS configuration for activation {step.activation_id}")
        
        # In a real implementation, this would call the NAS module
        # to remove the configuration
        
        # For now, we'll simulate success
        return True
    
    async def _handle_service_provisioning(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Handle service provisioning step."""
        self.logger.info(f"Provisioning service for activation {step.activation_id}")
        
        # In a real implementation, this would call the appropriate service module
        # to provision the service
        
        # For now, we'll simulate success
        return True
    
    async def _rollback_service_provisioning(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Rollback service provisioning step."""
        self.logger.info(f"Deprovisioning service for activation {step.activation_id}")
        
        # In a real implementation, this would call the appropriate service module
        # to deprovision the service
        
        # For now, we'll simulate success
        return True
    
    async def _handle_customer_notification(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Handle customer notification step."""
        self.logger.info(f"Sending notification for activation {step.activation_id}")
        
        # In a real implementation, this would call the notification module
        # to send an email, SMS, or other notification to the customer
        
        # For now, we'll simulate success
        return True
    
    async def _rollback_customer_notification(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Rollback customer notification step."""
        self.logger.info(f"Sending failure notification for activation {step.activation_id}")
        
        # In a real implementation, this would call the notification module
        # to send a failure notification
        
        # For now, we'll simulate success
        return True
    
    async def _handle_customer_status_update(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Handle customer status update step."""
        self.logger.info(f"Updating customer status for activation {step.activation_id}")
        
        # In a real implementation, this would call the customer module
        # to update the customer's status
        
        # For now, we'll simulate success
        return True
    
    async def _rollback_customer_status_update(
        self, step: ActivationStep, metadata: Dict[str, Any]
    ) -> bool:
        """Rollback customer status update step."""
        self.logger.info(f"Reverting customer status for activation {step.activation_id}")
        
        # In a real implementation, this would call the customer module
        # to revert the customer's status
        
        # For now, we'll simulate success
        return True
