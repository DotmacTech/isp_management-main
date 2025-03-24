from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend_core.database import get_db
from backend_core.models import (
    Reseller, 
    ResellerCustomer, 
    ResellerTransaction, 
    ResellerCommissionRule,
    ResellerNotification,
    ResellerPortalSettings,
    Customer,
    User,
    UserTariffPlan,
    TariffPlan
)
from backend_core.utils.hateoas import generate_links
from .auth_utils import get_current_reseller
from .commission_service import CommissionService
from .schemas import (
    ResellerDashboardStats,
    ResellerProfileUpdate,
    ResellerCustomerList,
    ResellerCustomerSummary,
    CommissionCalculationRequest,
    CommissionCalculationResponse,
    ResellerPortalSettings as ResellerPortalSettingsSchema,
    ResellerNotification as ResellerNotificationSchema
)

router = APIRouter(
    prefix="/portal",
    tags=["reseller_portal"]
)

@router.get("/dashboard", response_model=ResellerDashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_reseller: Reseller = Depends(get_current_reseller)
):
    """
    Get dashboard statistics for the current reseller
    """
    # Count customers
    total_customers = db.query(func.count(ResellerCustomer.id)).filter(
        ResellerCustomer.reseller_id == current_reseller.id
    ).scalar() or 0
    
    # Count active customers
    active_customers = db.query(func.count(ResellerCustomer.id)).filter(
        ResellerCustomer.reseller_id == current_reseller.id
    ).join(
        Customer, Customer.id == ResellerCustomer.customer_id
    ).filter(
        Customer.status == "active"
    ).scalar() or 0
    
    # Get recent transactions
    recent_transactions = db.query(ResellerTransaction).filter(
        ResellerTransaction.reseller_id == current_reseller.id
    ).order_by(
        desc(ResellerTransaction.created_at)
    ).limit(5).all()
    
    # Calculate total revenue (sum of all commission transactions)
    total_revenue = db.query(func.sum(ResellerTransaction.amount)).filter(
        ResellerTransaction.reseller_id == current_reseller.id,
        ResellerTransaction.transaction_type == "commission"
    ).scalar() or 0.0
    
    # Get commission summary by tariff plan
    # First, get all customers assigned to this reseller
    customer_ids = db.query(ResellerCustomer.customer_id).filter(
        ResellerCustomer.reseller_id == current_reseller.id
    ).all()
    customer_ids = [c[0] for c in customer_ids]
    
    # Get customers' user IDs
    user_ids = db.query(Customer.user_id).filter(
        Customer.id.in_(customer_ids)
    ).all()
    user_ids = [u[0] for u in user_ids]
    
    # Get active tariff plans for these users
    tariff_plans = db.query(
        TariffPlan.name,
        func.count(UserTariffPlan.id).label('customer_count')
    ).join(
        UserTariffPlan, UserTariffPlan.tariff_plan_id == TariffPlan.id
    ).filter(
        UserTariffPlan.user_id.in_(user_ids),
        UserTariffPlan.status == "active"
    ).group_by(
        TariffPlan.name
    ).all()
    
    commission_summary = {
        "plans_breakdown": {tp.name: tp.customer_count for tp in tariff_plans},
        "total_revenue": total_revenue,
        "current_balance": current_reseller.current_balance
    }
    
    # Format recent transactions for response
    formatted_transactions = [
        {
            "id": t.id,
            "amount": t.amount,
            "transaction_type": t.transaction_type,
            "description": t.description,
            "created_at": t.created_at.isoformat(),
            "links": generate_links(
                resource_id=t.id,
                resource_type="reseller_transaction",
                base_path="/api/v1/reseller/transactions"
            )
        } for t in recent_transactions
    ]
    
    return {
        "total_customers": total_customers,
        "active_customers": active_customers,
        "total_revenue": total_revenue,
        "current_balance": current_reseller.current_balance,
        "recent_transactions": formatted_transactions,
        "commission_summary": commission_summary
    }

