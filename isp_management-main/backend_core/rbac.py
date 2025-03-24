"""
Role-Based Access Control (RBAC) system for the ISP Management Platform.
"""
from enum import Enum
from typing import Dict, List, Set, Optional
import json
from sqlalchemy.orm import Session
from pydantic import BaseModel
from redis import Redis
import os

from backend_core.models import User, SystemConfig

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

# Cache keys
PERMISSIONS_CACHE_KEY = "rbac:permissions"
ROLES_CACHE_KEY = "rbac:roles"
ROLE_HIERARCHY_CACHE_KEY = "rbac:role_hierarchy"
USER_PERMISSIONS_CACHE_PREFIX = "rbac:user_permissions:"

class Permission(str, Enum):
    """Permissions available in the system."""
    # User management
    VIEW_USERS = "view_users"
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    
    # Customer management
    VIEW_CUSTOMERS = "view_customers"
    CREATE_CUSTOMER = "create_customer"
    UPDATE_CUSTOMER = "update_customer"
    DELETE_CUSTOMER = "delete_customer"
    
    # Billing
    VIEW_INVOICES = "view_invoices"
    CREATE_INVOICE = "create_invoice"
    UPDATE_INVOICE = "update_invoice"
    DELETE_INVOICE = "delete_invoice"
    PROCESS_PAYMENT = "process_payment"
    MANAGE_DISCOUNTS = "manage_discounts"
    MANAGE_CREDIT_NOTES = "manage_credit_notes"
    MANAGE_TAX_RATES = "manage_tax_rates"
    
    # Tariff management
    VIEW_TARIFFS = "view_tariffs"
    CREATE_TARIFF = "create_tariff"
    UPDATE_TARIFF = "update_tariff"
    DELETE_TARIFF = "delete_tariff"
    
    # RADIUS & AAA
    VIEW_RADIUS_PROFILES = "view_radius_profiles"
    CREATE_RADIUS_PROFILE = "create_radius_profile"
    UPDATE_RADIUS_PROFILE = "update_radius_profile"
    DELETE_RADIUS_PROFILE = "delete_radius_profile"
    VIEW_ACCOUNTING = "view_accounting"
    
    # Monitoring
    VIEW_SYSTEM_METRICS = "view_system_metrics"
    VIEW_USER_METRICS = "view_user_metrics"
    CONFIGURE_ALERTS = "configure_alerts"
    
    # Reseller management
    VIEW_RESELLERS = "view_resellers"
    CREATE_RESELLER = "create_reseller"
    UPDATE_RESELLER = "update_reseller"
    DELETE_RESELLER = "delete_reseller"
    MANAGE_RESELLER_COMMISSIONS = "manage_reseller_commissions"
    
    # Support tickets
    VIEW_ALL_TICKETS = "view_all_tickets"
    VIEW_OWN_TICKETS = "view_own_tickets"
    CREATE_TICKET = "create_ticket"
    UPDATE_TICKET = "update_ticket"
    ASSIGN_TICKET = "assign_ticket"
    CLOSE_TICKET = "close_ticket"
    
    # System configuration
    VIEW_SYSTEM_CONFIG = "view_system_config"
    UPDATE_SYSTEM_CONFIG = "update_system_config"
    
    # API access
    API_ACCESS = "api_access"
    
    # Logging
    VIEW_LOGS = "view_logs"
    CONFIGURE_LOGGING = "configure_logging"

class PermissionCategory(str, Enum):
    """Categories for organizing permissions."""
    USER_MANAGEMENT = "User Management"
    CUSTOMER_MANAGEMENT = "Customer Management"
    BILLING = "Billing"
    TARIFF_MANAGEMENT = "Tariff Management"
    RADIUS_AAA = "RADIUS & AAA"
    MONITORING = "Monitoring"
    RESELLER_MANAGEMENT = "Reseller Management"
    SUPPORT = "Support"
    SYSTEM = "System"
    API = "API"
    LOGGING = "Logging"

