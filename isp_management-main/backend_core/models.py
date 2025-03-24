from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Numeric, Text, JSON, Enum, Float, BigInteger
from sqlalchemy.orm import relationship, backref
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    role = Column(String(32), default="customer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # MFA fields
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)
    mfa_device_tokens = relationship("MFADeviceToken", back_populates="user")
    
    # Security fields
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    password_changed_at = Column(DateTime, nullable=True)
    account_locked_until = Column(DateTime, nullable=True)
    
    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    
    # Email verification
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_sent_at = Column(DateTime, nullable=True)

    # Relationships
    radius_profile = relationship("RadiusProfile", back_populates="user", uselist=False)
    invoices = relationship("Invoice", back_populates="user")
    customer_profile = relationship("Customer", back_populates="user", uselist=False)
    reseller_profile = relationship("Reseller", back_populates="user", uselist=False)
    credit_notes = relationship("CreditNote", back_populates="user")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    tariff_plans = relationship("UserTariffPlan", back_populates="user")

class RadiusProfile(Base):
    __tablename__ = "radius_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    speed_limit = Column(Integer, default=0)  # 0 means unlimited
    data_cap = Column(Integer, default=0)     # 0 means unlimited
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields for expanded RADIUS module
    service_type = Column(String(32), default="Framed-User")
    simultaneous_use = Column(Integer, default=1)
    acct_interim_interval = Column(Integer, default=300)  # 5 minutes
    session_timeout = Column(Integer, default=0)  # 0 means no timeout
    idle_timeout = Column(Integer, default=0)     # 0 means no timeout
    bandwidth_policy_id = Column(Integer, ForeignKey("radius_bandwidth_policies.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="radius_profile")
    accounting_records = relationship("RadiusAccounting", back_populates="profile")
    bandwidth_policy = relationship("RadiusBandwidthPolicy", back_populates="profiles")
    profile_attributes = relationship("RadiusProfileAttribute", back_populates="profile", cascade="all, delete-orphan")

class RadiusAccounting(Base):
    __tablename__ = "radius_accounting"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True)
    profile_id = Column(Integer, ForeignKey("radius_profiles.id"))
    nas_ip_address = Column(String(45))
    bytes_in = Column(Integer, default=0)
    bytes_out = Column(Integer, default=0)
    session_time = Column(Integer, default=0)
    start_time = Column(DateTime)
    stop_time = Column(DateTime, nullable=True)
    terminate_cause = Column(String(32), nullable=True)
    
    # Additional fields for expanded RADIUS module
    nas_id = Column(Integer, ForeignKey("nas_devices.id"), nullable=True)
    framed_ip_address = Column(String(45), nullable=True)
    framed_protocol = Column(String(32), nullable=True)
    calling_station_id = Column(String(64), nullable=True)  # Usually MAC address
    called_station_id = Column(String(64), nullable=True)   # Usually NAS MAC or ID
    acct_authentic = Column(String(32), nullable=True)      # RADIUS, Local, Remote
    acct_input_octets = Column(Integer, default=0)
    acct_output_octets = Column(Integer, default=0)
    acct_input_packets = Column(Integer, default=0)
    acct_output_packets = Column(Integer, default=0)
    acct_session_id = Column(String(64), nullable=True)
    acct_multi_session_id = Column(String(64), nullable=True)
    acct_link_count = Column(Integer, default=0)
    acct_interim_updates = Column(Integer, default=0)
    last_interim_update = Column(DateTime, nullable=True)

    # Relationships
    profile = relationship("RadiusProfile", back_populates="accounting_records")
    nas_device = relationship("NasDevice", back_populates="accounting_records")

class NasDevice(Base):
    __tablename__ = "nas_devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    ip_address = Column(String(45), unique=True, nullable=False, index=True)
    secret = Column(String(128), nullable=False)  # Encrypted shared secret
    vendor = Column(String(64), nullable=False, index=True)
    model = Column(String(64), nullable=True)
    location = Column(String(128), nullable=True)
    type = Column(String(32), default="other")  # router, switch, ap, etc.
    description = Column(Text, nullable=True)
    ports = Column(Integer, default=0)
    community = Column(String(64), nullable=True)  # For SNMP
    version = Column(String(32), nullable=True)    # Firmware/OS version
    config_json = Column(JSON, nullable=True)      # Additional configuration
    last_seen = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    accounting_records = relationship("RadiusAccounting", back_populates="nas_device")
    vendor_attributes = relationship("NasVendorAttribute", back_populates="nas_device", cascade="all, delete-orphan")

class NasVendorAttribute(Base):
    __tablename__ = "nas_vendor_attributes"

    id = Column(Integer, primary_key=True, index=True)
    nas_id = Column(Integer, ForeignKey("nas_devices.id"), nullable=False)
    attribute_name = Column(String(64), nullable=False)
    attribute_value = Column(String(255), nullable=False)
    vendor_type = Column(Integer, nullable=True)
    vendor_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    nas_device = relationship("NasDevice", back_populates="vendor_attributes")

class RadiusBandwidthPolicy(Base):
    __tablename__ = "radius_bandwidth_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    download_rate = Column(Integer, nullable=False)  # in kbps
    upload_rate = Column(Integer, nullable=False)    # in kbps
    burst_download_rate = Column(Integer, nullable=True)  # in kbps
    burst_upload_rate = Column(Integer, nullable=True)    # in kbps
    burst_threshold = Column(Integer, nullable=True)      # in bytes
    burst_time = Column(Integer, nullable=True)           # in seconds
    priority = Column(Integer, default=8)                 # 1-8, 1 is highest
    time_based_limits = Column(JSON, nullable=True)       # For time-of-day based limits
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profiles = relationship("RadiusProfile", back_populates="bandwidth_policy")

class RadiusProfileAttribute(Base):
    __tablename__ = "radius_profile_attributes"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("radius_profiles.id"), nullable=False)
    attribute_name = Column(String(64), nullable=False)
    attribute_value = Column(String(255), nullable=False)
    vendor_id = Column(Integer, nullable=True)
    vendor_type = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("RadiusProfile", back_populates="profile_attributes")

