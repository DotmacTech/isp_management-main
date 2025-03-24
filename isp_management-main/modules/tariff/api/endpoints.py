from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth_service import get_current_active_user
from .schemas import (
    TariffPlanCreate,
    TariffPlanResponse,
    TariffAssignmentCreate,
    TariffAssignmentResponse,
    FUPThresholdCheck,
    FUPThresholdResponse,
    UserTariffPlanCreate,
    UserTariffPlanUpdate,
    UserUsageRecordCreate,
    UsageCheckRequest,
    UsageCheckResponse,
    BandwidthPolicyResponse
)
from .services import TariffService
from backend_core.auth_service import has_role
from datetime import datetime

router = APIRouter(
    prefix="/tariff",
    tags=["tariff"],
    dependencies=[Depends(get_current_active_user)]
)

@router.post("/plans", response_model=TariffPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_tariff_plan(
    plan_data: TariffPlanCreate,
    db: Session = Depends(get_db)
):
    """Create a new tariff plan."""
    tariff_service = TariffService(db)
    return tariff_service.create_tariff_plan(plan_data)

@router.get("/plans/{plan_id}", response_model=TariffPlanResponse)
async def get_tariff_plan(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """Get tariff plan by ID."""
    tariff_service = TariffService(db)
    plan = tariff_service.get_tariff_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tariff plan not found"
        )
    return plan

@router.get("/plans", response_model=List[TariffPlanResponse])
async def get_all_active_plans(
    db: Session = Depends(get_db)
):
    """Get all active tariff plans."""
    tariff_service = TariffService(db)
    return tariff_service.get_all_active_plans()

@router.patch("/plans/{plan_id}", response_model=TariffPlanResponse)
async def update_tariff_plan(
    plan_id: int,
    plan_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update an existing tariff plan."""
    tariff_service = TariffService(db)
    return tariff_service.update_tariff_plan(plan_id, plan_data)

@router.post("/plans/{plan_id}/assign", response_model=Dict[str, Any], status_code=201)
async def assign_plan_to_user(
    plan_id: int,
    assignment_data: UserTariffPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Assign a tariff plan to a user.
    
    Requires admin or staff privileges.
    """
    if not has_role(current_user, ["admin", "staff"]):
        raise HTTPException(
            status_code=403, detail="Not authorized to assign tariff plans"
        )
    
    # Set the plan ID from the path parameter
    assignment_data.tariff_plan_id = plan_id
    
    # Set default start date if not provided
    if not assignment_data.start_date:
        assignment_data.start_date = datetime.utcnow()
    
    tariff_service = TariffService(db)
    user_plan = tariff_service.assign_plan_to_user(assignment_data)
    
    return {
        "status": "success",
        "message": "Plan assigned successfully",
        "user_plan_id": user_plan.id,
        "user_id": user_plan.user_id,
        "plan_id": user_plan.tariff_plan_id,
        "start_date": user_plan.start_date,
        "end_date": user_plan.end_date
    }

@router.get("/users/{user_id}/plan", response_model=Dict[str, Any])
async def get_user_plan(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the active tariff plan for a user.
    
    Users can only view their own plan unless they have admin or staff privileges.
    """
    if current_user.id != user_id and not has_role(current_user, ["admin", "staff"]):
        raise HTTPException(
            status_code=403, detail="Not authorized to view this user's tariff plan"
        )
    
    tariff_service = TariffService(db)
    user_plan = tariff_service.get_user_tariff_plan(user_id)
    
    if not user_plan:
        raise HTTPException(status_code=404, detail="No active tariff plan found for user")
    
    plan = tariff_service.get_tariff_plan(user_plan.tariff_plan_id)
    
    return {
        "user_id": user_id,
        "plan_id": plan.id,
        "plan_name": plan.name,
        "plan_description": plan.description,
        "price": plan.price,
        "billing_cycle": plan.billing_cycle,
        "download_speed": plan.download_speed,
        "upload_speed": plan.upload_speed,
        "data_cap": plan.data_cap,
        "data_used": user_plan.data_used,
        "percentage_used": tariff_service._calculate_percentage_used(user_plan.data_used, plan.data_cap),
        "is_throttled": user_plan.is_throttled,
        "status": user_plan.status,
        "current_cycle_start": user_plan.current_cycle_start,
        "current_cycle_end": user_plan.current_cycle_end
    }

@router.put("/users/{user_id}/plan/{plan_id}", response_model=Dict[str, Any])
async def update_user_plan(
    user_id: int,
    plan_id: int,
    update_data: UserTariffPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a user's tariff plan.
    
    Requires admin or staff privileges.
    """
    if not has_role(current_user, ["admin", "staff"]):
        raise HTTPException(
            status_code=403, detail="Not authorized to update tariff plans"
        )
    
    tariff_service = TariffService(db)
    user_plan = tariff_service.update_user_tariff_plan(plan_id, update_data)
    
    return {
        "status": "success",
        "message": "User tariff plan updated successfully",
        "user_plan_id": user_plan.id,
        "user_id": user_plan.user_id,
        "plan_id": user_plan.tariff_plan_id,
        "updated_fields": list(update_data.dict(exclude_unset=True).keys())
    }

@router.delete("/users/{user_id}/plan", response_model=Dict[str, Any])
async def cancel_user_plan(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Cancel a user's active tariff plan.
    
    Requires admin or staff privileges.
    """
    if not has_role(current_user, ["admin", "staff"]):
        raise HTTPException(
            status_code=403, detail="Not authorized to cancel tariff plans"
        )
    
    tariff_service = TariffService(db)
    result = tariff_service.cancel_user_tariff_plan(user_id)
    
    return {
        "status": "success",
        "message": "User tariff plan cancelled successfully",
        "user_id": user_id
    }

@router.post("/usage/record", response_model=Dict[str, Any])
async def record_usage(
    usage_data: UserUsageRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Record usage data for a user's tariff plan.
    
    This endpoint is typically called by the RADIUS accounting system.
    Requires admin, staff, or system privileges.
    """
    if not has_role(current_user, ["admin", "staff", "system"]):
        raise HTTPException(
            status_code=403, detail="Not authorized to record usage data"
        )
    
    # Set default timestamp if not provided
    if not usage_data.timestamp:
        usage_data.timestamp = datetime.utcnow()
    
    tariff_service = TariffService(db)
    usage_record = tariff_service.record_usage(usage_data)
    
    return {
        "status": "success",
        "message": "Usage data recorded successfully",
        "record_id": usage_record.id,
        "user_tariff_plan_id": usage_record.user_tariff_plan_id,
        "download_bytes": usage_record.download_bytes,
        "upload_bytes": usage_record.upload_bytes,
        "total_bytes": usage_record.total_bytes
    }

@router.post("/usage/check", response_model=UsageCheckResponse)
async def check_usage(
    check_data: UsageCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Check a user's usage against their plan limits.
    
    Users can only check their own usage unless they have admin or staff privileges.
    """
    if current_user.id != check_data.user_id and not has_role(current_user, ["admin", "staff", "system"]):
        raise HTTPException(
            status_code=403, detail="Not authorized to check this user's usage"
        )
    
    tariff_service = TariffService(db)
    return tariff_service.check_usage(check_data)

@router.get("/users/{user_id}/bandwidth-policy", response_model=BandwidthPolicyResponse)
async def get_bandwidth_policy(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the bandwidth policy for a user based on their tariff plan.
    
    This endpoint is typically called by the RADIUS authentication system.
    Requires admin, staff, or system privileges.
    """
    if not has_role(current_user, ["admin", "staff", "system"]) and current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view bandwidth policies"
        )
    
    tariff_service = TariffService(db)
    return tariff_service.get_bandwidth_policy(user_id)

@router.post("/users/{user_id}/reset-cycle", response_model=Dict[str, Any])
async def reset_usage_cycle(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Reset the usage cycle for a user's tariff plan.
    
    Requires admin or staff privileges.
    """
    if not has_role(current_user, ["admin", "staff"]):
        raise HTTPException(
            status_code=403, detail="Not authorized to reset usage cycles"
        )
    
    tariff_service = TariffService(db)
    result = tariff_service.reset_usage_cycle(user_id)
    
    return {
        "status": "success",
        "message": "Usage cycle reset successfully",
        "user_id": user_id
    }

@router.post("/process-scheduled-changes", response_model=Dict[str, Any])
async def process_scheduled_changes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Process scheduled tariff plan changes that are due.
    
    This endpoint is typically called by a scheduled task.
    Requires admin, staff, or system privileges.
    """
    if not has_role(current_user, ["admin", "staff", "system"]):
        raise HTTPException(
            status_code=403, detail="Not authorized to process scheduled changes"
        )
    
    tariff_service = TariffService(db)
    results = tariff_service.process_scheduled_plan_changes()
    
    return {
        "status": "success",
        "message": f"Processed {results['processed']} of {results['total']} scheduled changes",
        "results": results
    }

@router.post("/users/{user_id}/calculate-overage", response_model=Dict[str, Any])
async def calculate_overage_fee(
    user_id: int,
    usage_data: Dict[str, int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Calculate any overage fees based on usage and plan.
    
    Requires admin, staff, or system privileges.
    """
    if not has_role(current_user, ["admin", "staff", "system"]) and current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to calculate overage fees"
        )
    
    if "usage_mb" not in usage_data:
        raise HTTPException(status_code=400, detail="Missing required field: usage_mb")
    
    tariff_service = TariffService(db)
    fee = tariff_service.calculate_overage_fee(user_id, usage_data["usage_mb"])
    
    return {
        "user_id": user_id,
        "usage_mb": usage_data["usage_mb"],
        "overage_fee": fee
    }

@router.post("/check-fup", response_model=FUPThresholdResponse)
async def check_fup_threshold(
    check_data: FUPThresholdCheck,
    db: Session = Depends(get_db)
):
    """Check if a user has crossed the FUP threshold and should be throttled."""
    tariff_service = TariffService(db)
    return tariff_service.check_fup_threshold(check_data)

@router.get("/calculate-overage/{user_id}")
async def calculate_overage_fee(
    user_id: int,
    usage_mb: int,
    db: Session = Depends(get_db)
):
    """Calculate any overage fees based on usage and plan."""
    tariff_service = TariffService(db)
    fee = tariff_service.calculate_overage_fee(user_id, usage_mb)
    return {"user_id": user_id, "usage_mb": usage_mb, "overage_fee": fee}
