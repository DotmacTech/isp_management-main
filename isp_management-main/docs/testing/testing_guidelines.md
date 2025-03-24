# Testing Guidelines

This document outlines the testing standards and best practices for the ISP Management Platform.

## Testing Strategy

The ISP Management Platform follows a comprehensive testing strategy that includes:

1. **Unit Testing**: Testing individual components in isolation
2. **Integration Testing**: Testing interactions between components
3. **API Testing**: Testing API endpoints and responses
4. **Performance Testing**: Testing system performance under load
5. **Security Testing**: Testing for security vulnerabilities
6. **End-to-End Testing**: Testing complete user workflows

## Test Directory Structure

Tests should be organized following this structure:

```
tests/
├── conftest.py                # Shared fixtures and configuration
├── unit/                      # Unit tests
│   ├── modules/               # Module-specific unit tests
│   │   ├── module_name/       # Tests for a specific module
│   │   │   ├── test_api.py    # Tests for API layer
│   │   │   ├── test_models.py # Tests for models
│   │   │   └── test_services.py # Tests for services
│   └── core/                  # Core functionality tests
├── integration/               # Integration tests
│   ├── test_module_interactions.py
│   └── test_database.py
├── api/                       # API tests
│   ├── test_auth.py
│   └── test_endpoints.py
└── e2e/                       # End-to-end tests
    └── test_workflows.py
```

## Unit Testing

### Test Framework

- Use **pytest** as the primary test framework
- Organize tests in classes for related functionality
- Use descriptive test names that explain the test purpose

### Test Coverage

- Aim for at least 80% code coverage for all modules
- Focus on testing business logic and edge cases
- Ensure all error handling paths are tested

### Mocking

- Use `unittest.mock` or `pytest-mock` for mocking dependencies
- Create reusable mock fixtures in `conftest.py`
- Avoid excessive mocking that could hide integration issues

### Example Unit Test

```python
import pytest
from unittest.mock import MagicMock, patch
from modules.ai_chatbot.services.chatbot_service import ChatbotService
from modules.ai_chatbot.schemas.chatbot import ChatbotQueryCreate, ChatbotResponse

class TestChatbotService:
    @pytest.fixture
    def ai_service_client_mock(self):
        return MagicMock()
    
    @pytest.fixture
    def business_logic_processor_mock(self):
        return MagicMock()
    
    @pytest.fixture
    def chatbot_service(self, ai_service_client_mock, business_logic_processor_mock):
        return ChatbotService(
            ai_service_client=ai_service_client_mock,
            business_logic_processor=business_logic_processor_mock
        )
    
    async def test_process_query_success(self, chatbot_service, ai_service_client_mock, business_logic_processor_mock):
        # Arrange
        query = ChatbotQueryCreate(text="Show me billing information", user_id=1, tenant_id=1)
        ai_response = MagicMock()
        ai_service_client_mock.process_query.return_value = (ai_response, 0.5)
        expected_response = ChatbotResponse(
            query_id=1,
            response_text="Here is your billing information",
            confidence=0.9,
            processing_time=0.5
        )
        business_logic_processor_mock.process_intent.return_value = expected_response
        
        # Act
        result = await chatbot_service.process_query(query)
        
        # Assert
        assert result == expected_response
        ai_service_client_mock.process_query.assert_called_once()
        business_logic_processor_mock.process_intent.assert_called_once_with(
            ai_response, query, query.user_id, query.tenant_id
        )
```

## Integration Testing

### Database Integration

- Use test databases (preferably in-memory or containerized)
- Reset database state between tests
- Test database migrations and schema changes

### Service Integration

- Test interactions between services
- Verify correct data flow between components
- Test error propagation between services

### Example Integration Test

```python
import pytest
from sqlalchemy.orm import Session
from modules.ai_chatbot.services.chatbot_service import ChatbotService
from modules.ai_chatbot.models.chatbot import ChatbotQuery
from modules.ai_chatbot.schemas.chatbot import ChatbotQueryCreate

class TestChatbotIntegration:
    @pytest.mark.asyncio
    async def test_query_stored_in_database(self, db_session: Session, chatbot_service: ChatbotService):
        # Arrange
        query_text = "Show me billing information"
        query = ChatbotQueryCreate(text=query_text, user_id=1, tenant_id=1)
        
        # Act
        response = await chatbot_service.process_query(query)
        
        # Assert
        db_query = db_session.query(ChatbotQuery).filter(ChatbotQuery.id == response.query_id).first()
        assert db_query is not None
        assert db_query.text == query_text
        assert db_query.user_id == 1
        assert db_query.tenant_id == 1
```

