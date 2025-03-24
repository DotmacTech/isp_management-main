# AI Chatbot Integration Module

This module provides natural language processing capabilities to the ISP Management Platform, allowing support agents to interact with the platform using conversational queries.

## Overview

The AI Chatbot Integration Module enables:

- Processing natural language queries about platform data
- Maintaining conversation context for follow-up questions
- Translating user intent into platform actions
- Collecting feedback for continuous improvement
- Tracking query history and performance metrics

## Architecture

The module follows a layered architecture:

```
ai_chatbot/
├── api/                       # API layer
│   ├── __init__.py            # API router initialization
│   └── endpoints.py           # API endpoints
├── config/                    # Configuration
│   ├── __init__.py
│   └── settings.py            # Module settings
├── models/                    # Database models
│   ├── __init__.py
│   └── chatbot.py             # Chatbot-related models
├── schemas/                   # Pydantic schemas
│   ├── __init__.py
│   └── chatbot.py             # Chatbot-related schemas
├── services/                  # Business logic
│   ├── __init__.py
│   ├── ai_service_client.py   # AI service communication
│   ├── business_logic_processor.py # Business logic processing
│   └── chatbot_service.py     # Main chatbot service
└── utils/                     # Utilities
    ├── __init__.py
    ├── context.py             # Conversation context management
    └── security.py            # Security utilities
```

## Core Components

### ChatbotService

The `ChatbotService` coordinates between the AI service client and business logic processor:

```python
class ChatbotService:
    """
    Service for processing chatbot queries and managing responses.
    
    This service coordinates between the AI service client and business logic processor
    to handle natural language queries, process intents, and generate structured responses.
    """
    
    def __init__(
        self,
        ai_service_client: AIServiceClient,
        business_logic_processor: BusinessLogicProcessor
    ):
        self.ai_service_client = ai_service_client
        self.business_logic_processor = business_logic_processor
        
    async def process_query(self, query: ChatbotQueryCreate) -> ChatbotResponse:
        """
        Process a natural language query.
        
        Args:
            query: The query to process
            
        Returns:
            A structured response to the query
        """
        # Process the query with the AI service
        ai_response, processing_time = await self.ai_service_client.process_query(
            AIModelRequest(
                query=query.text,
                context=query.context,
                user_id=query.user_id,
                tenant_id=query.tenant_id
            )
        )
        
        # Process the intent with the business logic processor
        response = await self.business_logic_processor.process_intent(
            ai_response, query, query.user_id, query.tenant_id
        )
        
        return response
```

### AIServiceClient

The `AIServiceClient` handles communication with external AI services:

```python
class AIServiceClient:
    """
    Client for communicating with external AI services.
    
    This client handles sending requests to AI services, processing responses,
    and managing errors and metrics.
    """
    
    def __init__(
        self,
        http_client: Optional[httpx.AsyncClient] = None,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        self.http_client = http_client or httpx.AsyncClient()
        self.metrics_collector = metrics_collector or MetricsCollector("ai_service")
        
    async def process_query(
        self, 
        request: AIModelRequest, 
        service_name: Optional[str] = None
    ) -> Tuple[AIModelResponse, float]:
        """
        Process a natural language query using an AI service.
        
        Args:
            request: The request to process
            service_name: Optional name of the AI service to use
            
        Returns:
            A tuple containing the AI model response and processing time
            
        Raises:
            AIServiceError: If there is an error communicating with the AI service
        """
        # Implementation details...
```

### BusinessLogicProcessor

The `BusinessLogicProcessor` translates AI interpretations into platform actions:

```python
class BusinessLogicProcessor:
    """
    Processor for translating AI interpretations into platform actions.
    
    This processor handles the business logic of interpreting AI responses,
    executing actions, and generating structured responses.
    """
    
    def __init__(
        self,
        db: Session,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        self.db = db
        self.metrics_collector = metrics_collector or MetricsCollector("business_logic")
        
    async def process_intent(
        self, 
        ai_response: AIModelResponse, 
        query: ChatbotQueryCreate,
        user_id: int,
        tenant_id: int
    ) -> ChatbotResponse:
        """
        Process the intent from an AI response and generate a structured response.
        
        Args:
            ai_response: The AI model response
            query: The original query
            user_id: The ID of the user making the query
            tenant_id: The ID of the tenant
            
        Returns:
            A structured response to the query
        """
        # Implementation details...
```

