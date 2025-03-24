"""
Tests for User Session Management core functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from fastapi import Request

# Import the Session manager and shared models
from backend_core.user_session import SessionManager
from backend_core.auth_models import UserSession

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    return db

@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = MagicMock(spec=Request)
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    
    return request

def test_create_session(mock_db, mock_request):
    """Test creating a user session."""
    # Call the create_session method
    session = SessionManager.create_session(
        mock_db, 1, mock_request, 
        access_token="test-access-token", 
        refresh_token="test-refresh-token"
    )
    
    # Check that a session was added to the database
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    
    # Get the session that was added
    args, _ = mock_db.add.call_args
    added_session = args[0]
    
    # Verify session properties
    assert isinstance(added_session, UserSession)
    assert added_session.user_id == 1
    assert added_session.is_active is True
    assert added_session.access_token == "test-access-token"
    assert added_session.refresh_token == "test-refresh-token"
    assert added_session.ip_address == "127.0.0.1"
    assert "Mac computer" in added_session.device_info

def test_get_user_sessions(mock_db):
    """Test getting all sessions for a user."""
    # Setup mock sessions
    mock_sessions = [MagicMock(spec=UserSession), MagicMock(spec=UserSession)]
    mock_db.query.return_value.filter_by.return_value.all.return_value = mock_sessions
    
    # Call the get_user_sessions method
    sessions = SessionManager.get_user_sessions(mock_db, 1)
    
    # Check that sessions were returned
    assert sessions == mock_sessions
    mock_db.query.assert_called_once()

def test_terminate_user_session_success(mock_db):
    """Test terminating a user session successfully."""
    # Setup mock session
    session = MagicMock(spec=UserSession)
    session.is_active = True
    mock_db.query.return_value.filter_by.return_value.first.return_value = session
    
    # Call the terminate_user_session method
    result = SessionManager.terminate_user_session(mock_db, "test-session-id", "Test reason")
    
    # Check that the result is True
    assert result is True
    
    # Check that the session was updated
    assert session.is_active is False
    assert session.terminated_at is not None
    assert session.termination_reason == "Test reason"
    
    # Verify that the commit was called
    mock_db.commit.assert_called_once()

def test_terminate_user_session_not_found(mock_db):
    """Test terminating a user session that doesn't exist."""
    # Setup
    mock_db.query.return_value.filter_by.return_value.first.return_value = None
    
    # Call the terminate_user_session method
    result = SessionManager.terminate_user_session(mock_db, "non-existent-session-id")
    
    # Check that the result is False
    assert result is False
    
    # Verify that the commit was not called
    mock_db.commit.assert_not_called()

def test_terminate_all_user_sessions_except(mock_db):
    """Test terminating all sessions for a user except the current one."""
    # Setup mock sessions
    session1 = MagicMock(spec=UserSession)
    session1.session_id = "session-1"
    session1.is_active = True
    
    session2 = MagicMock(spec=UserSession)
    session2.session_id = "session-2"
    session2.is_active = True
    
    session3 = MagicMock(spec=UserSession)
    session3.session_id = "current-session-id"
    session3.is_active = True
    
    mock_db.query.return_value.filter_by.return_value.all.return_value = [session1, session2, session3]
    
    # Call the terminate_all_user_sessions_except method
    count = SessionManager.terminate_all_user_sessions_except(mock_db, 1, "current-session-id")
    
    # Check that the count is correct (should be 2 sessions terminated)
    assert count == 2
    
    # Check that the sessions were updated correctly
    assert session1.is_active is False
    assert session1.terminated_at is not None
    assert session1.termination_reason == "User terminated all other sessions"
    
    assert session2.is_active is False
    assert session2.terminated_at is not None
    assert session2.termination_reason == "User terminated all other sessions"
    
    # Current session should not be terminated
    assert session3.is_active is True
    
    # Verify that the commit was called
    mock_db.commit.assert_called_once()

def test_update_session_activity_success(mock_db):
    """Test updating the last activity timestamp for a session."""
    # Setup mock session
    session = MagicMock(spec=UserSession)
    session.is_active = True
    mock_db.query.return_value.filter_by.return_value.first.return_value = session
    
    # Call the update_session_activity method
    result = SessionManager.update_session_activity(mock_db, "test-session-id")
    
    # Check that the result is True
    assert result is True
    
    # Check that the session was updated
    assert session.last_active is not None
    
    # Verify that the commit was called
    mock_db.commit.assert_called_once()