@router.get("/profile", response_model=Dict[str, Any])
async def get_reseller_profile(
    db: Session = Depends(get_db),
    current_reseller: Reseller = Depends(get_current_reseller)
):
    """
    Get the current reseller's profile
    """
    # Get the user associated with this reseller
    user = db.query(User).filter(User.id == current_reseller.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get tier benefits
    commission_service = CommissionService(db)
    tier_benefits = commission_service.get_tier_benefits(current_reseller.tier)
    
    return {
        "id": current_reseller.id,
        "company_name": current_reseller.company_name,
        "contact_person": current_reseller.contact_person,
        "email": current_reseller.email,
        "phone": current_reseller.phone,
        "address": current_reseller.address,
        "tax_id": current_reseller.tax_id,
        "status": current_reseller.status,
        "tier": current_reseller.tier,
        "tier_benefits": tier_benefits,
        "commission_type": current_reseller.commission_type,
        "commission_rate": current_reseller.commission_rate,
        "credit_limit": current_reseller.credit_limit,
        "current_balance": current_reseller.current_balance,
        "created_at": current_reseller.created_at.isoformat(),
        "username": user.username,
        "user_email": user.email,
        "links": generate_links(
            resource_id=current_reseller.id,
            resource_type="reseller",
            base_path="/api/v1/reseller"
        )
    }

@router.patch("/profile", response_model=Dict[str, Any])
async def update_reseller_profile(
    profile_update: ResellerProfileUpdate,
    db: Session = Depends(get_db),
    current_reseller: Reseller = Depends(get_current_reseller)
):
    """
    Update the current reseller's profile
    """
    # Update only the provided fields
    update_data = profile_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        if hasattr(current_reseller, key):
            setattr(current_reseller, key, value)
    
    current_reseller.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_reseller)
    
    return {
        "id": current_reseller.id,
        "company_name": current_reseller.company_name,
        "contact_person": current_reseller.contact_person,
        "email": current_reseller.email,
        "phone": current_reseller.phone,
        "address": current_reseller.address,
        "tax_id": current_reseller.tax_id,
        "status": current_reseller.status,
        "updated_at": current_reseller.updated_at.isoformat(),
        "message": "Profile updated successfully",
        "links": generate_links(
            resource_id=current_reseller.id,
            resource_type="reseller",
            base_path="/api/v1/reseller"
        )
    }

@router.get("/customers", response_model=ResellerCustomerList)
async def get_reseller_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_reseller: Reseller = Depends(get_current_reseller)
):
    """
    Get all customers assigned to the current reseller
    """
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Base query
    query = db.query(Customer).join(
        ResellerCustomer, ResellerCustomer.customer_id == Customer.id
    ).filter(
        ResellerCustomer.reseller_id == current_reseller.id
    )
    
    # Apply filters
    if status:
        query = query.filter(Customer.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Customer.full_name.ilike(search_term)) |
            (Customer.email.ilike(search_term)) |
            (Customer.phone.ilike(search_term))
        )
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    customers = query.offset(offset).limit(page_size).all()
    
    # Format results
    customer_list = []
    for customer in customers:
        # Get subscription plan if available
        subscription_plan = None
        subscription_status = None
        
        user_tariff_plan = db.query(UserTariffPlan).filter(
            UserTariffPlan.user_id == customer.user_id,
            UserTariffPlan.status == "active"
        ).first()
        
        if user_tariff_plan:
            tariff_plan = db.query(TariffPlan).filter(
                TariffPlan.id == user_tariff_plan.tariff_plan_id
            ).first()
            
            if tariff_plan:
                subscription_plan = tariff_plan.name
                subscription_status = user_tariff_plan.status
        
        customer_list.append(ResellerCustomerSummary(
            id=customer.id,
            name=customer.full_name,
            email=customer.email,
            status=customer.status,
            subscription_plan=subscription_plan,
            subscription_status=subscription_status,
            created_at=customer.created_at
        ))
    
    return ResellerCustomerList(
        customers=customer_list,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/customers/{customer_id}", response_model=Dict[str, Any])
async def get_customer_details(
    customer_id: int,
    db: Session = Depends(get_db),
    current_reseller: Reseller = Depends(get_current_reseller)
):
    """
    Get detailed information about a specific customer
    """
    # Check if this customer belongs to the reseller
    reseller_customer = db.query(ResellerCustomer).filter(
        ResellerCustomer.reseller_id == current_reseller.id,
        ResellerCustomer.customer_id == customer_id
    ).first()
    
    if not reseller_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found or not assigned to this reseller"
        )
    
    # Get customer details
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Get subscription information
    user_tariff_plans = db.query(UserTariffPlan).filter(
        UserTariffPlan.user_id == customer.user_id
    ).all()
    
    subscriptions = []
    for utp in user_tariff_plans:
        tariff_plan = db.query(TariffPlan).filter(TariffPlan.id == utp.tariff_plan_id).first()
        if tariff_plan:
            subscriptions.append({
                "plan_name": tariff_plan.name,
                "status": utp.status,
                "start_date": utp.start_date.isoformat(),
                "end_date": utp.end_date.isoformat() if utp.end_date else None,
                "data_used": utp.data_used,
                "is_throttled": utp.is_throttled
            })
    
    return {
        "id": customer.id,
        "full_name": customer.full_name,
        "email": customer.email,
        "phone": customer.phone,
        "address": customer.address,
        "status": customer.status,
        "created_at": customer.created_at.isoformat(),
        "updated_at": customer.updated_at.isoformat(),
        "notes": reseller_customer.notes,
        "subscriptions": subscriptions,
        "links": generate_links(
            resource_id=customer.id,
            resource_type="customer",
            base_path="/api/v1/customer"
        )
    }

