"""
This package contains schemas for the communications module.
"""
# Import schema classes from the schemas.py file
from modules.communications.schemas_module import (
    # Message schemas
    Message, MessageCreate, MessageUpdate, MessageBase, 
    MessageAttachment, MessageAttachmentCreate, MessageAttachmentBase,
    MessagePriorityEnum, MessageStatusEnum,
    
    # Notification schemas
    Notification, NotificationCreate, NotificationUpdate, NotificationBase, NotificationTypeEnum,
    
    # Announcement schemas
    Announcement, AnnouncementCreate, AnnouncementUpdate, AnnouncementBase, AnnouncementTypeEnum,
    
    # Support ticket schemas
    SupportTicket, SupportTicketCreate, SupportTicketUpdate, SupportTicketBase,
    TicketResponse, TicketResponseCreate, TicketResponseBase,
    TicketAttachment, TicketAttachmentCreate, TicketAttachmentBase,
    ResponseAttachment, ResponseAttachmentCreate, ResponseAttachmentBase,
    TicketStatusEnum, TicketCategoryEnum, TicketPriorityEnum,
    
    # Template schemas
    Template, TemplateCreate, TemplateUpdate, TemplateBase,
    
    # Delivery method
    DeliveryMethodEnum,
    
    # Response schemas
    FileUploadResponse, TicketStatistics,
    
    # External service schemas
    ExternalServiceBase, ExternalServiceCreate, ExternalServiceUpdate, ExternalService,
    
    # Webhook schemas
    WebhookBase, WebhookCreate, WebhookUpdate, Webhook,
    WebhookLogBase, WebhookLog,
    
    # Event schemas
    MessageEvent, NotificationEvent, AnnouncementEvent, TicketEvent
)

# Re-export all imported classes
__all__ = [
    # Message schemas
    'Message', 'MessageCreate', 'MessageUpdate', 'MessageBase',
    'MessageAttachment', 'MessageAttachmentCreate', 'MessageAttachmentBase',
    'MessagePriorityEnum', 'MessageStatusEnum',
    
    # Notification schemas
    'Notification', 'NotificationCreate', 'NotificationUpdate', 'NotificationBase', 'NotificationTypeEnum',
    
    # Announcement schemas
    'Announcement', 'AnnouncementCreate', 'AnnouncementUpdate', 'AnnouncementBase', 'AnnouncementTypeEnum',
    
    # Support ticket schemas
    'SupportTicket', 'SupportTicketCreate', 'SupportTicketUpdate', 'SupportTicketBase',
    'TicketResponse', 'TicketResponseCreate', 'TicketResponseBase',
    'TicketAttachment', 'TicketAttachmentCreate', 'TicketAttachmentBase',
    'ResponseAttachment', 'ResponseAttachmentCreate', 'ResponseAttachmentBase',
    'TicketStatusEnum', 'TicketCategoryEnum', 'TicketPriorityEnum',
    
    # Template schemas
    'Template', 'TemplateCreate', 'TemplateUpdate', 'TemplateBase',
    
    # Delivery method
    'DeliveryMethodEnum',
    
    # Response schemas
    'FileUploadResponse', 'TicketStatistics',
    
    # External service schemas
    'ExternalServiceBase', 'ExternalServiceCreate', 'ExternalServiceUpdate', 'ExternalService',
    
    # Webhook schemas
    'WebhookBase', 'WebhookCreate', 'WebhookUpdate', 'Webhook',
    'WebhookLogBase', 'WebhookLog',
    
    # Event schemas
    'MessageEvent', 'NotificationEvent', 'AnnouncementEvent', 'TicketEvent'
]
