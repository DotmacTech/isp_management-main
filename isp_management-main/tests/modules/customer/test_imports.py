"""
Simple test to verify that imports are working correctly.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest

def test_customer_imports():
    """Test that customer module imports are working correctly."""
    # Import the models
    from modules.customer.models import (
        Customer,
        CustomerType,
        CustomerStatus,
        SubscriptionState,
        CustomerAddress,
        AddressType,
        CustomerContact,
        ContactType,
        CommunicationPreference,
        CommunicationType,
        CustomerDocument,
        DocumentType,
        VerificationStatus,
        CustomerNote,
        EmailVerification,
        CustomerTagDefinition
    )
    
    # Import the services
    from modules.customer.services import CustomerService
    from modules.customer.communication_service import CommunicationService
    from modules.customer.verification_service import VerificationService
    from modules.customer.document_service import CustomerDocumentService
    
    # Import the endpoints
    from modules.customer.endpoints import router
    
    # Simple assertions to verify the imports
    assert Customer.__name__ == "Customer"
    assert CustomerType.__name__ == "CustomerType"
    assert CustomerService.__name__ == "CustomerService"
    assert router.prefix == "/customers"
    
    # Test passed if we got here without import errors
    assert True