class RadiusCoALog(Base):
    __tablename__ = "radius_coa_logs"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("radius_profiles.id"), nullable=False)
    nas_id = Column(Integer, ForeignKey("nas_devices.id"), nullable=False)
    session_id = Column(String(64), nullable=True)
    coa_type = Column(String(32), nullable=False)  # disconnect, update, etc.
    attributes_changed = Column(JSON, nullable=True)
    result = Column(String(32), nullable=True)  # success, failure, timeout
    error_message = Column(Text, nullable=True)
    initiated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    profile = relationship("RadiusProfile")
    nas_device = relationship("NasDevice")
    initiator = relationship("User")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(32), default="unpaid", index=True)
    due_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    paid_at = Column(DateTime, nullable=True)
    billing_country = Column(String(2), nullable=False, default="GB", index=True)

    # Relationships
    user = relationship("User", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")
    discounts = relationship("InvoiceDiscount", back_populates="invoice")
    taxes = relationship("InvoiceTax", back_populates="invoice")
    credit_note_applications = relationship("CreditNoteApplication", back_populates="invoice")
    
    def to_dict(self):
        """Convert invoice to dictionary for caching."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": str(self.amount),
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "billing_country": self.billing_country
        }

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(32))  # credit_card, bank_transfer, etc.
    transaction_id = Column(String(128), unique=True)
    status = Column(String(32), default="pending")  # pending, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")

class TariffPlan(Base):
    """Model representing a service plan with associated tariffs and policies."""
    __tablename__ = "tariff_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    billing_cycle = Column(String, nullable=False)  # monthly, quarterly, yearly
    is_active = Column(Boolean, default=True)
    
    # Bandwidth limits
    download_speed = Column(Integer, nullable=False)  # in kbps
    upload_speed = Column(Integer, nullable=False)    # in kbps
    
    # Data caps and FUP
    data_cap = Column(BigInteger, nullable=True)      # in bytes, null means unlimited
    fup_threshold = Column(BigInteger, nullable=True) # in bytes, threshold for Fair Usage Policy
    
    # Throttling details
    throttle_speed_download = Column(Integer, nullable=True)  # in kbps after FUP
    throttle_speed_upload = Column(Integer, nullable=True)    # in kbps after FUP
    
    # Time restrictions
    time_restrictions = Column(JSON, nullable=True)  # JSON for time-based restrictions
    
    # Additional features
    features = Column(JSON, nullable=True)           # JSON for additional features
    
    # Radius policy integration
    radius_policy_id = Column(Integer, ForeignKey("radius_bandwidth_policies.id"), nullable=True)
    throttled_radius_policy_id = Column(Integer, ForeignKey("radius_bandwidth_policies.id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("UserTariffPlan", back_populates="tariff_plan")
    radius_policy = relationship("RadiusBandwidthPolicy", foreign_keys=[radius_policy_id])
    throttled_radius_policy = relationship("RadiusBandwidthPolicy", foreign_keys=[throttled_radius_policy_id])

class UserTariffPlan(Base):
    """Model representing the association between a user and a tariff plan."""
    __tablename__ = "user_tariff_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tariff_plan_id = Column(Integer, ForeignKey("tariff_plans.id"), nullable=False)
    
    # Status
    status = Column(String, nullable=False, default="active")  # active, suspended, cancelled
    
    # Billing details
    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)  # null means ongoing
    
    # Usage tracking
    current_cycle_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    current_cycle_end = Column(DateTime, nullable=True)
    
    # Data usage
    data_used = Column(BigInteger, default=0)  # in bytes
    is_throttled = Column(Boolean, default=False)
    throttled_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="tariff_plans")
    tariff_plan = relationship("TariffPlan", back_populates="users")
    usage_records = relationship("UserUsageRecord", back_populates="user_tariff_plan")

class UserUsageRecord(Base):
    """Model for tracking detailed usage records for users."""
    __tablename__ = "user_usage_records"

    id = Column(Integer, primary_key=True, index=True)
    user_tariff_plan_id = Column(Integer, ForeignKey("user_tariff_plans.id"), nullable=False)
    
    # Usage details
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    download_bytes = Column(BigInteger, default=0)
    upload_bytes = Column(BigInteger, default=0)
    total_bytes = Column(BigInteger, default=0)
    
    # Source of the usage data
    source = Column(String, nullable=False)  # radius, netflow, etc.
    session_id = Column(String, nullable=True)  # reference to the session if applicable
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_tariff_plan = relationship("UserTariffPlan", back_populates="usage_records")

class TariffPolicyAction(Base):
    """Model representing actions to be taken when policy thresholds are reached."""
    __tablename__ = "tariff_policy_actions"

    id = Column(Integer, primary_key=True, index=True)
    tariff_plan_id = Column(Integer, ForeignKey("tariff_plans.id"), nullable=False)
    
    # Trigger conditions
    trigger_type = Column(String, nullable=False)  # data_cap, fup, time_restriction
    threshold_value = Column(BigInteger, nullable=True)  # value for the trigger
    
    # Action details
    action_type = Column(String, nullable=False)  # notify, throttle, block, charge
    action_params = Column(JSON, nullable=True)  # Parameters for the action
    
    # Notification template if applicable
    notification_template_id = Column(Integer, ForeignKey("notification_templates.id"), nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tariff_plan = relationship("TariffPlan")
    notification_template = relationship("NotificationTemplate")

class TariffPlanChange(Base):
    """Model for tracking tariff plan changes for users."""
    __tablename__ = "tariff_plan_changes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Plan change details
    previous_plan_id = Column(Integer, ForeignKey("tariff_plans.id"), nullable=True)
    new_plan_id = Column(Integer, ForeignKey("tariff_plans.id"), nullable=False)
    
    # Change metadata
    change_type = Column(String, nullable=False)  # upgrade, downgrade, initial
    requested_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    effective_date = Column(DateTime, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, processed, cancelled
    
    # Billing adjustments
    prorated_credit = Column(Numeric(10, 2), nullable=True)
    prorated_charge = Column(Numeric(10, 2), nullable=True)
    
    # Change reason and notes
    reason = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    previous_plan = relationship("TariffPlan", foreign_keys=[previous_plan_id])
    new_plan = relationship("TariffPlan", foreign_keys=[new_plan_id])

class NotificationTemplate(Base):
    """Model for notification templates used in tariff policy actions."""
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    template_type = Column(String, nullable=False)  # email, sms, in-app
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(128), unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("users.id"))

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    full_name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False)
    phone = Column(String(32), nullable=True)
    address = Column(Text, nullable=True)
    status = Column(String(32), default="pending_activation")  # active, suspended, pending_activation, canceled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="customer_profile")
    tickets = relationship("Ticket", back_populates="customer")
    reseller_customers = relationship("ResellerCustomer", back_populates="customer")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(32), default="p3")  # p1, p2, p3, p4
    status = Column(String(32), default="new")  # new, assigned, in_progress, pending_customer, resolved, closed
    source = Column(String(32), default="customer_portal")  # customer_portal, email, phone, chat, social, system
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="tickets")
    assigned_agent = relationship("User", foreign_keys=[assigned_to])
    comments = relationship("TicketComment", back_populates="ticket")

class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    comment = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)  # True if only visible to staff
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket = relationship("Ticket", back_populates="comments")
    user = relationship("User")

class Reseller(Base):
    __tablename__ = "resellers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    company_name = Column(String(128), nullable=False)
    contact_person = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False)
    phone = Column(String(32), nullable=False)
    address = Column(Text, nullable=True)
    tax_id = Column(String(64), nullable=True)
    status = Column(String(32), default="pending_approval")  # active, suspended, pending_approval, terminated
    tier = Column(String(32), default="bronze")  # bronze, silver, gold, platinum
    commission_type = Column(String(32), default="percentage")  # percentage, fixed, tiered
    commission_rate = Column(Float, default=0.0)
    credit_limit = Column(Float, default=0.0)
    current_balance = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="reseller_profile")
    customers = relationship("ResellerCustomer", back_populates="reseller")
    transactions = relationship("ResellerTransaction", back_populates="reseller")
    commission_rules = relationship("ResellerCommissionRule", back_populates="reseller")

class ResellerCustomer(Base):
    __tablename__ = "reseller_customers"

    id = Column(Integer, primary_key=True, index=True)
    reseller_id = Column(Integer, ForeignKey("resellers.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    reseller = relationship("Reseller", back_populates="customers")
    customer = relationship("Customer", back_populates="reseller_customers")

class ResellerTransaction(Base):
    __tablename__ = "reseller_transactions"

    id = Column(Integer, primary_key=True, index=True)
    reseller_id = Column(Integer, ForeignKey("resellers.id"))
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(32), nullable=False)  # commission, payment, adjustment, withdrawal
    description = Column(Text, nullable=False)
    reference_id = Column(String(128), nullable=True)  # e.g., invoice ID, payment ID
    balance_after = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    reseller = relationship("Reseller", back_populates="transactions")

class ResellerCommissionRule(Base):
    __tablename__ = "reseller_commission_rules"

    id = Column(Integer, primary_key=True, index=True)
    reseller_id = Column(Integer, ForeignKey("resellers.id"))
    tariff_plan_id = Column(Integer, ForeignKey("tariff_plans.id"))
    commission_type = Column(String(32), nullable=False)  # percentage, fixed, tiered
    commission_rate = Column(Float, nullable=False)
    min_customers = Column(Integer, nullable=True)  # For tiered commission
    max_customers = Column(Integer, nullable=True)  # For tiered commission
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reseller = relationship("Reseller", back_populates="commission_rules")
    tariff_plan = relationship("TariffPlan")

class Discount(Base):
    __tablename__ = "discounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    discount_type = Column(String(32), nullable=False, index=True)
    value = Column(Numeric(10, 2), nullable=False)
    is_percentage = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    valid_from = Column(DateTime, nullable=False, index=True)
    valid_to = Column(DateTime, nullable=True, index=True)
    applicable_plans = Column(JSON, nullable=True)  # List of tariff plan IDs
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applied_discounts = relationship("InvoiceDiscount", back_populates="discount")
    
    def to_dict(self):
        """Convert discount to dictionary for caching."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "discount_type": self.discount_type,
            "value": str(self.value),
            "is_percentage": self.is_percentage,
            "is_active": self.is_active,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "applicable_plans": self.applicable_plans,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class InvoiceDiscount(Base):
    __tablename__ = "invoice_discounts"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    discount_id = Column(Integer, ForeignKey("discounts.id"))
    amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="discounts")
    discount = relationship("Discount", back_populates="applied_discounts")

