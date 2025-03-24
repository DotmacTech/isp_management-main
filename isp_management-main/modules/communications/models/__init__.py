"""
Models for the communications module.

This package contains models for the communications module.
"""

# Import models directly from the parent directory's models.py file
import sys
import os
from importlib.util import spec_from_file_location, module_from_spec

# Get the absolute path to the models.py file in the parent directory
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
models_path = os.path.join(parent_dir, 'models.py')

# Load the models.py module dynamically
spec = spec_from_file_location('models_module', models_path)
models_module = module_from_spec(spec)
spec.loader.exec_module(models_module)

# Import all models from the dynamically loaded module
Message = models_module.Message
MessageAttachment = models_module.MessageAttachment
MessagePriority = models_module.MessagePriority
MessageStatus = models_module.MessageStatus
Notification = models_module.Notification
NotificationType = models_module.NotificationType
Announcement = models_module.Announcement
AnnouncementType = models_module.AnnouncementType
SupportTicket = models_module.SupportTicket
TicketResponse = models_module.TicketResponse
TicketAttachment = models_module.TicketAttachment
ResponseAttachment = models_module.ResponseAttachment
TicketStatus = models_module.TicketStatus
TicketPriority = models_module.TicketPriority
TicketCategory = models_module.TicketCategory
Template = models_module.Template
Webhook = models_module.Webhook
WebhookLog = models_module.WebhookLog
ExternalService = models_module.ExternalService
DeliveryMethod = models_module.DeliveryMethod

# Re-export all imported models
__all__ = [
    # Message models
    'Message', 'MessageAttachment', 'MessagePriority', 'MessageStatus',
    
    # Notification models
    'Notification', 'NotificationType',
    
    # Announcement models
    'Announcement', 'AnnouncementType',
    
    # Support ticket models
    'SupportTicket', 'TicketResponse', 'TicketAttachment', 'ResponseAttachment',
    'TicketStatus', 'TicketPriority', 'TicketCategory',
    
    # Template models
    'Template',
    
    # Webhook models
    'Webhook', 'WebhookLog',
    
    # External service models
    'ExternalService',
    
    # Delivery method
    'DeliveryMethod'
]