## API Endpoints

The module exposes the following API endpoints:

### Process Query

```
POST /api/v1/chatbot/query
```

Process a natural language query and return a structured response.

**Request:**
```json
{
  "text": "Show me billing information for customer ABC123",
  "context": {
    "previous_queries": [
      {
        "query_id": 123,
        "text": "Who are our top customers?",
        "timestamp": "2025-03-15T07:30:45.123Z"
      }
    ],
    "user_context": {
      "role": "support_agent",
      "permissions": ["billing_read", "customer_read"]
    }
  },
  "user_id": 42,
  "tenant_id": 1
}
```

**Response:**
```json
{
  "query_id": 456,
  "response_text": "Here is the billing information for customer ABC123...",
  "structured_data": {
    "customer_id": "ABC123",
    "invoices": [
      {
        "invoice_id": "INV-2025-001",
        "amount": 99.99,
        "status": "paid",
        "date": "2025-02-01"
      }
    ]
  },
  "confidence": 0.95,
  "processing_time": 0.35,
  "suggested_actions": [
    {
      "action": "view_invoice",
      "parameters": {
        "invoice_id": "INV-2025-001"
      },
      "description": "View invoice details"
    }
  ]
}
```

### Submit Feedback

```
POST /api/v1/chatbot/feedback
```

Submit feedback on a chatbot response.

**Request:**
```json
{
  "query_id": 456,
  "rating": 5,
  "comments": "Very helpful response!",
  "user_id": 42
}
```

**Response:**
```json
{
  "feedback_id": 789,
  "status": "received",
  "timestamp": "2025-03-15T07:35:12.456Z"
}
```

### Get Query History

```
GET /api/v1/chatbot/history
```

Get the query history for the current user.

**Response:**
```json
{
  "queries": [
    {
      "query_id": 456,
      "text": "Show me billing information for customer ABC123",
      "response_text": "Here is the billing information for customer ABC123...",
      "timestamp": "2025-03-15T07:30:45.123Z",
      "rating": 5
    },
    {
      "query_id": 123,
      "text": "Who are our top customers?",
      "response_text": "Your top customers by revenue are...",
      "timestamp": "2025-03-15T07:25:30.789Z",
      "rating": null
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 10
}
```

### Manage AI Service Configuration

```
GET /api/v1/chatbot/config
POST /api/v1/chatbot/config
PUT /api/v1/chatbot/config/{config_id}
DELETE /api/v1/chatbot/config/{config_id}
```

Manage AI service configurations.

## Database Models

### ChatbotQuery

Stores user queries and responses:

```python
class ChatbotQuery(Base):
    """
    Model for storing chatbot queries and responses.
    """
    __tablename__ = "chatbot_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    response_text = Column(String, nullable=False)
    structured_data = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=False)
    processing_time = Column(Float, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="chatbot_queries")
    tenant = relationship("Tenant", back_populates="chatbot_queries")
    feedback = relationship("ChatbotFeedback", back_populates="query", uselist=False)
    actions = relationship("ChatbotAction", back_populates="query")
```

### ChatbotFeedback

Stores user feedback on responses:

```python
class ChatbotFeedback(Base):
    """
    Model for storing user feedback on chatbot responses.
    """
    __tablename__ = "chatbot_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("chatbot_queries.id"), nullable=False, unique=True)
    rating = Column(Integer, nullable=False)
    comments = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    query = relationship("ChatbotQuery", back_populates="feedback")
    user = relationship("User", back_populates="chatbot_feedback")
```

### ChatbotAction

Records actions taken based on queries:

```python
class ChatbotAction(Base):
    """
    Model for recording actions taken based on chatbot queries.
    """
    __tablename__ = "chatbot_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("chatbot_queries.id"), nullable=False)
    action_type = Column(String, nullable=False)
    parameters = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    query = relationship("ChatbotQuery", back_populates="actions")
```

### AIServiceConfig

Manages AI service configurations:

```python
class AIServiceConfig(Base):
    """
    Model for managing AI service configurations.
    """
    __tablename__ = "ai_service_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    service_url = Column(String, nullable=False)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    parameters = Column(JSON, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    api_key = relationship("APIKey", back_populates="ai_service_configs")
```

## Configuration

The module uses the following configuration settings:

