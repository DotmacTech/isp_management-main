# Customer Management Module

## Overview

The Customer Management Module provides comprehensive functionality for managing customer data within the ISP Management Platform. This module handles various aspects of customer information, including personal details, addresses, contacts, communication preferences, documents, notes, and tags.

## Features

- **Customer Profile Management**: Create, update, retrieve, and delete customer profiles
- **Address Management**: Manage multiple addresses for customers (billing, service, etc.)
- **Contact Management**: Manage multiple contacts for a customer
- **Communication Preferences**: Set and manage customer communication preferences
- **Document Management**: Upload, verify, and manage customer documents
- **Notes**: Add and manage notes related to customers
- **Tags**: Create and assign tags to customers for easy categorization
- **Email Verification**: Verify customer email addresses

## API Endpoints

### Customer Endpoints

- `POST /customers/`: Create a new customer
- `GET /customers/{customer_id}`: Get customer details
- `PUT /customers/{customer_id}`: Update customer details
- `DELETE /customers/{customer_id}`: Delete a customer
- `PUT /customers/{customer_id}/subscription-state`: Update customer subscription state

### Address Endpoints

- `POST /customers/{customer_id}/addresses/`: Add a new address for a customer
- `GET /customers/{customer_id}/addresses/`: Get all addresses for a customer
- `GET /customers/{customer_id}/addresses/{address_id}`: Get a specific address
- `PUT /customers/{customer_id}/addresses/{address_id}`: Update an address
- `DELETE /customers/{customer_id}/addresses/{address_id}`: Delete an address
- `PUT /customers/{customer_id}/addresses/{address_id}/verify`: Verify an address

### Contact Endpoints

- `POST /customers/{customer_id}/contacts/`: Add a new contact for a customer
- `GET /customers/{customer_id}/contacts/`: Get all contacts for a customer
- `GET /customers/{customer_id}/contacts/{contact_id}`: Get a specific contact
- `PUT /customers/{customer_id}/contacts/{contact_id}`: Update a contact
- `DELETE /customers/{customer_id}/contacts/{contact_id}`: Delete a contact

### Communication Preference Endpoints

- `POST /customers/{customer_id}/communication-preferences/`: Set communication preferences
- `GET /customers/{customer_id}/communication-preferences/`: Get all communication preferences
- `GET /customers/{customer_id}/communication-preferences/{preference_id}`: Get a specific preference
- `PUT /customers/{customer_id}/communication-preferences/{preference_id}`: Update a preference
- `DELETE /customers/{customer_id}/communication-preferences/{preference_id}`: Delete a preference

### Document Endpoints

- `POST /customers/{customer_id}/documents/`: Upload a document for a customer
- `GET /customers/{customer_id}/documents/`: Get all documents for a customer
- `GET /customers/{customer_id}/documents/{document_id}`: Get a specific document
- `GET /customers/{customer_id}/documents/{document_id}/download`: Download a document
- `PUT /customers/{customer_id}/documents/{document_id}/verify`: Update document verification status
- `DELETE /customers/{customer_id}/documents/{document_id}`: Delete a document

### Note Endpoints

- `POST /customers/{customer_id}/notes/`: Add a note for a customer
- `GET /customers/{customer_id}/notes/`: Get all notes for a customer
- `GET /customers/{customer_id}/notes/{note_id}`: Get a specific note
- `PUT /customers/{customer_id}/notes/{note_id}`: Update a note
- `DELETE /customers/{customer_id}/notes/{note_id}`: Delete a note

### Tag Endpoints

- `POST /tags/`: Create a new tag
- `GET /tags/`: Get all tags
- `GET /tags/{tag_id}`: Get a specific tag
- `PUT /tags/{tag_id}`: Update a tag
- `DELETE /tags/{tag_id}`: Delete a tag
- `POST /customers/{customer_id}/tags/{tag_id}`: Assign a tag to a customer
- `DELETE /customers/{customer_id}/tags/{tag_id}`: Remove a tag from a customer
- `GET /customers/{customer_id}/tags/`: Get all tags for a customer

### Email Verification Endpoints

- `POST /customers/{customer_id}/verify-email`: Send email verification
- `GET /customers/verify-email`: Verify email with token

## Configuration

The Customer Management Module requires the following environment variables:

- `CUSTOMER_DOCUMENT_PATH`: Path to store customer documents

## Integration with Other Modules

The Customer Management Module integrates with the following modules:

- **Billing Module**: For managing customer billing information
- **Tariff Module**: For managing customer tariff plans
- **Monitoring Module**: For monitoring customer service usage
- **RADIUS Module**: For managing customer authentication and authorization

## Testing

The module includes comprehensive tests for all services and endpoints. Run the tests using:

```bash
pytest tests/modules/customer/ -v
```

## Security Considerations

- All sensitive customer data is properly validated and secured
- Role-based access control is implemented for all endpoints
- Document uploads are validated for size and file type
- Email verification ensures valid customer email addresses

## Future Enhancements

- Customer segmentation based on behavior and preferences
- Enhanced reporting capabilities
- Integration with external CRM systems
- Advanced search functionality
