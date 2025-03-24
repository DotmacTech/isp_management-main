"""
Core database utilities for the ISP Management Platform.

This module provides database utilities that are used across
different modules of the ISP Management Platform.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from backend_core.database import Base, get_engine

# Configure logging
logger = logging.getLogger(__name__)


def get_session() -> Session:
    """
    Get a new database session.
    
    Returns:
        SQLAlchemy Session object.
    """
    from backend_core.database import SessionLocal
    return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get a database session.
    
    Yields:
        SQLAlchemy Session object.
    """
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Yields:
        SQLAlchemy Session object.
    
    Example:
        with db_session() as session:
            result = session.query(Model).all()
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def create_tables() -> None:
    """
    Create all tables defined in the Base metadata.
    
    This function should be used with caution, as it will create
    all tables in the database that are defined in the Base metadata.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Created all tables")


def drop_tables() -> None:
    """
    Drop all tables defined in the Base metadata.
    
    This function should be used with extreme caution, as it will drop
    all tables in the database that are defined in the Base metadata.
    """
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    logger.info("Dropped all tables")


def execute_raw_sql(sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Execute raw SQL and return the results.
    
    Args:
        sql: SQL statement to execute.
        params: Parameters for the SQL statement.
    
    Returns:
        List of dictionaries containing the results.
    """
    engine = get_engine()
    with engine.connect() as connection:
        result = connection.execute(sql, params or {})
        return [dict(row) for row in result]


def get_model_by_id(model_class: Any, model_id: str, session: Optional[Session] = None) -> Optional[Any]:
    """
    Get a model instance by its ID.
    
    Args:
        model_class: SQLAlchemy model class.
        model_id: ID of the model instance.
        session: SQLAlchemy session to use. If None, a new session will be created.
    
    Returns:
        Model instance or None if not found.
    """
    if session is None:
        with db_session() as session:
            return session.query(model_class).filter(model_class.id == model_id).first()
    else:
        return session.query(model_class).filter(model_class.id == model_id).first()


def create_model(model_class: Any, data: Dict[str, Any], session: Optional[Session] = None) -> Any:
    """
    Create a new model instance.
    
    Args:
        model_class: SQLAlchemy model class.
        data: Dictionary containing model data.
        session: SQLAlchemy session to use. If None, a new session will be created.
    
    Returns:
        Created model instance.
    """
    instance = model_class(**data)
    
    if session is None:
        with db_session() as session:
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance
    else:
        session.add(instance)
        session.flush()
        return instance


def update_model(model: Any, data: Dict[str, Any], session: Optional[Session] = None) -> Any:
    """
    Update a model instance.
    
    Args:
        model: SQLAlchemy model instance.
        data: Dictionary containing model data.
        session: SQLAlchemy session to use. If None, a new session will be created.
    
    Returns:
        Updated model instance.
    """
    for key, value in data.items():
        if hasattr(model, key):
            setattr(model, key, value)
    
    if session is None:
        with db_session() as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return model
    else:
        session.add(model)
        session.flush()
        return model


def delete_model(model: Any, session: Optional[Session] = None) -> bool:
    """
    Delete a model instance.
    
    Args:
        model: SQLAlchemy model instance.
        session: SQLAlchemy session to use. If None, a new session will be created.
    
    Returns:
        True if the model was deleted, False otherwise.
    """
    if session is None:
        with db_session() as session:
            session.delete(model)
            session.commit()
            return True
    else:
        session.delete(model)
        session.flush()
        return True
