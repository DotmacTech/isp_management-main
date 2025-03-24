"""
Email service for the authentication module.

This module provides functionality for sending emails for various authentication-related
actions, such as welcome emails, password reset emails, and two-factor authentication setup.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader

# Configure logging
logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails related to authentication."""

    def __init__(self):
        """Initialize the email service."""
        self.templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.example.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "user@example.com")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "password")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@example.com")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        template_name: str, 
        context: Dict[str, Any],
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email using a template.

        Args:
            to_email: The recipient's email address.
            subject: The email subject.
            template_name: The name of the template file (without extension).
            context: The context variables for the template.
            cc: Optional list of CC recipients.
            bcc: Optional list of BCC recipients.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        try:
            # Add current year to context for copyright notices
            context["current_year"] = datetime.now().year
            
            # Render the template
            template = self.env.get_template(f"{template_name}.html")
            html_content = template.render(**context)
            
            # Create the email message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to_email
            
            if cc:
                message["Cc"] = ", ".join(cc)
            if bcc:
                message["Bcc"] = ", ".join(bcc)
            
            # Attach HTML content
            message.attach(MIMEText(html_content, "html"))
            
            # Send the email
            # In production, replace this with actual SMTP sending
            # For now, we'll just log the message for development
            logger.info(f"Email would be sent to {to_email} with subject: {subject}")
            logger.debug(f"Email content: {html_content}")
            
            # Uncomment this code when ready to send real emails
            """
            import smtplib
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                recipients = [to_email]
                if cc:
                    recipients.extend(cc)
                if bcc:
                    recipients.extend(bcc)
                server.sendmail(self.from_email, recipients, message.as_string())
            """
            
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_welcome_email(self, username: str, email: str) -> bool:
        """
        Send a welcome email to a newly registered user.

        Args:
            username: The user's username.
            email: The user's email address.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        subject = "Welcome to ISP Management Platform"
        template_name = "welcome_email"
        context = {
            "username": username,
            "email": email,
            "login_url": f"{self.frontend_url}/login"
        }
        return await self.send_email(email, subject, template_name, context)

    async def send_password_reset_email(self, email: str, token: str) -> bool:
        """
        Send a password reset email.

        Args:
            email: The user's email address.
            token: The password reset token.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        subject = "Password Reset Request"
        template_name = "password_reset_email"
        reset_url = f"{self.frontend_url}/reset-password?token={token}"
        context = {
            "email": email,
            "reset_url": reset_url
        }
        return await self.send_email(email, subject, template_name, context)

    async def send_two_factor_setup_email(
        self, 
        username: str, 
        email: str, 
        qr_code: str, 
        secret_key: str,
        recovery_codes: List[str]
    ) -> bool:
        """
        Send an email with two-factor authentication setup information.

        Args:
            username: The user's username.
            email: The user's email address.
            qr_code: The QR code image as a data URL.
            secret_key: The TOTP secret key.
            recovery_codes: List of recovery codes.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        subject = "Two-Factor Authentication Setup"
        template_name = "two_factor_setup_email"
        context = {
            "username": username,
            "email": email,
            "qr_code": qr_code,
            "secret_key": secret_key,
            "recovery_codes": "<br>".join(recovery_codes)
        }
        return await self.send_email(email, subject, template_name, context)

    async def send_account_lockout_email(
        self, 
        username: str, 
        email: str, 
        ip_address: str,
        timestamp: datetime,
        location: str = "Unknown",
        device: str = "Unknown",
        lockout_duration: int = 30
    ) -> bool:
        """
        Send an email notification about account lockout due to multiple failed login attempts.

        Args:
            username: The user's username.
            email: The user's email address.
            ip_address: The IP address of the login attempt.
            timestamp: The timestamp of the lockout.
            location: The location of the login attempt (if available).
            device: The device used for the login attempt (if available).
            lockout_duration: The duration of the lockout in minutes.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        subject = "Account Security Alert"
        template_name = "account_lockout_email"
        unlock_url = f"{self.frontend_url}/unlock-account?email={email}"
        context = {
            "username": username,
            "email": email,
            "ip_address": ip_address,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "location": location,
            "device": device,
            "lockout_duration": lockout_duration,
            "unlock_url": unlock_url
        }
        return await self.send_email(email, subject, template_name, context)

# Create a singleton instance
email_service = EmailService()
