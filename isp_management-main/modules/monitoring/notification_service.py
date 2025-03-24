"""
Notification Service for ISP Management Platform.

This module provides services for sending notifications through various channels:
- Email
- SMS
- Webhooks
- Slack
"""

import logging
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends

from backend_core.database import get_db
from backend_core.config import settings
from backend_core.cache import get_redis
from redis import Redis

# Configure logging
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications through various channels."""
    
    def __init__(self, db: Session = Depends(get_db), redis: Redis = Depends(get_redis)):
        """Initialize the notification service."""
        self.db = db
        self.redis = redis
        
    def send_email_notification(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        alert_data: Optional[Dict[str, Any]] = None,
        html: bool = True
    ) -> Dict[str, Any]:
        """
        Send an email notification.
        
        Args:
            recipients: List of email recipients
            subject: Email subject
            body: Email body
            alert_data: Optional alert data for tracking
            html: Whether the body is HTML
            
        Returns:
            Dictionary with sending status
        """
        if not settings.SMTP_HOST or not settings.SMTP_PORT:
            logger.warning("SMTP settings not configured, email notification not sent")
            return {"status": "error", "message": "SMTP settings not configured"}
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_SENDER
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = subject
            
            # Attach body
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
                
            # Connect to SMTP server
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                    
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    
                server.send_message(msg)
                
            logger.info(f"Email notification sent to {len(recipients)} recipients: {subject}")
            
            # Track notification in Redis for rate limiting
            self._track_notification("email", recipients, alert_data)
            
            return {
                "status": "success",
                "message": f"Email notification sent to {len(recipients)} recipients",
                "recipients": recipients
            }
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def send_sms_notification(
        self,
        recipients: List[str],
        message: str,
        alert_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send an SMS notification.
        
        Note: This is a placeholder implementation. In a real-world scenario,
        you would integrate with an SMS provider like Twilio, Nexmo, etc.
        
        Args:
            recipients: List of phone numbers
            message: SMS message
            alert_data: Optional alert data for tracking
            
        Returns:
            Dictionary with sending status
        """
        if not settings.SMS_PROVIDER_API_KEY:
            logger.warning("SMS provider not configured, SMS notification not sent")
            return {"status": "error", "message": "SMS provider not configured"}
            
        try:
            # This is a placeholder. In a real implementation, you would:
            # 1. Format the phone numbers according to your SMS provider's requirements
            # 2. Make API calls to your SMS provider
            # 3. Handle responses and errors
            
            logger.info(f"SMS notification sent to {len(recipients)} recipients: {message[:30]}...")
            
            # Track notification in Redis for rate limiting
            self._track_notification("sms", recipients, alert_data)
            
            return {
                "status": "success",
                "message": f"SMS notification sent to {len(recipients)} recipients",
                "recipients": recipients
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def send_webhook_notification(
        self,
        webhook_url: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a notification to a webhook.
        
        Args:
            webhook_url: Webhook URL
            data: Data to send
            
        Returns:
            Dictionary with sending status
        """
        try:
            # Add timestamp to data
            data["timestamp"] = datetime.utcnow().isoformat()
            
            # Send POST request to webhook URL
            response = requests.post(
                webhook_url,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            response.raise_for_status()
            
            logger.info(f"Webhook notification sent to {webhook_url}")
            
            return {
                "status": "success",
                "message": f"Webhook notification sent to {webhook_url}",
                "response_status": response.status_code
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending webhook notification: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def send_slack_notification(
        self,
        webhook_url: str,
        message: Union[str, Dict[str, Any]],
        alert_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a notification to a Slack channel using a webhook.
        
        Args:
            webhook_url: Slack webhook URL
            message: Message text or formatted Slack message payload
            alert_data: Optional alert data for tracking
            
        Returns:
            Dictionary with sending status
        """
        try:
            # Prepare payload
            if isinstance(message, str):
                payload = {"text": message}
            else:
                payload = message
                
            # Send POST request to Slack webhook URL
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            response.raise_for_status()
            
            logger.info(f"Slack notification sent to webhook {webhook_url}")
            
            return {
                "status": "success",
                "message": "Slack notification sent",
                "response_status": response.status_code
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def send_in_app_notification(
        self,
        user_ids: List[int],
        title: str,
        message: str,
        notification_type: str,
        link: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send an in-app notification to users.
        
        Args:
            user_ids: List of user IDs
            title: Notification title
            message: Notification message
            notification_type: Type of notification (e.g., 'alert', 'info')
            link: Optional link to include
            data: Optional additional data
            
        Returns:
            Dictionary with sending status
        """
        try:
            # In a real implementation, you would:
            # 1. Store the notification in the database
            # 2. Notify connected clients via WebSockets or similar
            
            # For now, we'll just log it
            logger.info(f"In-app notification sent to {len(user_ids)} users: {title}")
            
            # Publish to Redis channel for WebSocket distribution
            notification = {
                "user_ids": user_ids,
                "title": title,
                "message": message,
                "type": notification_type,
                "link": link,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.redis.publish(
                "notifications",
                json.dumps(notification)
            )
            
            return {
                "status": "success",
                "message": f"In-app notification sent to {len(user_ids)} users",
                "user_ids": user_ids
            }
            
        except Exception as e:
            logger.error(f"Error sending in-app notification: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _track_notification(
        self,
        channel: str,
        recipients: List[str],
        alert_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track a notification in Redis for rate limiting.
        
        Args:
            channel: Notification channel (email, sms, etc.)
            recipients: List of recipients
            alert_data: Optional alert data
        """
        now = datetime.utcnow().timestamp()
        
        # If alert data is provided, track by alert ID to prevent duplicate notifications
        if alert_data and "alert_id" in alert_data:
            alert_id = alert_data["alert_id"]
            key = f"notification:{channel}:alert:{alert_id}"
            
            # Store in Redis with 24-hour expiry
            self.redis.setex(key, 86400, now)
            
        # Track by recipient for rate limiting
        for recipient in recipients:
            key = f"notification:{channel}:recipient:{recipient}"
            
            # Store in Redis with 1-hour expiry
            self.redis.setex(key, 3600, now)
    
    def check_rate_limit(
        self,
        channel: str,
        recipient: str,
        limit_period_seconds: int = 3600
    ) -> bool:
        """
        Check if a recipient has exceeded the rate limit for a channel.
        
        Args:
            channel: Notification channel (email, sms, etc.)
            recipient: Recipient identifier
            limit_period_seconds: Period for rate limiting in seconds
            
        Returns:
            True if rate limited, False otherwise
        """
        key = f"notification:{channel}:recipient:{recipient}"
        last_notification = self.redis.get(key)
        
        if not last_notification:
            return False
            
        last_time = float(last_notification)
        now = datetime.utcnow().timestamp()
        
        # Check if the time difference is less than the limit period
        return (now - last_time) < limit_period_seconds
    
    def check_alert_notification_sent(
        self,
        channel: str,
        alert_id: int
    ) -> bool:
        """
        Check if a notification has already been sent for an alert.
        
        Args:
            channel: Notification channel (email, sms, etc.)
            alert_id: Alert ID
            
        Returns:
            True if notification already sent, False otherwise
        """
        key = f"notification:{channel}:alert:{alert_id}"
        return self.redis.exists(key) > 0
