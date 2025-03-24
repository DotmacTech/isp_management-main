"""
Direct test script to validate the ExternalServiceCreate schema.

This script directly imports the schema module to test if our fix is working.
"""

from importlib import reload
import sys

# Remove any existing imports to force reload
for mod in list(sys.modules.keys()):
    if mod.startswith('modules.communications'):
        del sys.modules[mod]

# Now import directly from file
from modules.communications.schemas import ExternalServiceCreate

# Test that the schema class works
service = ExternalServiceCreate(
    name="Test Service",
    service_type="sms",
    config={"api_key": "test"}
)

print(f"Successfully imported ExternalServiceCreate")
print(f"service.name = {service.name}")
print(f"service.service_type = {service.service_type}")
print(f"service.config = {service.config}")
print(f"service.is_active = {service.is_active}")
