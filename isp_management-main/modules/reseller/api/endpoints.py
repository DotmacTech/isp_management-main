from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend_core.database import get_db
from backend_core.auth_service import get_current_active_user, get_current_user_role
from .schemas import (
    ResellerCreate,
    ResellerResponse,
    ResellerCustomerCreate,
    ResellerCustomerResponse,
    ResellerTransactionCreate,
    ResellerTransactionResponse,
    ResellerCommissionRuleCreate,
    ResellerCommissionRuleResponse,
    ResellerSearch
)
from .services import ResellerService

router = APIRouter(
    prefix="/reseller",
    tags=["reseller"],
    dependencies=[Depends(get_current_active_user)]
)

# Reseller Management
@router.post("/", response_model=ResellerResponse, status_code=status.HTTP_201_CREATED)
async def create_reseller(
    reseller_data: ResellerCreate,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Create a new reseller profile."""
    if current_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    reseller_service = ResellerService(db)
    return reseller_service.create_reseller(reseller_data)

@router.get("/{reseller_id}", response_model=ResellerResponse)
async def get_reseller(
    reseller_id: int,
    db: Session = Depends(get_db)
):
    """Get a reseller by ID."""
    reseller_service = ResellerService(db)
    return reseller_service.get_reseller(reseller_id)

@router.get("/user/{user_id}", response_model=ResellerResponse)
async def get_reseller_by_user_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get a reseller by user ID."""
    reseller_service = ResellerService(db)
    return reseller_service.get_reseller_by_user_id(user_id)

@router.patch("/{reseller_id}", response_model=ResellerResponse)
async def update_reseller(
    reseller_id: int,
    reseller_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Update a reseller's information."""
    if current_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    reseller_service = ResellerService(db)
    return reseller_service.update_reseller(reseller_id, reseller_data)

@router.post("/search", response_model=List[ResellerResponse])
async def search_resellers(
    search_params: ResellerSearch,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Search for resellers."""
    if current_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    reseller_service = ResellerService(db)
    return reseller_service.search_resellers(search_params)

@router.get("/{reseller_id}/statistics", response_model=Dict[str, Any])
async def get_reseller_statistics(
    reseller_id: int,
    db: Session = Depends(get_db)
):
    """Get statistics about a reseller."""
    reseller_service = ResellerService(db)
    return reseller_service.get_reseller_statistics(reseller_id)

# Customer Management
@router.post("/customers", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def assign_customer_to_reseller(
    assignment_data: ResellerCustomerCreate,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Assign a customer to a reseller."""
    if current_user_role not in ["admin", "reseller"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    reseller_service = ResellerService(db)
    return reseller_service.assign_customer_to_reseller(assignment_data)

@router.get("/{reseller_id}/customers", response_model=List[Dict[str, Any]])
async def get_reseller_customers(
    reseller_id: int,
    db: Session = Depends(get_db)
):
    """Get all customers assigned to a reseller."""
    reseller_service = ResellerService(db)
    return reseller_service.get_reseller_customers(reseller_id)

@router.delete("/customers/{assignment_id}", response_model=Dict[str, Any])
async def remove_customer_from_reseller(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Remove a customer from a reseller."""
    if current_user_role not in ["admin", "reseller"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    reseller_service = ResellerService(db)
    return reseller_service.remove_customer_from_reseller(assignment_id)

# Transaction Management
@router.post("/transactions", response_model=ResellerTransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: ResellerTransactionCreate,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Create a new transaction for a reseller."""
    if current_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    reseller_service = ResellerService(db)
    return reseller_service.create_transaction(transaction_data)

@router.get("/{reseller_id}/transactions", response_model=List[ResellerTransactionResponse])
async def get_reseller_transactions(
    reseller_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all transactions for a reseller."""
    reseller_service = ResellerService(db)
    return reseller_service.get_reseller_transactions(reseller_id, limit, offset)

# Commission Rules Management
@router.post("/commission-rules", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_commission_rule(
    rule_data: ResellerCommissionRuleCreate,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Create a new commission rule for a reseller."""
    if current_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    reseller_service = ResellerService(db)
    return reseller_service.create_commission_rule(rule_data)

@router.get("/{reseller_id}/commission-rules", response_model=List[Dict[str, Any]])
async def get_reseller_commission_rules(
    reseller_id: int,
    db: Session = Depends(get_db)
):
    """Get all commission rules for a reseller."""
    reseller_service = ResellerService(db)
    return reseller_service.get_reseller_commission_rules(reseller_id)

@router.patch("/commission-rules/{rule_id}", response_model=Dict[str, Any])
async def update_commission_rule(
    rule_id: int,
    rule_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Update a commission rule."""
    if current_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    reseller_service = ResellerService(db)
    return reseller_service.update_commission_rule(rule_id, rule_data)

@router.delete("/commission-rules/{rule_id}", response_model=Dict[str, Any])
async def delete_commission_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user_role: str = Depends(get_current_user_role)
):
    """Delete a commission rule."""
    if current_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    reseller_service = ResellerService(db)
    return reseller_service.delete_commission_rule(rule_id)