```python
class AIChatbotSettings(BaseSettings):
    """
    Settings for the AI Chatbot Integration Module.
    """
    # AI Service settings
    AI_SERVICE_URL: str = "https://api.example.com/v1/ai"
    AI_SERVICE_API_KEY: str = Field(..., env="AI_SERVICE_API_KEY")
    AI_SERVICE_TIMEOUT: int = 10  # seconds
    AI_SERVICE_MAX_RETRIES: int = 3
    
    # Request handling
    MAX_QUERY_LENGTH: int = 500
    MAX_CONTEXT_SIZE: int = 10  # number of previous queries to include
    
    # Caching
    CACHE_TTL: int = 3600  # seconds
    ENABLE_RESPONSE_CACHE: bool = True
    
    # Security
    MASK_PII_IN_LOGS: bool = True
    SIGN_REQUESTS: bool = True
    
    class Config:
        env_prefix = "CHATBOT_"
        case_sensitive = True
```

## Security Considerations

The module implements several security measures:

1. **API Key Management**:
   - Secure storage of API keys
   - Rotation of keys on a regular schedule
   - Access control for key management

2. **Data Masking**:
   - PII detection and masking before sending to AI services
   - Sensitive data filtering in logs and error messages
   - Configurable masking rules

3. **Request Signing**:
   - HMAC-based request signing for AI service communication
   - Timestamp validation to prevent replay attacks
   - Nonce generation for request uniqueness

## Integration Points

The AI Chatbot module integrates with other modules:

1. **Authentication & Authorization**:
   - Uses the platform's JWT authentication
   - Respects role-based access control
   - Validates permissions for each action

2. **Billing Module**:
   - Retrieves billing information for customers
   - Processes billing-related queries
   - Executes billing actions (e.g., generating invoices)

3. **CRM Module**:
   - Accesses customer information
   - Handles customer-related queries
   - Updates customer records when needed

4. **Monitoring Module**:
   - Sends metrics for performance monitoring
   - Logs query processing for troubleshooting
   - Tracks error rates and response times

## Metrics and Monitoring

The module collects the following metrics:

1. **Performance Metrics**:
   - Query processing time
   - AI service response time
   - Database operation latency

2. **Usage Metrics**:
   - Queries per minute
   - Queries by user/tenant
   - Query complexity distribution

3. **Quality Metrics**:
   - Response confidence scores
   - User feedback ratings
   - Error rates by query type

## Testing

The module includes comprehensive tests:

1. **Unit Tests**:
   - Test individual components in isolation
   - Mock external dependencies
   - Test error handling and edge cases

2. **Integration Tests**:
   - Test interaction between components
   - Test database operations
   - Test API endpoints

3. **Performance Tests**:
   - Test response time under load
   - Test concurrent query handling
   - Test caching effectiveness

## Deployment

The module is deployed as part of the ISP Management Platform:

1. **Dependencies**:
   - FastAPI
   - SQLAlchemy
   - httpx
   - Pydantic

2. **Environment Variables**:
   - `CHATBOT_AI_SERVICE_URL`
   - `CHATBOT_AI_SERVICE_API_KEY`
   - `CHATBOT_CACHE_TTL`
   - `CHATBOT_MASK_PII_IN_LOGS`

3. **Database Migration**:
   - Run Alembic migration to create required tables

## Future Enhancements

Planned enhancements for the module:

1. **Multi-Language Support**:
   - Support for multiple languages in queries and responses
   - Language detection and translation

2. **Enhanced Context Management**:
   - Long-term conversation memory
   - User preference tracking
   - Adaptive response generation

3. **Advanced Analytics**:
   - Query pattern analysis
   - User satisfaction prediction
   - Automated response improvement

4. **Voice Integration**:
   - Speech-to-text for voice queries
   - Text-to-speech for voice responses
   - Voice biometrics for authentication

## Troubleshooting

Common issues and solutions:

1. **Slow Response Times**:
   - Check AI service latency
   - Verify database query performance
   - Ensure caching is properly configured

2. **Low Confidence Scores**:
   - Review query patterns
   - Update AI service configuration
   - Enhance business logic processing

3. **Error Handling**:
   - Check logs for detailed error messages
   - Verify API key validity
   - Ensure proper network connectivity

## API Reference

For detailed API documentation, see the OpenAPI documentation at `/docs` or `/redoc`.
