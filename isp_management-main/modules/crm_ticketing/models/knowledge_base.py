"""
Knowledge Base models for the CRM & Ticketing module.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Table
from sqlalchemy.orm import relationship

from backend_core.database import Base


# Association table for article tags
article_tags = Table(
    "crm_kb_article_tags",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("crm_kb_articles.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("crm_tags.id"), primary_key=True)
)


class KnowledgeBaseCategory(Base):
    """
    Knowledge Base category model.
    
    Represents a category for organizing knowledge base articles.
    """
    __tablename__ = "crm_kb_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("crm_kb_categories.id"), nullable=True)
    icon = Column(String(50), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent = relationship("KnowledgeBaseCategory", remote_side=[id], backref="subcategories")
    articles = relationship("KnowledgeBaseArticle", back_populates="category")
    
    def __repr__(self):
        return f"<KnowledgeBaseCategory(id={self.id}, name={self.name})>"


class KnowledgeBaseArticle(Base):
    """
    Knowledge Base article model.
    
    Represents an article in the knowledge base that can be used to help
    customers and support staff resolve common issues.
    """
    __tablename__ = "crm_kb_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False)
    excerpt = Column(String(500), nullable=True)
    category_id = Column(Integer, ForeignKey("crm_kb_categories.id"), nullable=False)
    
    # Article metadata
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    last_updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    is_published = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    is_internal = Column(Boolean, default=False)  # Whether visible to customers
    
    # SEO and metadata
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    keywords = Column(JSON, default=list)
    
    # Related content
    related_article_ids = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    
    # Relationships
    category = relationship("KnowledgeBaseCategory", back_populates="articles")
    author = relationship("User", foreign_keys=[author_id])
    editor = relationship("User", foreign_keys=[last_updated_by])
    tags = relationship("Tag", secondary=article_tags)
    
    def __repr__(self):
        return f"<KnowledgeBaseArticle(id={self.id}, title={self.title})>"
    
    @property
    def helpfulness_ratio(self):
        """Calculate the helpfulness ratio of the article."""
        total = self.helpful_count + self.not_helpful_count
        if total == 0:
            return 0
        return (self.helpful_count / total) * 100