class CreditNote(Base):
    __tablename__ = "credit_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    remaining_amount = Column(Numeric(10, 2), nullable=False)
    reason = Column(String(255), nullable=False)
    reference_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    status = Column(String(20), default="issued", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    applied_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="credit_notes")
    reference_invoice = relationship("Invoice", foreign_keys=[reference_invoice_id])
    invoice_applications = relationship("CreditNoteApplication", back_populates="credit_note")
    
    def to_dict(self):
        """Convert credit note to dictionary for caching."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": str(self.amount),
            "remaining_amount": str(self.remaining_amount),
            "reason": self.reason,
            "reference_invoice_id": self.reference_invoice_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None
        }

class CreditNoteApplication(Base):
    __tablename__ = "credit_note_applications"

    id = Column(Integer, primary_key=True, index=True)
    credit_note_id = Column(Integer, ForeignKey("credit_notes.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    credit_note = relationship("CreditNote", back_populates="invoice_applications")
    invoice = relationship("Invoice", back_populates="credit_note_applications")

class TaxRate(Base):
    __tablename__ = "tax_rates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    rate = Column(Numeric(5, 2), nullable=False)  # Percentage, e.g., 7.5 for 7.5%
    country = Column(String(64), nullable=False, index=True)
    region = Column(String(128), nullable=True, index=True)
    is_default = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert tax rate to dictionary for caching."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rate": str(self.rate),
            "country": self.country,
            "region": self.region,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class InvoiceTax(Base):
    __tablename__ = "invoice_taxes"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    tax_rate_id = Column(Integer, ForeignKey("tax_rates.id"))
    taxable_amount = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="taxes")
    tax_rate = relationship("TaxRate")

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    access_token = Column(String(512), nullable=True)
    refresh_token = Column(String(512), nullable=True)
    
    # Device information
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(512), nullable=True)
    device_info = Column(String(255), nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    terminated_at = Column(DateTime, nullable=True)
    termination_reason = Column(String(50), nullable=True)
    
    # MFA status for this session
    mfa_verified = Column(Boolean, default=False)
    mfa_verified_at = Column(DateTime, nullable=True)
    remember_device = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, session_id={self.session_id})>"

class MFADeviceToken(Base):
    """Model for storing MFA device tokens for remembered devices."""
    __tablename__ = "mfa_device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="mfa_device_tokens")
    
    def __repr__(self):
        return f"<MFADeviceToken(id={self.id}, user_id={self.user_id})>"

class AuditLog(Base):
    """Model for storing audit logs of user activities."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=True)
    username = Column(String(100), index=True, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(20), nullable=False)
    details = Column(Text, nullable=True)
    severity = Column(String(20), default="info")
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(50), nullable=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, user_id={self.user_id})>"

