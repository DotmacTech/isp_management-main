from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, extract, case
from fastapi import HTTPException
import calendar
import json

from backend_core.models import User, Invoice, Payment
from modules.billing.models import (
    InvoiceItem, PaymentTransaction, Subscription, 
    SubscriptionStatus, FinancialTransaction, BillingCycle
)


class ReportingService:
    """Service for generating financial reports and analytics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_revenue_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Gets a summary of revenue for a date range."""
        # Get total invoiced amount
        invoiced_amount = self.db.query(func.sum(Invoice.amount)).filter(
            Invoice.created_at.between(start_date, end_date)
        ).scalar() or Decimal('0.00')
        
        # Get total paid amount
        paid_amount = self.db.query(func.sum(Payment.amount)).filter(
            Payment.created_at.between(start_date, end_date),
            Payment.status == 'completed'
        ).scalar() or Decimal('0.00')
        
        # Get total outstanding amount
        outstanding_amount = self.db.query(func.sum(Invoice.amount - Invoice.amount_paid)).filter(
            Invoice.created_at.between(start_date, end_date),
            Invoice.status.in_(['pending', 'overdue'])
        ).scalar() or Decimal('0.00')
        
        # Get invoice count
        invoice_count = self.db.query(func.count(Invoice.id)).filter(
            Invoice.created_at.between(start_date, end_date)
        ).scalar() or 0
        
        # Get payment count
        payment_count = self.db.query(func.count(Payment.id)).filter(
            Payment.created_at.between(start_date, end_date),
            Payment.status == 'completed'
        ).scalar() or 0
        
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "invoiced_amount": float(invoiced_amount),
            "paid_amount": float(paid_amount),
            "outstanding_amount": float(outstanding_amount),
            "invoice_count": invoice_count,
            "payment_count": payment_count,
            "collection_rate": float(paid_amount / invoiced_amount * 100) if invoiced_amount > 0 else 0
        }
    
    def get_revenue_by_period(self, start_date: datetime, end_date: datetime, period: str = 'month') -> List[Dict[str, Any]]:
        """Gets revenue broken down by period (day, week, month, quarter, year)."""
        results = []
        
        if period == 'day':
            # Group by day
            query = self.db.query(
                func.date(Payment.created_at).label('period'),
                func.sum(Payment.amount).label('revenue')
            ).filter(
                Payment.created_at.between(start_date, end_date),
                Payment.status == 'completed'
            ).group_by(func.date(Payment.created_at)).order_by('period')
            
            for row in query:
                results.append({
                    "period": row.period.isoformat(),
                    "revenue": float(row.revenue)
                })
        
        elif period == 'week':
            # Group by week
            query = self.db.query(
                extract('year', Payment.created_at).label('year'),
                extract('week', Payment.created_at).label('week'),
                func.sum(Payment.amount).label('revenue')
            ).filter(
                Payment.created_at.between(start_date, end_date),
                Payment.status == 'completed'
            ).group_by('year', 'week').order_by('year', 'week')
            
            for row in query:
                results.append({
                    "period": f"{int(row.year)}-W{int(row.week)}",
                    "revenue": float(row.revenue)
                })
        
        elif period == 'month':
            # Group by month
            query = self.db.query(
                extract('year', Payment.created_at).label('year'),
                extract('month', Payment.created_at).label('month'),
                func.sum(Payment.amount).label('revenue')
            ).filter(
                Payment.created_at.between(start_date, end_date),
                Payment.status == 'completed'
            ).group_by('year', 'month').order_by('year', 'month')
            
            for row in query:
                month_name = calendar.month_name[int(row.month)]
                results.append({
                    "period": f"{int(row.year)}-{int(row.month):02d}",
                    "period_name": f"{month_name} {int(row.year)}",
                    "revenue": float(row.revenue)
                })
        
        elif period == 'quarter':
            # Group by quarter
            query = self.db.query(
                extract('year', Payment.created_at).label('year'),
                extract('quarter', Payment.created_at).label('quarter'),
                func.sum(Payment.amount).label('revenue')
            ).filter(
                Payment.created_at.between(start_date, end_date),
                Payment.status == 'completed'
            ).group_by('year', 'quarter').order_by('year', 'quarter')
            
            for row in query:
                results.append({
                    "period": f"{int(row.year)}-Q{int(row.quarter)}",
                    "revenue": float(row.revenue)
                })
        
        elif period == 'year':
            # Group by year
            query = self.db.query(
                extract('year', Payment.created_at).label('year'),
                func.sum(Payment.amount).label('revenue')
            ).filter(
                Payment.created_at.between(start_date, end_date),
                Payment.status == 'completed'
            ).group_by('year').order_by('year')
            
            for row in query:
                results.append({
                    "period": str(int(row.year)),
                    "revenue": float(row.revenue)
                })
        
        return results
    
    def get_revenue_by_service(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Gets revenue broken down by service type."""
        query = self.db.query(
            InvoiceItem.description.label('service'),
            func.sum(InvoiceItem.quantity * InvoiceItem.unit_price).label('revenue')
        ).join(
            Invoice, InvoiceItem.invoice_id == Invoice.id
        ).filter(
            Invoice.created_at.between(start_date, end_date)
        ).group_by(InvoiceItem.description).order_by(desc('revenue'))
        
        results = []
        for row in query:
            results.append({
                "service": row.service,
                "revenue": float(row.revenue)
            })
        
        return results
    
    def get_payment_method_distribution(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Gets distribution of payments by payment method."""
        query = self.db.query(
            Payment.payment_method.label('method'),
            func.count(Payment.id).label('count'),
            func.sum(Payment.amount).label('amount')
        ).filter(
            Payment.created_at.between(start_date, end_date),
            Payment.status == 'completed'
        ).group_by(Payment.payment_method).order_by(desc('amount'))
        
        results = []
        total_amount = Decimal('0.00')
        
        # First pass to get total
        for row in query:
            total_amount += row.amount
        
        # Second pass to calculate percentages
        for row in query:
            percentage = (row.amount / total_amount * 100) if total_amount > 0 else 0
            results.append({
                "method": row.method,
                "count": row.count,
                "amount": float(row.amount),
                "percentage": float(percentage)
            })
        
        return results
    
    def get_subscription_metrics(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Gets metrics about subscriptions at a specific date."""
        if not date:
            date = datetime.utcnow()
        
        # Total active subscriptions
        active_count = self.db.query(func.count(Subscription.id)).filter(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            Subscription.created_at <= date
        ).scalar() or 0
        
        # Subscriptions by status
        status_counts = {}
        for status in SubscriptionStatus:
            count = self.db.query(func.count(Subscription.id)).filter(
                Subscription.status == status,
                Subscription.created_at <= date
            ).scalar() or 0
            status_counts[status.name] = count
        
        # Subscriptions by billing cycle
        cycle_counts = {}
        for cycle in BillingCycle:
            count = self.db.query(func.count(Subscription.id)).filter(
                Subscription.billing_cycle == cycle,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                Subscription.created_at <= date
            ).scalar() or 0
            cycle_counts[cycle.name] = count
        
        # Monthly recurring revenue (MRR)
        mrr = self.db.query(func.sum(
            case(
                [
                    (Subscription.billing_cycle == BillingCycle.MONTHLY, Subscription.amount),
                    (Subscription.billing_cycle == BillingCycle.QUARTERLY, Subscription.amount / 3),
                    (Subscription.billing_cycle == BillingCycle.SEMI_ANNUAL, Subscription.amount / 6),
                    (Subscription.billing_cycle == BillingCycle.ANNUAL, Subscription.amount / 12)
                ],
                else_=Subscription.amount
            )
        )).filter(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            Subscription.created_at <= date
        ).scalar() or Decimal('0.00')
        
        # Annual recurring revenue (ARR)
        arr = mrr * 12
        
        return {
            "date": date.isoformat(),
            "active_subscriptions": active_count,
            "subscriptions_by_status": status_counts,
            "subscriptions_by_cycle": cycle_counts,
            "monthly_recurring_revenue": float(mrr),
            "annual_recurring_revenue": float(arr)
        }
    
    def get_subscription_growth(self, start_date: datetime, end_date: datetime, period: str = 'month') -> List[Dict[str, Any]]:
        """Gets subscription growth over time."""
        results = []
        
        if period == 'day':
            # Daily granularity
            current_date = start_date
            while current_date <= end_date:
                next_date = current_date + timedelta(days=1)
                
                # New subscriptions
                new_count = self.db.query(func.count(Subscription.id)).filter(
                    Subscription.created_at.between(current_date, next_date)
                ).scalar() or 0
                
                # Cancelled subscriptions
                cancelled_count = self.db.query(func.count(Subscription.id)).filter(
                    Subscription.status == SubscriptionStatus.CANCELLED,
                    Subscription.cancelled_at.between(current_date, next_date)
                ).scalar() or 0
                
                # Active subscriptions at end of day
                active_count = self.db.query(func.count(Subscription.id)).filter(
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                    Subscription.created_at <= next_date
                ).scalar() or 0
                
                results.append({
                    "period": current_date.date().isoformat(),
                    "new_subscriptions": new_count,
                    "cancelled_subscriptions": cancelled_count,
                    "active_subscriptions": active_count,
                    "net_change": new_count - cancelled_count
                })
                
                current_date = next_date
        
        elif period == 'month':
            # Monthly granularity
            current_date = datetime(start_date.year, start_date.month, 1)
            while current_date <= end_date:
                # Calculate end of month
                if current_date.month == 12:
                    next_date = datetime(current_date.year + 1, 1, 1)
                else:
                    next_date = datetime(current_date.year, current_date.month + 1, 1)
                
                # New subscriptions
                new_count = self.db.query(func.count(Subscription.id)).filter(
                    Subscription.created_at.between(current_date, next_date)
                ).scalar() or 0
                
                # Cancelled subscriptions
                cancelled_count = self.db.query(func.count(Subscription.id)).filter(
                    Subscription.status == SubscriptionStatus.CANCELLED,
                    Subscription.cancelled_at.between(current_date, next_date)
                ).scalar() or 0
                
                # Active subscriptions at end of month
                active_count = self.db.query(func.count(Subscription.id)).filter(
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                    Subscription.created_at <= next_date
                ).scalar() or 0
                
                month_name = calendar.month_name[current_date.month]
                results.append({
                    "period": f"{current_date.year}-{current_date.month:02d}",
                    "period_name": f"{month_name} {current_date.year}",
                    "new_subscriptions": new_count,
                    "cancelled_subscriptions": cancelled_count,
                    "active_subscriptions": active_count,
                    "net_change": new_count - cancelled_count
                })
                
                current_date = next_date
        
        return results
    
    def get_churn_rate(self, start_date: datetime, end_date: datetime, period: str = 'month') -> List[Dict[str, Any]]:
        """Calculates churn rate over time."""
        results = []
        
        if period == 'month':
            # Monthly granularity
            current_date = datetime(start_date.year, start_date.month, 1)
            while current_date <= end_date:
                # Calculate end of month
                if current_date.month == 12:
                    next_date = datetime(current_date.year + 1, 1, 1)
                else:
                    next_date = datetime(current_date.year, current_date.month + 1, 1)
                
                # Subscriptions at start of month
                start_count = self.db.query(func.count(Subscription.id)).filter(
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                    Subscription.created_at < current_date
                ).scalar() or 0
                
                # Cancelled during month
                cancelled_count = self.db.query(func.count(Subscription.id)).filter(
                    Subscription.status == SubscriptionStatus.CANCELLED,
                    Subscription.cancelled_at.between(current_date, next_date)
                ).scalar() or 0
                
                # Calculate churn rate
                churn_rate = (cancelled_count / start_count * 100) if start_count > 0 else 0
                
                month_name = calendar.month_name[current_date.month]
                results.append({
                    "period": f"{current_date.year}-{current_date.month:02d}",
                    "period_name": f"{month_name} {current_date.year}",
                    "starting_subscriptions": start_count,
                    "cancelled_subscriptions": cancelled_count,
                    "churn_rate": float(churn_rate)
                })
                
                current_date = next_date
        
        return results
    
    def get_accounts_receivable_aging(self) -> Dict[str, Any]:
        """Gets accounts receivable aging report."""
        now = datetime.utcnow()
        
        # Define aging buckets
        buckets = {
            "current": (0, 30),
            "30_60_days": (30, 60),
            "60_90_days": (60, 90),
            "over_90_days": (90, float('inf'))
        }
        
        results = {
            "total_outstanding": 0,
            "buckets": {}
        }
        
        for bucket_name, (min_days, max_days) in buckets.items():
            min_date = now - timedelta(days=max_days)
            max_date = now - timedelta(days=min_days)
            
            amount = self.db.query(func.sum(Invoice.amount - Invoice.amount_paid)).filter(
                Invoice.due_date.between(min_date, max_date),
                Invoice.status.in_(['pending', 'overdue']),
                Invoice.amount_paid < Invoice.amount
            ).scalar() or Decimal('0.00')
            
            count = self.db.query(func.count(Invoice.id)).filter(
                Invoice.due_date.between(min_date, max_date),
                Invoice.status.in_(['pending', 'overdue']),
                Invoice.amount_paid < Invoice.amount
            ).scalar() or 0
            
            results["buckets"][bucket_name] = {
                "amount": float(amount),
                "count": count
            }
            
            results["total_outstanding"] += float(amount)
        
        return results
    
    def get_financial_statement(self, start_date: datetime, end_date: datetime, statement_type: str = 'income') -> Dict[str, Any]:
        """Generates a financial statement (income statement or balance sheet)."""
        if statement_type == 'income':
            # Income Statement
            
            # Revenue
            revenue = self.db.query(func.sum(Payment.amount)).filter(
                Payment.created_at.between(start_date, end_date),
                Payment.status == 'completed'
            ).scalar() or Decimal('0.00')
            
            # Refunds
            refunds = self.db.query(func.sum(PaymentTransaction.amount)).filter(
                PaymentTransaction.transaction_type == 'refund',
                PaymentTransaction.created_at.between(start_date, end_date)
            ).scalar() or Decimal('0.00')
            
            # Net revenue
            net_revenue = revenue - refunds
            
            # Cost of services (placeholder - would need actual cost data)
            cost_of_services = Decimal('0.00')
            
            # Gross profit
            gross_profit = net_revenue - cost_of_services
            
            # Expenses (placeholder - would need actual expense data)
            expenses = {
                "payment_processing_fees": Decimal('0.00'),
                "bad_debt": Decimal('0.00'),
                "other_expenses": Decimal('0.00')
            }
            
            total_expenses = sum(expenses.values())
            
            # Net income
            net_income = gross_profit - total_expenses
            
            return {
                "statement_type": "income",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "revenue": float(revenue),
                "refunds": float(refunds),
                "net_revenue": float(net_revenue),
                "cost_of_services": float(cost_of_services),
                "gross_profit": float(gross_profit),
                "expenses": {k: float(v) for k, v in expenses.items()},
                "total_expenses": float(total_expenses),
                "net_income": float(net_income)
            }
        
        elif statement_type == 'balance':
            # Balance Sheet (simplified)
            
            # Assets
            accounts_receivable = self.db.query(func.sum(Invoice.amount - Invoice.amount_paid)).filter(
                Invoice.status.in_(['pending', 'overdue']),
                Invoice.amount_paid < Invoice.amount
            ).scalar() or Decimal('0.00')
            
            # Liabilities
            customer_credits = Decimal('0.00')  # Would need actual credit balance data
            
            return {
                "statement_type": "balance",
                "as_of_date": end_date.isoformat(),
                "assets": {
                    "accounts_receivable": float(accounts_receivable),
                    "total_assets": float(accounts_receivable)
                },
                "liabilities": {
                    "customer_credits": float(customer_credits),
                    "total_liabilities": float(customer_credits)
                },
                "equity": {
                    "total_equity": float(accounts_receivable - customer_credits)
                }
            }
        
        return {"error": "Invalid statement type"}
    
    def get_customer_lifetime_value(self, user_id: Optional[int] = None, segment: Optional[str] = None) -> Dict[str, Any]:
        """Calculates customer lifetime value for a user or segment."""
        if user_id:
            # Calculate LTV for specific user
            
            # Total payments
            total_payments = self.db.query(func.sum(Payment.amount)).filter(
                Payment.user_id == user_id,
                Payment.status == 'completed'
            ).scalar() or Decimal('0.00')
            
            # Customer age in months
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            months_active = (datetime.utcnow() - user.created_at).days / 30
            
            # Average monthly revenue
            monthly_revenue = total_payments / Decimal(str(months_active)) if months_active > 0 else Decimal('0.00')
            
            return {
                "user_id": user_id,
                "total_revenue": float(total_payments),
                "months_active": round(months_active, 1),
                "monthly_revenue": float(monthly_revenue),
                "estimated_lifetime_value": float(monthly_revenue * 36)  # 3-year estimate
            }
        
        elif segment:
            # Calculate average LTV for a segment
            # This would require a more complex implementation with user segmentation
            return {"error": "Segment-based LTV calculation not implemented"}
        
        else:
            # Calculate average LTV across all customers
            
            # Total revenue
            total_revenue = self.db.query(func.sum(Payment.amount)).filter(
                Payment.status == 'completed'
            ).scalar() or Decimal('0.00')
            
            # Total customers with payments
            paying_customers = self.db.query(func.count(func.distinct(Payment.user_id))).filter(
                Payment.status == 'completed'
            ).scalar() or 0
            
            # Average revenue per customer
            avg_revenue_per_customer = total_revenue / Decimal(str(paying_customers)) if paying_customers > 0 else Decimal('0.00')
            
            # Average customer lifespan (in months)
            avg_lifespan = 24  # Placeholder - would need actual churn data to calculate
            
            return {
                "total_revenue": float(total_revenue),
                "paying_customers": paying_customers,
                "average_revenue_per_customer": float(avg_revenue_per_customer),
                "average_customer_lifespan_months": avg_lifespan,
                "average_lifetime_value": float(avg_revenue_per_customer * avg_lifespan)
            }
    
    def export_financial_data(self, start_date: datetime, end_date: datetime, report_type: str) -> Dict[str, Any]:
        """Exports financial data for external use."""
        if report_type == 'revenue':
            data = self.get_revenue_by_period(start_date, end_date, 'month')
        elif report_type == 'subscriptions':
            data = self.get_subscription_growth(start_date, end_date, 'month')
        elif report_type == 'payments':
            # Get all payments in date range
            payments = self.db.query(Payment).filter(
                Payment.created_at.between(start_date, end_date)
            ).all()
            
            data = [{
                "id": payment.id,
                "user_id": payment.user_id,
                "invoice_id": payment.invoice_id,
                "amount": float(payment.amount),
                "payment_method": payment.payment_method,
                "status": payment.status,
                "created_at": payment.created_at.isoformat()
            } for payment in payments]
        else:
            return {"error": "Invalid report type"}
        
        return {
            "report_type": report_type,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "data": data
        }