## API Testing

### Endpoint Testing

- Test all API endpoints with various inputs
- Verify correct status codes and response formats
- Test authentication and authorization

### FastAPI TestClient

- Use FastAPI's TestClient for API testing
- Create test fixtures for authenticated clients
- Test different user roles and permissions

### Example API Test

```python
from fastapi.testclient import TestClient
import pytest
from main import app

client = TestClient(app)

class TestChatbotAPI:
    def test_process_query_endpoint(self, auth_headers):
        # Arrange
        query_data = {
            "text": "Show me billing information",
            "user_id": 1,
            "tenant_id": 1
        }
        
        # Act
        response = client.post("/api/v1/chatbot/query", json=query_data, headers=auth_headers)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "query_id" in data
        assert "response_text" in data
        assert "confidence" in data
        assert data["response_text"] != ""
```

## Performance Testing

### Load Testing

- Use tools like Locust or k6 for load testing
- Test system performance under expected and peak loads
- Identify bottlenecks and optimization opportunities

### Benchmarking

- Establish performance baselines for critical operations
- Compare performance metrics across releases
- Set performance budgets for API response times

### Example Load Test

```python
from locust import HttpUser, task, between

class ChatbotUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        self.token = response.json()["access_token"]
    
    @task
    def query_chatbot(self):
        self.client.post(
            "/api/v1/chatbot/query",
            json={"text": "Show me billing information", "user_id": 1, "tenant_id": 1},
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

## Security Testing

### Vulnerability Scanning

- Use automated tools to scan for common vulnerabilities
- Test for OWASP Top 10 vulnerabilities
- Conduct regular penetration testing

### Authentication Testing

- Test token validation and expiration
- Verify role-based access controls
- Test against common authentication attacks

### Example Security Test

```python
def test_unauthorized_access(client):
    # Test without authentication
    response = client.post("/api/v1/chatbot/query", json={"text": "Test"})
    assert response.status_code == 401
    
    # Test with invalid token
    response = client.post(
        "/api/v1/chatbot/query",
        json={"text": "Test"},
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    
    # Test with insufficient permissions
    response = client.post(
        "/api/v1/chatbot/query",
        json={"text": "Test"},
        headers={"Authorization": f"Bearer {regular_user_token}"}
    )
    assert response.status_code == 403
```

## End-to-End Testing

### User Workflows

- Test complete user workflows from start to finish
- Verify system behavior across multiple components
- Test critical business processes

### UI Testing

- Use Selenium or Playwright for UI testing
- Test responsive design and browser compatibility
- Verify accessibility compliance

## Test Automation

### CI/CD Integration

- Run tests automatically on pull requests
- Block merges if tests fail
- Generate test coverage reports

### Test Environment Management

- Use Docker containers for consistent test environments
- Implement database seeding for test data
- Reset environment state between test runs

## Test Documentation

### Test Plans

- Document test objectives and scope
- Define test scenarios and expected results
- Identify test data requirements

### Test Reports

- Generate automated test reports
- Track test coverage over time
- Document known issues and limitations

## Module-Specific Testing

### AI Chatbot Module

1. **Unit Tests**:
   - Test `ChatbotService` for proper coordination
   - Test `AIServiceClient` for API communication
   - Test `BusinessLogicProcessor` for intent handling

2. **Integration Tests**:
   - Test end-to-end query processing
   - Test database storage of queries and feedback
   - Test context management across queries

3. **Performance Tests**:
   - Test response time under load
   - Test concurrent query handling
   - Test caching effectiveness

## Testing Tools

- **pytest**: Primary test framework
- **pytest-asyncio**: For testing async code
- **pytest-cov**: For test coverage reporting
- **pytest-mock**: For mocking dependencies
- **pytest-xdist**: For parallel test execution
- **Locust**: For load testing
- **Selenium/Playwright**: For UI testing

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Fast Execution**: Tests should run quickly to enable frequent execution
3. **Deterministic Results**: Tests should produce the same results each time
4. **Clear Failures**: Test failures should clearly indicate what went wrong
5. **Maintainable Tests**: Tests should be easy to understand and maintain