class TimestampMixin:
    """Mixin class to add created_at and updated_at columns to models."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class ResellerHierarchy(Base, TimestampMixin):
    __tablename__ = "reseller_hierarchy"

    id = Column(Integer, primary_key=True, index=True)
    parent_reseller_id = Column(Integer, ForeignKey("resellers.id"), nullable=False)
    child_reseller_id = Column(Integer, ForeignKey("resellers.id"), nullable=False)
    relationship_type = Column(String(32), nullable=False)  # direct, master, sub_reseller
    commission_share_percentage = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)

    # Relationships
    parent_reseller = relationship("Reseller", foreign_keys=[parent_reseller_id], backref="child_resellers")
    child_reseller = relationship("Reseller", foreign_keys=[child_reseller_id], backref="parent_resellers")

class ResellerNotification(Base, TimestampMixin):
    __tablename__ = "reseller_notifications"

    id = Column(Integer, primary_key=True, index=True)
    reseller_id = Column(Integer, ForeignKey("resellers.id"), nullable=False)
    notification_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    data = Column(JSON, nullable=True)

    # Relationships
    reseller = relationship("Reseller", backref="notifications")

class ResellerPortalSettings(Base, TimestampMixin):
    __tablename__ = "reseller_portal_settings"

    id = Column(Integer, primary_key=True, index=True)
    reseller_id = Column(Integer, ForeignKey("resellers.id"), unique=True, nullable=False)
    dashboard_widgets = Column(JSON, nullable=True)
    notification_preferences = Column(JSON, nullable=True)
    display_preferences = Column(JSON, nullable=True)

    # Relationships
    reseller = relationship("Reseller", backref=backref("portal_settings", uselist=False))

class ResellerTierBenefit(Base, TimestampMixin):
    __tablename__ = "reseller_tier_benefits"

    id = Column(Integer, primary_key=True, index=True)
    tier = Column(String(32), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    commission_multiplier = Column(Float, default=1.0)
    features = Column(JSON, nullable=True)
    requirements = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)

class ResellerCommissionPayout(Base, TimestampMixin):
    __tablename__ = "reseller_commission_payouts"

    id = Column(Integer, primary_key=True, index=True)
    reseller_id = Column(Integer, ForeignKey("resellers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    status = Column(String(32), default="pending")  # pending, processing, completed, failed
    payment_method = Column(String(64), nullable=True)
    payment_reference = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    reseller = relationship("Reseller", backref="commission_payouts")
    transactions = relationship("ResellerTransaction", secondary="reseller_payout_transactions")

class ResellerPayoutTransaction(Base):
    __tablename__ = "reseller_payout_transactions"

    payout_id = Column(Integer, ForeignKey("reseller_commission_payouts.id"), primary_key=True)
    transaction_id = Column(Integer, ForeignKey("reseller_transactions.id"), primary_key=True)