def test_update_session_activity_not_found(mock_db):
    """Test updating the last activity timestamp for a session that doesn't exist."""
    # Setup
    mock_db.query.return_value.filter_by.return_value.first.return_value = None
    
    # Call the update_session_activity method
    result = SessionManager.update_session_activity(mock_db, "non-existent-session-id")
    
    # Check that the result is False
    assert result is False
    
    # Verify that the commit was not called
    mock_db.commit.assert_not_called()

def test_get_session_by_id_success(mock_db):
    """Test getting a session by ID."""
    # Setup mock session
    session = MagicMock(spec=UserSession)
    session.session_id = "test-session-id"
    session.is_active = True
    mock_db.query.return_value.filter_by.return_value.first.return_value = session
    
    # Call the get_session_by_id method
    result = SessionManager.get_session_by_id(mock_db, "test-session-id")
    
    # Check that the session was returned
    assert result == session

def test_get_session_by_id_with_user_id(mock_db):
    """Test getting a session by ID with user ID verification."""
    # Setup mock session
    session = MagicMock(spec=UserSession)
    session.session_id = "test-session-id"
    session.user_id = 1
    session.is_active = True
    mock_db.query.return_value.filter_by.return_value.filter_by.return_value.first.return_value = session
    
    # Call the get_session_by_id method
    result = SessionManager.get_session_by_id(mock_db, "test-session-id", 1)
    
    # Check that the session was returned
    assert result == session

def test_get_session_by_id_not_found(mock_db):
    """Test getting a session by ID that doesn't exist."""
    # Setup
    mock_db.query.return_value.filter_by.return_value.first.return_value = None
    
    # Call the get_session_by_id method
    result = SessionManager.get_session_by_id(mock_db, "non-existent-session-id")
    
    # Check that None was returned
    assert result is None

def test_cleanup_inactive_sessions(mock_db):
    """Test cleaning up inactive sessions."""
    # Setup mock sessions
    session1 = MagicMock(spec=UserSession)
    session1.is_active = False
    session1.terminated_at = datetime.utcnow() - timedelta(days=31)
    
    session2 = MagicMock(spec=UserSession)
    session2.is_active = False
    session2.terminated_at = datetime.utcnow() - timedelta(days=31)
    
    # Setup the mock query chain
    mock_query = mock_db.query.return_value
    mock_filter_by = mock_query.filter_by.return_value
    mock_filter = mock_filter_by.filter.return_value
    mock_params = mock_filter.params.return_value
    mock_params.all.return_value = [session1, session2]
    
    # Call the cleanup_inactive_sessions method
    count = SessionManager.cleanup_inactive_sessions(mock_db, 30)
    
    # Check that the count is correct
    assert count == 2
    
    # Verify that the sessions were deleted
    assert mock_db.delete.call_count == 2
    
    # Verify that the commit was called
    mock_db.commit.assert_called_once()

def test_blacklist_refresh_token_success():
    """Test blacklisting a refresh token successfully."""
    # Call the blacklist_refresh_token method with a patch for redis
    with patch('redis.Redis.set', return_value=True):
        result = SessionManager.blacklist_refresh_token("test-refresh-token", timedelta(days=7))
    
    # Check that the result is True
    assert result is True

def test_blacklist_refresh_token_failure():
    """Test blacklisting a refresh token with a failure."""
    # Call the blacklist_refresh_token method with a patch for redis that raises an exception
    with patch('redis.Redis.set', side_effect=Exception("Redis error")):
        result = SessionManager.blacklist_refresh_token("test-refresh-token", timedelta(days=7))
    
    # Check that the result is False
    assert result is False

def test_is_refresh_token_blacklisted_true():
    """Test checking if a refresh token is blacklisted (true case)."""
    # Call the is_refresh_token_blacklisted method with a patch for redis
    with patch('redis.Redis.exists', return_value=1):
        result = SessionManager.is_refresh_token_blacklisted("blacklisted-token")
    
    # Check that the result is True
    assert result is True

def test_is_refresh_token_blacklisted_false():
    """Test checking if a refresh token is blacklisted (false case)."""
    # Call the is_refresh_token_blacklisted method with a patch for redis
    with patch('redis.Redis.exists', return_value=0):
        result = SessionManager.is_refresh_token_blacklisted("non-blacklisted-token")
    
    # Check that the result is False
    assert result is False

def test_is_refresh_token_blacklisted_error():
    """Test checking if a refresh token is blacklisted with a redis error."""
    # Call the is_refresh_token_blacklisted method with a patch for redis that raises an exception
    with patch('redis.Redis.exists', side_effect=Exception("Redis error")):
        result = SessionManager.is_refresh_token_blacklisted("test-token")
    
    # Check that the result is False (fallback behavior)
    assert result is False
