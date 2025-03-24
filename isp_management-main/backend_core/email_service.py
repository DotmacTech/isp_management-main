"""
Email service for the ISP Management Platform.
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import List, Optional

logger = logging.getLogger(__name__)

# Email configuration from environment variables
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.example.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'noreply@example.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'password')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'ISP Management <noreply@example.com>')
USE_TLS = os.environ.get('SMTP_USE_TLS', 'True').lower() in ('true', '1', 't')


class EmailService:
    """
    Service for sending emails in the ISP Management Platform.
    Provides methods for sending various types of emails including
    authentication-related notifications.
    """
    
    @staticmethod
    def send_email(
        recipient_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[tuple]] = None
    ) -> bool:
        """
        Send an email using the configured SMTP server.
        
        Args:
            recipient_email: Email address of the recipient
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content of the email (optional)
            from_email: Sender email address (optional, defaults to DEFAULT_FROM_EMAIL)
            cc: List of CC recipients (optional)
            bcc: List of BCC recipients (optional)
            attachments: List of attachments as tuples (filename, content_bytes, mimetype)
            
        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        if not recipient_email:
            logger.error("Recipient email is required")
            return False
        
        # Use default text content if not provided
        if text_content is None:
            # Simple HTML to text conversion
            text_content = html_content.replace('<br>', '\n').replace('<p>', '\n').replace('</p>', '\n')
            # Remove all other HTML tags
            import re
            text_content = re.sub(r'<[^>]*>', '', text_content)
        
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email or DEFAULT_FROM_EMAIL
        msg['To'] = recipient_email
        
        # Add CC recipients if provided
        if cc:
            msg['Cc'] = ', '.join(cc)
        
        # Add BCC recipients if provided
        if bcc:
            msg['Bcc'] = ', '.join(bcc)
        
        # Attach parts
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Add attachments if provided
        if attachments:
            for attachment in attachments:
                filename, content, mimetype = attachment
                part = MIMEApplication(content)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                if mimetype:
                    part.add_header('Content-Type', mimetype)
                msg.attach(part)
        
        try:
            # Connect to SMTP server
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.ehlo()
            
            # Use TLS if configured
            if USE_TLS:
                server.starttls()
                server.ehlo()
            
            # Login if credentials are provided
            if SMTP_USERNAME and SMTP_PASSWORD:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            
            # Get all recipients
            all_recipients = [recipient_email]
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)
            
            # Send email
            server.sendmail(
                from_email or DEFAULT_FROM_EMAIL,
                all_recipients,
                msg.as_string()
            )
            
            # Close connection
            server.quit()
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False
    
    @classmethod
    def send_password_reset_email(cls, email: str, reset_token: str, username: str) -> bool:
        """
        Send a password reset email.
        
        Args:
            email: Recipient email address
            reset_token: Password reset token
            username: Username of the user
            
        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        subject = "Password Reset Request"
        reset_url = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={reset_token}"
        
        html_content = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hello {username},</p>
                <p>We received a request to reset your password. If you didn't make this request, you can ignore this email.</p>
                <p>To reset your password, click the link below:</p>
                <p><a href="{reset_url}">Reset Password</a></p>
                <p>This link will expire in 30 minutes.</p>
                <p>Thank you,<br>ISP Management Team</p>
            </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request
        
        Hello {username},
        
        We received a request to reset your password. If you didn't make this request, you can ignore this email.
        
        To reset your password, visit this link:
        {reset_url}
        
        This link will expire in 30 minutes.
        
        Thank you,
        ISP Management Team
        """
        
        return cls.send_email(
            recipient_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    @classmethod
    def send_mfa_setup_email(cls, email: str, username: str) -> bool:
        """
        Send an email notification about MFA setup.
        
        Args:
            email: Recipient email address
            username: Username of the user
            
        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        subject = "Multi-Factor Authentication Enabled"
        
        html_content = f"""
        <html>
            <body>
                <h2>Multi-Factor Authentication Enabled</h2>
                <p>Hello {username},</p>
                <p>Multi-factor authentication has been enabled for your account.</p>
                <p>If you did not make this change, please contact support immediately.</p>
                <p>Thank you,<br>ISP Management Team</p>
            </body>
        </html>
        """
        
        text_content = f"""
        Multi-Factor Authentication Enabled
        
        Hello {username},
        
        Multi-factor authentication has been enabled for your account.
        
        If you did not make this change, please contact support immediately.
        
        Thank you,
        ISP Management Team
        """
        
        return cls.send_email(
            recipient_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )


def send_invoice_email(
    recipient_email: str,
    invoice_id: int,
    invoice_html: str,
    invoice_pdf: Optional[bytes] = None
) -> bool:
    """
    Send an invoice email to a customer.
    
    Args:
        recipient_email: Email address of the recipient
        invoice_id: ID of the invoice
        invoice_html: HTML content of the invoice
        invoice_pdf: PDF content of the invoice (optional)
        
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    subject = f"Invoice #{invoice_id} - Payment Required"
    
    attachments = []
    if invoice_pdf:
        attachments.append((f"invoice_{invoice_id}.pdf", invoice_pdf, 'application/pdf'))
    
    return EmailService.send_email(
        recipient_email=recipient_email,
        subject=subject,
        html_content=invoice_html,
        attachments=attachments
    )


def send_payment_confirmation_email(
    recipient_email: str,
    invoice_id: int,
    payment_amount: float,
    payment_method: str,
    transaction_id: str
) -> bool:
    """
    Send a payment confirmation email to a customer.
    
    Args:
        recipient_email: Email address of the recipient
        invoice_id: ID of the invoice
        payment_amount: Amount paid
        payment_method: Payment method used
        transaction_id: Transaction ID
        
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    subject = f"Payment Confirmation - Invoice #{invoice_id}"
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .content {{ margin-bottom: 30px; }}
            .footer {{ text-align: center; font-size: 12px; color: #777; margin-top: 30px; }}
            .details {{ background-color: #f9f9f9; padding: 15px; border: 1px solid #ddd; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Payment Confirmation</h2>
            </div>
            <div class="content">
                <p>Dear Customer,</p>
                <p>We have received your payment for Invoice #{invoice_id}. Thank you for your prompt payment.</p>
                <div class="details">
                    <p><strong>Invoice Number:</strong> #{invoice_id}</p>
                    <p><strong>Payment Amount:</strong> ${payment_amount:.2f}</p>
                    <p><strong>Payment Method:</strong> {payment_method}</p>
                    <p><strong>Transaction ID:</strong> {transaction_id}</p>
                    <p><strong>Date:</strong> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                <p>If you have any questions regarding this payment, please contact our billing department.</p>
            </div>
            <div class="footer">
                <p>Thank you for your business!</p>
                <p>ISP Management Team</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return EmailService.send_email(
        recipient_email=recipient_email,
        subject=subject,
        html_content=html_content
    )


def send_bulk_emails(
    recipients: List[str],
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    from_email: Optional[str] = None,
    attachments: Optional[List[tuple]] = None
) -> dict:
    """
    Send bulk emails to multiple recipients.
    
    Args:
        recipients: List of recipient email addresses
        subject: Email subject
        html_content: HTML content of the email
        text_content: Plain text content of the email (optional)
        from_email: Sender email address (optional, defaults to DEFAULT_FROM_EMAIL)
        attachments: List of attachments as tuples (filename, content_bytes, mimetype)
        
    Returns:
        dict: Dictionary with email addresses as keys and success status as values
    """
    results = {}
    
    for recipient in recipients:
        success = EmailService.send_email(
            recipient_email=recipient,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            from_email=from_email,
            attachments=attachments
        )
        results[recipient] = success
    
    return results
