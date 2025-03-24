from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from fastapi import HTTPException

from backend_core.models import TaxRate
from modules.billing.models import TaxExemption
from modules.billing.schemas.tax import (
    TaxRateCreate, TaxRateUpdate, TaxExemptionCreate
)
from modules.billing.utils.audit import log_billing_action


class TaxService:
    """Service for managing tax rates and exemptions"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_tax_rate(self, tax_data: TaxRateCreate) -> TaxRate:
        """Creates a new tax rate."""
        # Check if a default tax rate already exists for this country/region
        if tax_data.is_default:
            existing_default = self.db.query(TaxRate).filter(
                TaxRate.country == tax_data.country,
                TaxRate.region == tax_data.region if tax_data.region else TaxRate.region.is_(None),
                TaxRate.is_default == True
            ).first()
            
            if existing_default:
                existing_default.is_default = False
        
        # Create new tax rate
        tax_rate = TaxRate(
            name=tax_data.name,
            description=tax_data.description,
            rate=tax_data.rate,
            country=tax_data.country,
            region=tax_data.region,
            is_default=tax_data.is_default
        )
        
        self.db.add(tax_rate)
        self.db.commit()
        self.db.refresh(tax_rate)
        
        # Log the action
        log_billing_action(
            self.db, 
            "tax_rate", 
            tax_rate.id, 
            "create", 
            None,  # Admin action, no user ID
            {"name": tax_rate.name, "rate": str(tax_rate.rate)}
        )
        
        return tax_rate
    
    def get_tax_rate(self, tax_rate_id: int) -> Optional[TaxRate]:
        """Retrieves a tax rate by ID."""
        return self.db.query(TaxRate).filter(TaxRate.id == tax_rate_id).first()
    
    def get_tax_rates(self, country: Optional[str] = None, region: Optional[str] = None) -> List[TaxRate]:
        """Gets all tax rates, optionally filtered by country and region."""
        query = self.db.query(TaxRate)
        
        if country:
            query = query.filter(TaxRate.country == country)
            
        if region:
            query = query.filter(TaxRate.region == region)
            
        return query.order_by(TaxRate.country, TaxRate.region).all()
    
    def update_tax_rate(self, tax_rate_id: int, tax_data: TaxRateUpdate) -> TaxRate:
        """Updates an existing tax rate."""
        tax_rate = self.get_tax_rate(tax_rate_id)
        if not tax_rate:
            raise HTTPException(status_code=404, detail="Tax rate not found")
        
        # Handle default flag
        if tax_data.is_default and not tax_rate.is_default:
            # Unset default flag on other tax rates for the same country/region
            self.db.query(TaxRate).filter(
                TaxRate.id != tax_rate_id,
                TaxRate.country == tax_rate.country,
                TaxRate.region == tax_rate.region if tax_rate.region else TaxRate.region.is_(None),
                TaxRate.is_default == True
            ).update({"is_default": False})
        
        # Update fields
        for field, value in tax_data.dict(exclude_unset=True).items():
            if hasattr(tax_rate, field) and field not in ['id', 'created_at']:
                setattr(tax_rate, field, value)
        
        tax_rate.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(tax_rate)
        
        # Log the action
        log_billing_action(
            self.db, 
            "tax_rate", 
            tax_rate.id, 
            "update", 
            None,  # Admin action, no user ID
            {"name": tax_rate.name, "rate": str(tax_rate.rate)}
        )
        
        return tax_rate
    
    def delete_tax_rate(self, tax_rate_id: int) -> bool:
        """Deletes a tax rate."""
        tax_rate = self.get_tax_rate(tax_rate_id)
        if not tax_rate:
            raise HTTPException(status_code=404, detail="Tax rate not found")
        
        # Check if tax rate is used in any invoices
        from backend_core.models import InvoiceTax
        usage_count = self.db.query(InvoiceTax).filter(
            InvoiceTax.tax_rate_id == tax_rate_id
        ).count()
        
        if usage_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete tax rate that is used in {usage_count} invoices"
            )
        
        # Delete tax exemptions for this tax rate
        self.db.query(TaxExemption).filter(
            TaxExemption.tax_rate_id == tax_rate_id
        ).delete()
        
        # Delete the tax rate
        self.db.delete(tax_rate)
        self.db.commit()
        
        # Log the action
        log_billing_action(
            self.db, 
            "tax_rate", 
            tax_rate_id, 
            "delete", 
            None,  # Admin action, no user ID
            {"name": tax_rate.name}
        )
        
        return True
    
    def get_applicable_tax_rates(self, country: str, region: Optional[str] = None) -> List[TaxRate]:
        """Gets applicable tax rates for a specific country and region."""
        # First try to find region-specific tax rates
        if region:
            region_rates = self.db.query(TaxRate).filter(
                TaxRate.country == country,
                TaxRate.region == region
            ).all()
            
            if region_rates:
                return region_rates
        
        # If no region-specific rates or no region provided, get country-level rates
        country_rates = self.db.query(TaxRate).filter(
            TaxRate.country == country,
            TaxRate.region.is_(None)
        ).all()
        
        if country_rates:
            return country_rates
        
        # If no country-specific rates, get the default rate for the country
        default_rate = self.db.query(TaxRate).filter(
            TaxRate.country == country,
            TaxRate.is_default == True
        ).first()
        
        if default_rate:
            return [default_rate]
        
        # If no default rate for the country, get the global default rate
        global_default = self.db.query(TaxRate).filter(
            TaxRate.is_default == True
        ).first()
        
        if global_default:
            return [global_default]
        
        # If no tax rates found, return empty list
        return []
    
    def create_tax_exemption(self, exemption_data: TaxExemptionCreate) -> TaxExemption:
        """Creates a tax exemption for a user."""
        # Verify tax rate exists
        tax_rate = self.get_tax_rate(exemption_data.tax_rate_id)
        if not tax_rate:
            raise HTTPException(status_code=404, detail="Tax rate not found")
        
        # Check if exemption already exists
        existing_exemption = self.db.query(TaxExemption).filter(
            TaxExemption.user_id == exemption_data.user_id,
            TaxExemption.tax_rate_id == exemption_data.tax_rate_id,
            or_(
                TaxExemption.valid_to.is_(None),
                TaxExemption.valid_to > datetime.utcnow()
            )
        ).first()
        
        if existing_exemption:
            raise HTTPException(
                status_code=400, 
                detail="User already has an active exemption for this tax rate"
            )
        
        # Create exemption
        exemption = TaxExemption(
            user_id=exemption_data.user_id,
            tax_rate_id=exemption_data.tax_rate_id,
            exemption_certificate=exemption_data.exemption_certificate,
            valid_from=exemption_data.valid_from or datetime.utcnow(),
            valid_to=exemption_data.valid_to
        )
        
        self.db.add(exemption)
        self.db.commit()
        self.db.refresh(exemption)
        
        # Log the action
        log_billing_action(
            self.db, 
            "tax_exemption", 
            exemption.id, 
            "create", 
            exemption_data.user_id, 
            {"tax_rate_id": exemption.tax_rate_id}
        )
        
        return exemption
    
    def get_tax_exemption(self, exemption_id: int) -> Optional[TaxExemption]:
        """Retrieves a tax exemption by ID."""
        return self.db.query(TaxExemption).filter(TaxExemption.id == exemption_id).first()
    
    def get_user_tax_exemptions(self, user_id: int, include_expired: bool = False) -> List[TaxExemption]:
        """Gets all tax exemptions for a specific user."""
        query = self.db.query(TaxExemption).filter(TaxExemption.user_id == user_id)
        
        if not include_expired:
            query = query.filter(
                or_(
                    TaxExemption.valid_to.is_(None),
                    TaxExemption.valid_to > datetime.utcnow()
                )
            )
            
        return query.all()
    
    def is_user_exempt(self, user_id: int, tax_rate_id: int) -> bool:
        """Checks if a user is exempt from a specific tax rate."""
        now = datetime.utcnow()
        
        exemption = self.db.query(TaxExemption).filter(
            TaxExemption.user_id == user_id,
            TaxExemption.tax_rate_id == tax_rate_id,
            TaxExemption.valid_from <= now,
            or_(
                TaxExemption.valid_to.is_(None),
                TaxExemption.valid_to > now
            )
        ).first()
        
        return exemption is not None
    
    def revoke_tax_exemption(self, exemption_id: int) -> TaxExemption:
        """Revokes a tax exemption by setting its valid_to date to now."""
        exemption = self.get_tax_exemption(exemption_id)
        if not exemption:
            raise HTTPException(status_code=404, detail="Tax exemption not found")
        
        exemption.valid_to = datetime.utcnow()
        self.db.commit()
        self.db.refresh(exemption)
        
        # Log the action
        log_billing_action(
            self.db, 
            "tax_exemption", 
            exemption.id, 
            "revoke", 
            exemption.user_id, 
            {"tax_rate_id": exemption.tax_rate_id}
        )
        
        return exemption
    
    def calculate_tax(self, amount: Decimal, country: str, region: Optional[str] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Calculates tax for a given amount, country, and region."""
        # Get applicable tax rates
        tax_rates = self.get_applicable_tax_rates(country, region)
        
        tax_details = []
        total_tax = Decimal('0.00')
        
        for tax_rate in tax_rates:
            # Check if user is exempt
            if user_id and self.is_user_exempt(user_id, tax_rate.id):
                continue
            
            # Calculate tax
            tax_amount = (amount * tax_rate.rate) / Decimal('100.00')
            
            tax_details.append({
                "tax_rate_id": tax_rate.id,
                "name": tax_rate.name,
                "rate": tax_rate.rate,
                "amount": tax_amount
            })
            
            total_tax += tax_amount
        
        return {
            "taxable_amount": amount,
            "total_tax": total_tax,
            "tax_details": tax_details,
            "country": country,
            "region": region
        }