# Permission category mapping
PERMISSION_CATEGORIES: Dict[PermissionCategory, List[Permission]] = {
    PermissionCategory.USER_MANAGEMENT: [
        Permission.VIEW_USERS,
        Permission.CREATE_USER,
        Permission.UPDATE_USER,
        Permission.DELETE_USER,
    ],
    PermissionCategory.CUSTOMER_MANAGEMENT: [
        Permission.VIEW_CUSTOMERS,
        Permission.CREATE_CUSTOMER,
        Permission.UPDATE_CUSTOMER,
        Permission.DELETE_CUSTOMER,
    ],
    PermissionCategory.BILLING: [
        Permission.VIEW_INVOICES,
        Permission.CREATE_INVOICE,
        Permission.UPDATE_INVOICE,
        Permission.DELETE_INVOICE,
        Permission.PROCESS_PAYMENT,
        Permission.MANAGE_DISCOUNTS,
        Permission.MANAGE_CREDIT_NOTES,
        Permission.MANAGE_TAX_RATES,
    ],
    PermissionCategory.TARIFF_MANAGEMENT: [
        Permission.VIEW_TARIFFS,
        Permission.CREATE_TARIFF,
        Permission.UPDATE_TARIFF,
        Permission.DELETE_TARIFF,
    ],
    PermissionCategory.RADIUS_AAA: [
        Permission.VIEW_RADIUS_PROFILES,
        Permission.CREATE_RADIUS_PROFILE,
        Permission.UPDATE_RADIUS_PROFILE,
        Permission.DELETE_RADIUS_PROFILE,
        Permission.VIEW_ACCOUNTING,
    ],
    PermissionCategory.MONITORING: [
        Permission.VIEW_SYSTEM_METRICS,
        Permission.VIEW_USER_METRICS,
        Permission.CONFIGURE_ALERTS,
    ],
    PermissionCategory.RESELLER_MANAGEMENT: [
        Permission.VIEW_RESELLERS,
        Permission.CREATE_RESELLER,
        Permission.UPDATE_RESELLER,
        Permission.DELETE_RESELLER,
        Permission.MANAGE_RESELLER_COMMISSIONS,
    ],
    PermissionCategory.SUPPORT: [
        Permission.VIEW_ALL_TICKETS,
        Permission.VIEW_OWN_TICKETS,
        Permission.CREATE_TICKET,
        Permission.UPDATE_TICKET,
        Permission.ASSIGN_TICKET,
        Permission.CLOSE_TICKET,
    ],
    PermissionCategory.SYSTEM: [
        Permission.VIEW_SYSTEM_CONFIG,
        Permission.UPDATE_SYSTEM_CONFIG,
    ],
    PermissionCategory.API: [
        Permission.API_ACCESS,
    ],
    PermissionCategory.LOGGING: [
        Permission.VIEW_LOGS,
        Permission.CONFIGURE_LOGGING,
    ],
}

# Default role definitions
DEFAULT_ROLES = {
    "admin": {
        "description": "Administrator with full system access",
        "permissions": [p.value for p in Permission],
    },
    "staff": {
        "description": "Staff member with access to customer management and support",
        "permissions": [
            Permission.VIEW_USERS.value,
            Permission.VIEW_CUSTOMERS.value,
            Permission.CREATE_CUSTOMER.value,
            Permission.UPDATE_CUSTOMER.value,
            Permission.VIEW_INVOICES.value,
            Permission.CREATE_INVOICE.value,
            Permission.PROCESS_PAYMENT.value,
            Permission.VIEW_TARIFFS.value,
            Permission.VIEW_RADIUS_PROFILES.value,
            Permission.CREATE_RADIUS_PROFILE.value,
            Permission.UPDATE_RADIUS_PROFILE.value,
            Permission.VIEW_ACCOUNTING.value,
            Permission.VIEW_USER_METRICS.value,
            Permission.VIEW_ALL_TICKETS.value,
            Permission.CREATE_TICKET.value,
            Permission.UPDATE_TICKET.value,
            Permission.ASSIGN_TICKET.value,
            Permission.CLOSE_TICKET.value,
            Permission.API_ACCESS.value,
            Permission.VIEW_LOGS.value,
        ],
    },
    "reseller": {
        "description": "Reseller with access to their customers",
        "permissions": [
            Permission.VIEW_CUSTOMERS.value,
            Permission.CREATE_CUSTOMER.value,
            Permission.UPDATE_CUSTOMER.value,
            Permission.VIEW_INVOICES.value,
            Permission.VIEW_TARIFFS.value,
            Permission.VIEW_USER_METRICS.value,
            Permission.VIEW_OWN_TICKETS.value,
            Permission.CREATE_TICKET.value,
            Permission.UPDATE_TICKET.value,
            Permission.API_ACCESS.value,
        ],
    },
    "technician": {
        "description": "Technical support with access to network and support functions",
        "permissions": [
            Permission.VIEW_CUSTOMERS.value,
            Permission.VIEW_RADIUS_PROFILES.value,
            Permission.UPDATE_RADIUS_PROFILE.value,
            Permission.VIEW_ACCOUNTING.value,
            Permission.VIEW_USER_METRICS.value,
            Permission.VIEW_ALL_TICKETS.value,
            Permission.CREATE_TICKET.value,
            Permission.UPDATE_TICKET.value,
            Permission.ASSIGN_TICKET.value,
            Permission.CLOSE_TICKET.value,
            Permission.API_ACCESS.value,
            Permission.VIEW_LOGS.value,
        ],
    },
    "customer": {
        "description": "Regular customer with self-service access",
        "permissions": [
            Permission.VIEW_OWN_TICKETS.value,
            Permission.CREATE_TICKET.value,
            Permission.UPDATE_TICKET.value,
            Permission.API_ACCESS.value,
        ],
    },
}