@router.post("/commission/calculate", response_model=CommissionCalculationResponse)
async def calculate_commission(
    request: CommissionCalculationRequest,
    db: Session = Depends(get_db),
    current_reseller: Reseller = Depends(get_current_reseller)
):
    """
    Calculate commission for the current reseller
    """
    # Override reseller_id with current reseller's ID
    request.reseller_id = current_reseller.id
    
    commission_service = CommissionService(db)
    return commission_service.calculate_commission(request)

@router.get("/commission/history", response_model=List[Dict[str, Any]])
async def get_commission_history(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_reseller: Reseller = Depends(get_current_reseller)
):
    """
    Get commission payment history for the current reseller
    """
    commission_service = CommissionService(db)
    history = commission_service.get_commission_history(current_reseller.id, limit, offset)
    
    # Add HATEOAS links
    for item in history:
        item["links"] = generate_links(
            resource_id=item["id"],
            resource_type="reseller_commission_payout",
            base_path="/api/v1/reseller/commission/payouts"
        )
    
    return history

@router.get("/notifications", response_model=List[ResellerNotificationSchema])
async def get_notifications(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_reseller: Reseller = Depends(get_current_reseller)
):
    """
    Get notifications for the current reseller
    """
    query = db.query(ResellerNotification).filter(
        ResellerNotification.reseller_id == current_reseller.id
    )
    
    if unread_only:
        query = query.filter(ResellerNotification.is_read == False)
    
    notifications = query.order_by(
        desc(ResellerNotification.created_at)
    ).offset(offset).limit(limit).all()
    
    return notifications

@router.patch("/notifications/{notification_id}/read", response_model=Dict[str, Any])
async def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_reseller: Reseller = Depends(get_current_reseller)
):
    """
    Mark a notification as read
    """
    notification = db.query(ResellerNotification).filter(
        ResellerNotification.id == notification_id,
        ResellerNotification.reseller_id == current_reseller.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    db.commit()
    
    return {
        "id": notification.id,
        "is_read": True,
        "message": "Notification marked as read"
    }

@router.get("/settings", response_model=ResellerPortalSettingsSchema)
async def get_portal_settings(
    db: Session = Depends(get_db),
    current_reseller: Reseller = Depends(get_current_reseller)
):
    """
    Get portal settings for the current reseller
    """
    settings = db.query(ResellerPortalSettings).filter(
        ResellerPortalSettings.reseller_id == current_reseller.id
    ).first()
    
    if not settings:
        # Create default settings
        settings = ResellerPortalSettings(
            reseller_id=current_reseller.id,
            dashboard_widgets=["customers", "revenue", "transactions", "commissions"],
            notification_preferences={
                "email": True,
                "portal": True
            },
            display_preferences={
                "theme": "light",
                "language": "en"
            }
        )
        
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return ResellerPortalSettingsSchema(
        dashboard_widgets=settings.dashboard_widgets or [],
        notification_preferences=settings.notification_preferences or {},
        display_preferences=settings.display_preferences or {}
    )

@router.patch("/settings", response_model=Dict[str, Any])
async def update_portal_settings(
    settings_update: ResellerPortalSettingsSchema,
    db: Session = Depends(get_db),
    current_reseller: Reseller = Depends(get_current_reseller)
):
    """
    Update portal settings for the current reseller
    """
    settings = db.query(ResellerPortalSettings).filter(
        ResellerPortalSettings.reseller_id == current_reseller.id
    ).first()
    
    if not settings:
        # Create new settings
        settings = ResellerPortalSettings(
            reseller_id=current_reseller.id,
            dashboard_widgets=settings_update.dashboard_widgets,
            notification_preferences=settings_update.notification_preferences,
            display_preferences=settings_update.display_preferences
        )
        
        db.add(settings)
    else:
        # Update existing settings
        settings.dashboard_widgets = settings_update.dashboard_widgets
        settings.notification_preferences = settings_update.notification_preferences
        settings.display_preferences = settings_update.display_preferences
        settings.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Settings updated successfully",
        "dashboard_widgets": settings.dashboard_widgets,
        "notification_preferences": settings.notification_preferences,
        "display_preferences": settings.display_preferences
    }
