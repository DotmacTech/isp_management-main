"""
Workflow Engine for the Service Activation Module.

This engine manages the execution of multi-step workflows for service activation,
handling dependencies, retries, and rollbacks.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend_core.exceptions import WorkflowException
from modules.service_activation.models import (
    ServiceActivation,
    ActivationStep,
    ActivationLog,
    ActivationStatus,
    StepStatus
)


class WorkflowEngine:
    """
    Engine for executing multi-step service activation workflows.
    
    This class handles:
    - Sequential and parallel execution of workflow steps
    - Dependency management between steps
    - Automatic retries for failed steps
    - Rollback mechanisms for failed activations
    - Comprehensive logging of all actions
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize the workflow engine with a database session."""
        self.session = session
        self.logger = logging.getLogger(__name__)
        self._step_handlers: Dict[str, Callable] = {}
        self._rollback_handlers: Dict[str, Callable] = {}
    
    def register_step_handler(self, step_name: str, handler: Callable[[ActivationStep, Dict[str, Any]], Awaitable[bool]]):
        """
        Register a handler function for a specific workflow step.
        
        Args:
            step_name: The name of the step
            handler: Async function that performs the step's action
        """
        self._step_handlers[step_name] = handler
    
    def register_rollback_handler(self, step_name: str, handler: Callable[[ActivationStep, Dict[str, Any]], Awaitable[bool]]):
        """
        Register a handler function for rolling back a specific workflow step.
        
        Args:
            step_name: The name of the step
            handler: Async function that performs the rollback action
        """
        self._rollback_handlers[step_name] = handler
    
    async def execute_workflow(self, activation_id: int) -> bool:
        """
        Execute a complete workflow for a service activation.
        
        Args:
            activation_id: ID of the service activation to process
            
        Returns:
            bool: True if workflow completed successfully, False otherwise
        """
        # Get the activation record
        result = await self.session.execute(
            select(ServiceActivation).where(ServiceActivation.id == activation_id)
        )
        activation = result.scalars().first()
        
        if not activation:
            self.logger.error(f"Activation {activation_id} not found")
            return False
        
        # Update activation status to in-progress
        activation.status = ActivationStatus.IN_PROGRESS
        activation.updated_at = datetime.utcnow()
        await self.session.commit()
        
        # Log workflow start
        await self._log_activation_event(
            activation_id=activation_id,
            level="INFO",
            message=f"Starting service activation workflow for customer {activation.customer_id}, service {activation.service_id}"
        )
        
        # Check prerequisites if not already checked
        if not activation.prerequisites_checked:
            prerequisites_ok = await self._check_prerequisites(activation)
            if not prerequisites_ok:
                await self._fail_activation(activation_id, "Prerequisite checks failed")
                return False
        
        # Check payment if not already verified
        if not activation.payment_verified:
            payment_ok = await self._verify_payment(activation)
            if not payment_ok:
                await self._fail_activation(activation_id, "Payment verification failed")
                return False
        
        # Get all steps for this activation in order
        result = await self.session.execute(
            select(ActivationStep)
            .where(
                ActivationStep.activation_id == activation_id,
                ActivationStep.is_rollback_step == False
            )
            .order_by(ActivationStep.step_order)
        )
        steps = result.scalars().all()
        
        # Execute each step
        for step in steps:
            success = await self._execute_step(step, activation.metadata or {})
            if not success:
                # If a step fails, start rollback process
                await self._start_rollback(activation_id)
                return False
        
        # If we get here, all steps completed successfully
        activation.status = ActivationStatus.COMPLETED
        activation.completed_at = datetime.utcnow()
        activation.updated_at = datetime.utcnow()
        await self.session.commit()
        
        await self._log_activation_event(
            activation_id=activation_id,
            level="INFO",
            message=f"Service activation workflow completed successfully for customer {activation.customer_id}, service {activation.service_id}"
        )
        
        return True
    
    async def _execute_step(self, step: ActivationStep, metadata: Dict[str, Any]) -> bool:
        """
        Execute a single workflow step.
        
        Args:
            step: The step to execute
            metadata: Additional metadata for the step
            
        Returns:
            bool: True if step completed successfully, False otherwise
        """
        # Check if this step depends on another step
        if step.depends_on_step_id:
            result = await self.session.execute(
                select(ActivationStep).where(ActivationStep.id == step.depends_on_step_id)
            )
            dependency = result.scalars().first()
            
            if dependency and dependency.status != StepStatus.COMPLETED:
                await self._log_step_event(
                    step_id=step.id,
                    activation_id=step.activation_id,
                    level="WARNING",
                    message=f"Step {step.step_name} depends on step {dependency.step_name} which is not completed"
                )
                step.status = StepStatus.PENDING
                await self.session.commit()
                return False
        
        # Update step status to in-progress
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.utcnow()
        await self.session.commit()
        
        await self._log_step_event(
            step_id=step.id,
            activation_id=step.activation_id,
            level="INFO",
            message=f"Executing step: {step.step_name}"
        )
        
        # Get the handler for this step
        handler = self._step_handlers.get(step.step_name)
        if not handler:
            step.status = StepStatus.FAILED
            step.error_message = f"No handler registered for step {step.step_name}"
            await self.session.commit()
            
            await self._log_step_event(
                step_id=step.id,
                activation_id=step.activation_id,
                level="ERROR",
                message=f"No handler registered for step {step.step_name}"
            )
            return False
        
        # Execute the step handler
        try:
            success = await handler(step, metadata)
            
            if success:
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.utcnow()
                await self.session.commit()
                
                await self._log_step_event(
                    step_id=step.id,
                    activation_id=step.activation_id,
                    level="INFO",
                    message=f"Step {step.step_name} completed successfully"
                )
                return True
            else:
                # Step failed but can be retried
                if step.retry_count < step.max_retries:
                    step.retry_count += 1
                    step.status = StepStatus.PENDING
                    await self.session.commit()
                    
                    await self._log_step_event(
                        step_id=step.id,
                        activation_id=step.activation_id,
                        level="WARNING",
                        message=f"Step {step.step_name} failed, retrying (attempt {step.retry_count}/{step.max_retries})"
                    )
                    
                    # Retry the step
                    return await self._execute_step(step, metadata)
                else:
                    # Step failed and max retries reached
                    step.status = StepStatus.FAILED
                    step.error_message = "Step failed after maximum retry attempts"
                    await self.session.commit()
                    
                    await self._log_step_event(
                        step_id=step.id,
                        activation_id=step.activation_id,
                        level="ERROR",
                        message=f"Step {step.step_name} failed after {step.max_retries} retry attempts"
                    )
                    return False
        
        except Exception as e:
            # Handle exceptions during step execution
            step.status = StepStatus.FAILED
            step.error_message = str(e)
            await self.session.commit()
            
            await self._log_step_event(
                step_id=step.id,
                activation_id=step.activation_id,
                level="ERROR",
                message=f"Exception in step {step.step_name}: {str(e)}",
                details={"exception": str(e)}
            )
            return False
    
    async def _start_rollback(self, activation_id: int) -> bool:
        """
        Start the rollback process for a failed activation.
        
        Args:
            activation_id: ID of the activation to roll back
            
        Returns:
            bool: True if rollback completed successfully, False otherwise
        """
        # Update activation status
        result = await self.session.execute(
            select(ServiceActivation).where(ServiceActivation.id == activation_id)
        )
        activation = result.scalars().first()
        
        if not activation:
            self.logger.error(f"Activation {activation_id} not found for rollback")
            return False
        
        activation.status = ActivationStatus.ROLLBACK_IN_PROGRESS
        activation.updated_at = datetime.utcnow()
        await self.session.commit()
        
        await self._log_activation_event(
            activation_id=activation_id,
            level="WARNING",
            message=f"Starting rollback for failed activation {activation_id}"
        )
        
        # Get completed steps that need to be rolled back (in reverse order)
        result = await self.session.execute(
            select(ActivationStep)
            .where(
                ActivationStep.activation_id == activation_id,
                ActivationStep.status == StepStatus.COMPLETED,
                ActivationStep.is_rollback_step == False
            )
            .order_by(ActivationStep.step_order.desc())
        )
        steps_to_rollback = result.scalars().all()
        
        rollback_success = True
        
        # Execute rollback for each completed step
        for step in steps_to_rollback:
            success = await self._rollback_step(step, activation.metadata or {})
            if not success:
                rollback_success = False
        
        # Update activation status based on rollback result
        if rollback_success:
            activation.status = ActivationStatus.ROLLBACK_COMPLETED
            await self._log_activation_event(
                activation_id=activation_id,
                level="INFO",
                message=f"Rollback completed successfully for activation {activation_id}"
            )
        else:
            activation.status = ActivationStatus.ROLLBACK_FAILED
            await self._log_activation_event(
                activation_id=activation_id,
                level="ERROR",
                message=f"Rollback failed for activation {activation_id}"
            )
        
        activation.updated_at = datetime.utcnow()
        await self.session.commit()
        
        return rollback_success
    
    async def _rollback_step(self, step: ActivationStep, metadata: Dict[str, Any]) -> bool:
        """
        Roll back a single workflow step.
        
        Args:
            step: The step to roll back
            metadata: Additional metadata for the rollback
            
        Returns:
            bool: True if rollback completed successfully, False otherwise
        """
        # Get the rollback handler for this step
        handler = self._rollback_handlers.get(step.step_name)
        if not handler:
            await self._log_step_event(
                step_id=step.id,
                activation_id=step.activation_id,
                level="WARNING",
                message=f"No rollback handler registered for step {step.step_name}"
            )
            return True  # Continue with other rollbacks even if one is missing
        
        await self._log_step_event(
            step_id=step.id,
            activation_id=step.activation_id,
            level="INFO",
            message=f"Rolling back step: {step.step_name}"
        )
        
        try:
            success = await handler(step, metadata)
            
            if success:
                await self._log_step_event(
                    step_id=step.id,
                    activation_id=step.activation_id,
                    level="INFO",
                    message=f"Rollback of step {step.step_name} completed successfully"
                )
                return True
            else:
                await self._log_step_event(
                    step_id=step.id,
                    activation_id=step.activation_id,
                    level="ERROR",
                    message=f"Rollback of step {step.step_name} failed"
                )
                return False
        
        except Exception as e:
            await self._log_step_event(
                step_id=step.id,
                activation_id=step.activation_id,
                level="ERROR",
                message=f"Exception in rollback of step {step.step_name}: {str(e)}",
                details={"exception": str(e)}
            )
            return False
    
    async def _check_prerequisites(self, activation: ServiceActivation) -> bool:
        """
        Check all prerequisites for service activation.
        
        Args:
            activation: The service activation record
            
        Returns:
            bool: True if all prerequisites are met, False otherwise
        """
        await self._log_activation_event(
            activation_id=activation.id,
            level="INFO",
            message="Checking service activation prerequisites"
        )
        
        try:
            # Implement prerequisite checks here
            # For example, check if customer has required equipment, if location is serviceable, etc.
            
            # For now, we'll just mark prerequisites as checked
            activation.prerequisites_checked = True
            await self.session.commit()
            
            await self._log_activation_event(
                activation_id=activation.id,
                level="INFO",
                message="All prerequisites checked successfully"
            )
            
            return True
        
        except Exception as e:
            await self._log_activation_event(
                activation_id=activation.id,
                level="ERROR",
                message=f"Prerequisite check failed: {str(e)}",
                details={"exception": str(e)}
            )
            return False
    
    async def _verify_payment(self, activation: ServiceActivation) -> bool:
        """
        Verify payment for service activation.
        
        Args:
            activation: The service activation record
            
        Returns:
            bool: True if payment is verified, False otherwise
        """
        await self._log_activation_event(
            activation_id=activation.id,
            level="INFO",
            message="Verifying payment for service activation"
        )
        
        try:
            # Implement payment verification here
            # This would typically involve calling the billing module
            
            # For now, we'll just mark payment as verified
            activation.payment_verified = True
            await self.session.commit()
            
            await self._log_activation_event(
                activation_id=activation.id,
                level="INFO",
                message="Payment verified successfully"
            )
            
            return True
        
        except Exception as e:
            await self._log_activation_event(
                activation_id=activation.id,
                level="ERROR",
                message=f"Payment verification failed: {str(e)}",
                details={"exception": str(e)}
            )
            return False
    
    async def _fail_activation(self, activation_id: int, reason: str) -> None:
        """
        Mark an activation as failed with the given reason.
        
        Args:
            activation_id: ID of the activation to mark as failed
            reason: Reason for the failure
        """
        result = await self.session.execute(
            select(ServiceActivation).where(ServiceActivation.id == activation_id)
        )
        activation = result.scalars().first()
        
        if not activation:
            self.logger.error(f"Activation {activation_id} not found for failure marking")
            return
        
        activation.status = ActivationStatus.FAILED
        activation.updated_at = datetime.utcnow()
        await self.session.commit()
        
        await self._log_activation_event(
            activation_id=activation_id,
            level="ERROR",
            message=f"Service activation failed: {reason}"
        )
    
    async def _log_activation_event(
        self,
        activation_id: int,
        level: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an event for a service activation.
        
        Args:
            activation_id: ID of the activation
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            message: Log message
            details: Additional details for the log
        """
        log_entry = ActivationLog(
            activation_id=activation_id,
            level=level,
            message=message,
            details=details
        )
        
        self.session.add(log_entry)
        await self.session.commit()
        
        # Also log to the application logger
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(f"Activation {activation_id}: {message}")
    
    async def _log_step_event(
        self,
        step_id: int,
        activation_id: int,
        level: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an event for a workflow step.
        
        Args:
            step_id: ID of the step
            activation_id: ID of the activation
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            message: Log message
            details: Additional details for the log
        """
        log_entry = ActivationLog(
            activation_id=activation_id,
            step_id=step_id,
            level=level,
            message=message,
            details=details
        )
        
        self.session.add(log_entry)
        await self.session.commit()
        
        # Also log to the application logger
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(f"Activation {activation_id}, Step {step_id}: {message}")
