"""
Celery tasks for the billing module.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from celery import shared_task
from sqlalchemy.orm import Session

from backend_core.database import SessionLocal
from backend_core.models import Invoice, User
from backend_core.email_service import send_email
from .services import BillingService

logger = logging.getLogger(__name__)

@shared_task
def send_invoice_reminders():
    """
    Task to send invoice reminders for overdue invoices.
    This task should be scheduled to run daily.
    """
    logger.info("Starting task: send_invoice_reminders")
    
    db = SessionLocal()
    try:
        billing_service = BillingService(db)
        
        # Get all overdue invoices
        overdue_invoices = billing_service.check_overdue_invoices()
        
        # Group invoices by user for consolidated reminders
        user_invoices: Dict[int, List[Invoice]] = {}
        for invoice in overdue_invoices:
            if invoice.user_id not in user_invoices:
                user_invoices[invoice.user_id] = []
            user_invoices[invoice.user_id].append(invoice)
        
        # Send reminders for each user
        for user_id, invoices in user_invoices.items():
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user or not user.email:
                    logger.warning(f"User {user_id} not found or has no email. Skipping reminder.")
                    continue
                
                # Generate reminder email for the first invoice (most important one)
                # In a real implementation, we might want to include all invoices in a single email
                invoice_id = invoices[0].id
                html_content = billing_service.generate_invoice_reminder_email(invoice_id)
                
                # Send the email
                subject = f"Reminder: Invoice #{invoice_id} is overdue"
                send_email(
                    recipient_email=user.email,
                    subject=subject,
                    html_content=html_content
                )
                
                logger.info(f"Sent invoice reminder to user {user_id} for invoice {invoice_id}")
            except Exception as e:
                logger.error(f"Error sending reminder for user {user_id}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in send_invoice_reminders task: {str(e)}")
    finally:
        db.close()

@shared_task
def generate_monthly_billing_report():
    """
    Task to generate monthly billing report for the previous month.
    This task should be scheduled to run on the 1st of each month.
    """
    logger.info("Starting task: generate_monthly_billing_report")
    
    # Calculate previous month
    today = datetime.utcnow()
    first_day_of_current_month = datetime(today.year, today.month, 1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    previous_month = last_day_of_previous_month.month
    previous_year = last_day_of_previous_month.year
    
    db = SessionLocal()
    try:
        billing_service = BillingService(db)
        
        # Generate the report
        report_html = billing_service.generate_monthly_billing_report(
            previous_year, 
            previous_month
        )
        
        # Save the report to a file or send it via email to administrators
        # This is a simplified example - in a real implementation, you might want to:
        # 1. Save the report to a database or file system
        # 2. Send the report to administrators via email
        # 3. Generate a PDF version of the report
        
        # Example: Send to administrators
        admin_users = db.query(User).filter(User.is_admin == True).all()
        for admin in admin_users:
            if admin.email:
                try:
                    subject = f"Monthly Billing Report: {previous_month}/{previous_year}"
                    send_email(
                        recipient_email=admin.email,
                        subject=subject,
                        html_content=report_html
                    )
                    logger.info(f"Sent monthly billing report to admin {admin.id}")
                except Exception as e:
                    logger.error(f"Error sending report to admin {admin.id}: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error in generate_monthly_billing_report task: {str(e)}")
    finally:
        db.close()

@shared_task
def clear_template_cache():
    """
    Task to clear the template cache periodically.
    This task should be scheduled to run weekly or after template updates.
    """
    logger.info("Starting task: clear_template_cache")
    
    try:
        from .template_service import invalidate_template_cache
        invalidate_template_cache()
        logger.info("Template cache cleared successfully")
    except Exception as e:
        logger.error(f"Error in clear_template_cache task: {str(e)}")