# Role hierarchy
DEFAULT_ROLE_HIERARCHY = {
    "admin": [],  # Admin inherits from no one
    "staff": [],  # Staff inherits from no one
    "reseller": [],  # Reseller inherits from no one
    "technician": [],  # Technician inherits from no one
    "customer": [],  # Customer inherits from no one
}

class RBACService:
    """Service for managing role-based access control."""
    
    @staticmethod
    def initialize_rbac(db: Session) -> None:
        """Initialize RBAC system with default roles and permissions."""
        # Check if RBAC is already initialized
        roles_config = db.query(SystemConfig).filter(SystemConfig.key == "rbac_roles").first()
        if not roles_config:
            # Create roles configuration
            roles_config = SystemConfig(
                key="rbac_roles",
                value=DEFAULT_ROLES,
                description="RBAC role definitions"
            )
            db.add(roles_config)
        
        # Check if role hierarchy is initialized
        hierarchy_config = db.query(SystemConfig).filter(SystemConfig.key == "rbac_role_hierarchy").first()
        if not hierarchy_config:
            # Create role hierarchy configuration
            hierarchy_config = SystemConfig(
                key="rbac_role_hierarchy",
                value=DEFAULT_ROLE_HIERARCHY,
                description="RBAC role hierarchy"
            )
            db.add(hierarchy_config)
        
        db.commit()
        
        # Cache roles and permissions
        RBACService.cache_roles_and_permissions(db)
    
    @staticmethod
    def cache_roles_and_permissions(db: Session) -> None:
        """Cache roles and permissions in Redis for faster access."""
        # Get roles and hierarchy from database
        roles_config = db.query(SystemConfig).filter(SystemConfig.key == "rbac_roles").first()
        hierarchy_config = db.query(SystemConfig).filter(SystemConfig.key == "rbac_role_hierarchy").first()
        
        if not roles_config or not hierarchy_config:
            return
        
        # Cache roles
        redis_client.set(ROLES_CACHE_KEY, json.dumps(roles_config.value))
        
        # Cache role hierarchy
        redis_client.set(ROLE_HIERARCHY_CACHE_KEY, json.dumps(hierarchy_config.value))
        
        # Cache all permissions
        all_permissions = [p.value for p in Permission]
        redis_client.set(PERMISSIONS_CACHE_KEY, json.dumps(all_permissions))
    
    @staticmethod
    def get_roles() -> Dict:
        """Get all roles and their permissions."""
        # Try to get from cache
        cached_roles = redis_client.get(ROLES_CACHE_KEY)
        if cached_roles:
            return json.loads(cached_roles)
        
        # If not in cache, return default roles
        return DEFAULT_ROLES
    
    @staticmethod
    def get_role_hierarchy() -> Dict:
        """Get role hierarchy."""
        # Try to get from cache
        cached_hierarchy = redis_client.get(ROLE_HIERARCHY_CACHE_KEY)
        if cached_hierarchy:
            return json.loads(cached_hierarchy)
        
        # If not in cache, return default hierarchy
        return DEFAULT_ROLE_HIERARCHY
    
    @staticmethod
    def get_role_permissions(role: str) -> Set[str]:
        """Get permissions for a specific role, including inherited permissions."""
        roles = RBACService.get_roles()
        hierarchy = RBACService.get_role_hierarchy()
        
        if role not in roles:
            return set()
        
        # Get direct permissions
        permissions = set(roles[role]["permissions"])
        
        # Get inherited permissions
        for parent_role in hierarchy.get(role, []):
            parent_permissions = RBACService.get_role_permissions(parent_role)
            permissions.update(parent_permissions)
        
        return permissions
    
    @staticmethod
    def get_user_permissions(user: User) -> Set[str]:
        """Get all permissions for a user based on their role."""
        # Try to get from cache
        cache_key = f"{USER_PERMISSIONS_CACHE_PREFIX}{user.id}"
        cached_permissions = redis_client.get(cache_key)
        if cached_permissions:
            return set(json.loads(cached_permissions))
        
        # Get permissions for user's role
        permissions = RBACService.get_role_permissions(user.role)
        
        # Cache user permissions
        redis_client.setex(cache_key, 3600, json.dumps(list(permissions)))  # Cache for 1 hour
        
        return permissions
    
    @staticmethod
    def has_permission(user: User, permission: str) -> bool:
        """Check if a user has a specific permission."""
        user_permissions = RBACService.get_user_permissions(user)
        return permission in user_permissions
    
    @staticmethod
    def invalidate_user_permissions_cache(user_id: int) -> None:
        """Invalidate cached permissions for a user."""
        cache_key = f"{USER_PERMISSIONS_CACHE_PREFIX}{user_id}"
        redis_client.delete(cache_key)
    
    @staticmethod
    def update_role(db: Session, role_name: str, description: str, permissions: List[str]) -> bool:
        """Update or create a role with specified permissions."""
        # Get current roles
        roles_config = db.query(SystemConfig).filter(SystemConfig.key == "rbac_roles").first()
        if not roles_config:
            return False
        
        roles = roles_config.value
        
        # Update or create role
        roles[role_name] = {
            "description": description,
            "permissions": permissions
        }
        
        # Save to database
        roles_config.value = roles
        db.commit()
        
        # Update cache
        redis_client.set(ROLES_CACHE_KEY, json.dumps(roles))
        
        # Invalidate all user permissions caches
        users = db.query(User).filter(User.role == role_name).all()
        for user in users:
            RBACService.invalidate_user_permissions_cache(user.id)
        
        return True
    
    @staticmethod
    def delete_role(db: Session, role_name: str) -> bool:
        """Delete a role."""
        # Check if role is in use
        users_with_role = db.query(User).filter(User.role == role_name).count()
        if users_with_role > 0:
            return False
        
        # Get current roles
        roles_config = db.query(SystemConfig).filter(SystemConfig.key == "rbac_roles").first()
        if not roles_config or role_name not in roles_config.value:
            return False
        
        roles = roles_config.value
        
        # Delete role
        del roles[role_name]
        
        # Save to database
        roles_config.value = roles
        db.commit()
        
        # Update cache
        redis_client.set(ROLES_CACHE_KEY, json.dumps(roles))
        
        # Update role hierarchy
        hierarchy_config = db.query(SystemConfig).filter(SystemConfig.key == "rbac_role_hierarchy").first()
        if hierarchy_config and role_name in hierarchy_config.value:
            hierarchy = hierarchy_config.value
            del hierarchy[role_name]
            
            # Remove role from parent roles
            for parent_roles in hierarchy.values():
                if role_name in parent_roles:
                    parent_roles.remove(role_name)
            
            # Save to database
            hierarchy_config.value = hierarchy
            db.commit()
            
            # Update cache
            redis_client.set(ROLE_HIERARCHY_CACHE_KEY, json.dumps(hierarchy))
        
        return True
    
    @staticmethod
    def update_role_hierarchy(db: Session, role_name: str, parent_roles: List[str]) -> bool:
        """Update the hierarchy for a role."""
        # Get current hierarchy
        hierarchy_config = db.query(SystemConfig).filter(SystemConfig.key == "rbac_role_hierarchy").first()
        if not hierarchy_config:
            return False
        
        hierarchy = hierarchy_config.value
        
        # Update hierarchy
        hierarchy[role_name] = parent_roles
        
        # Save to database
        hierarchy_config.value = hierarchy
        db.commit()
        
        # Update cache
        redis_client.set(ROLE_HIERARCHY_CACHE_KEY, json.dumps(hierarchy))
        
        # Invalidate all user permissions caches for users with this role
        users = db.query(User).filter(User.role == role_name).all()
        for user in users:
            RBACService.invalidate_user_permissions_cache(user.id)
        
        return True
    
    @staticmethod
    def get_all_permissions() -> List[Dict]:
        """Get all available permissions with their categories."""
        result = []
        
        for category, permissions in PERMISSION_CATEGORIES.items():
            for permission in permissions:
                result.append({
                    "name": permission.value,
                    "category": category.value,
                    "description": permission.value.replace("_", " ").title()
                })
        
        return result
