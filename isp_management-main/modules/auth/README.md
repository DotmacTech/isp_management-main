# Authentication Module for ISP Management Platform

This module provides comprehensive authentication and authorization services for the ISP Management Platform, including user registration, login, token management, password reset, and two-factor authentication.

## Authentication Workflow

The authentication system follows a well-defined workflow as documented in [authentication_workflow.md](/docs/auth/authentication_workflow.md). The workflow includes:

1. **User Registration and Account Creation** - New user signup with email verification
2. **Email Verification** - Confirmation of user email addresses
3. **User Login (Standard Flow)** - Basic username/password authentication
4. **User Login (With MFA)** - Enhanced security with multi-factor authentication
5. **Token-based Authentication** - JWT token validation for API access
6. **Token Refresh** - Mechanism for maintaining valid sessions
7. **Session Management** - Tracking and control of user sessions
8. **Password Management** - Secure password changing and reset workflows
9. **Multi-Factor Authentication (MFA)** - Implementation of TOTP-based second factor
10. **Logout** - Secure session termination and token invalidation

All authentication code in the module adheres to this workflow to ensure consistent, secure authentication processes.

## Features

- **User Management**
  - User registration with email validation
  - User profile management
  - Role-based access control (customer, staff, admin)
  - User activation/deactivation (admin only)

- **Authentication**
  - Secure login with rate limiting
  - JWT-based token authentication
  - Access and refresh tokens
  - Token blacklisting for logout
  - Remember me functionality

- **Security Features**
  - Password hashing with bcrypt
  - Two-factor authentication (TOTP)
  - Password reset with secure tokens
  - Account lockout after multiple failed attempts
  - Rate limiting for sensitive endpoints

- **Email Notifications**
  - Welcome emails for new users
  - Password reset emails
  - Two-factor authentication setup emails
  - Account lockout notifications

## Setup

### Environment Variables

Add the following environment variables to your `.env` file:

```
# JWT Configuration
JWT_SECRET_KEY=your_jwt_secret_key
JWT_REFRESH_SECRET_KEY=your_jwt_refresh_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis Configuration (for rate limiting and token blacklisting)
REDIS_URL=redis://localhost:6379/0

# Email Configuration
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=your_smtp_password
FROM_EMAIL=noreply@example.com

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:3000
```

### Dependencies

This module requires the following dependencies:

```
fastapi>=0.68.0
pydantic>=1.8.2
sqlalchemy>=1.4.23
passlib>=1.7.4
python-jose>=3.3.0
python-multipart>=0.0.5
redis>=4.0.2
pyotp>=2.6.0
qrcode>=7.3.1
pillow>=8.3.2
jinja2>=3.0.1
```

## API Endpoints

### User Registration and Authentication

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Authenticate a user and get tokens
- `POST /auth/refresh` - Refresh an access token
- `POST /auth/logout` - Logout and blacklist the current token

### Password Management

- `POST /auth/password-reset` - Request a password reset
- `POST /auth/password-reset/confirm` - Confirm a password reset
- `POST /auth/password-change` - Change a user's password

### Two-Factor Authentication

- `POST /auth/2fa/setup` - Set up two-factor authentication
- `POST /auth/2fa/verify` - Verify a two-factor authentication code

### User Management

- `GET /auth/users/me` - Get the current authenticated user
- `GET /auth/users` - Get a list of users (admin only)
- `GET /auth/users/{user_id}` - Get a user by ID (staff/admin only)
- `PUT /auth/users/{user_id}` - Update a user (staff/admin only)
- `POST /auth/users/{user_id}/deactivate` - Deactivate a user (admin only)
- `POST /auth/users/{user_id}/activate` - Activate a user (admin only)

## Usage Examples

### User Registration

```python
import requests

response = requests.post(
    "http://localhost:8000/auth/register",
    json={
        "username": "newuser",
        "email": "user@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "role": "customer"
    }
)
print(response.json())
```

### User Login

```python
import requests

response = requests.post(
    "http://localhost:8000/auth/login",
    json={
        "username": "newuser",
        "password": "SecurePassword123!",
        "remember_me": True
    }
)
tokens = response.json()
access_token = tokens["access_token"]
refresh_token = tokens["refresh_token"]
```

### Accessing Protected Endpoints

```python
import requests

headers = {
    "Authorization": f"Bearer {access_token}"
}

response = requests.get(
    "http://localhost:8000/auth/users/me",
    headers=headers
)
print(response.json())
```

### Setting Up Two-Factor Authentication

```python
import requests

headers = {
    "Authorization": f"Bearer {access_token}"
}

response = requests.post(
    "http://localhost:8000/auth/2fa/setup",
    headers=headers
)
setup_data = response.json()
qr_code = setup_data["qr_code"]
secret_key = setup_data["secret_key"]
recovery_codes = setup_data["recovery_codes"]
```

## Testing

Run the tests for the authentication module:

```bash
pytest tests/modules/auth/ -v
```

## Security Considerations

- Always use HTTPS in production
- Configure CORS appropriately for your frontend domains
- Rotate JWT secrets periodically
- Monitor for suspicious login attempts
- Implement proper error logging and monitoring
- Consider adding additional security measures like IP-based rate limiting

## License

This module is part of the ISP Management Platform and is subject to the same license terms as the main project.
