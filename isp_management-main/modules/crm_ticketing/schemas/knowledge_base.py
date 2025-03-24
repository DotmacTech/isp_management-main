"""
Knowledge Base schemas for the CRM & Ticketing module.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator
import re


class KBCategoryBase(BaseModel):
    """Base schema for knowledge base categories."""
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    parent_id: Optional[int] = Field(None, description="ID of the parent category")
    icon: Optional[str] = Field(None, max_length=50, description="Icon identifier for the category")
    display_order: Optional[int] = Field(0, ge=0, description="Display order for sorting")
    is_active: Optional[bool] = Field(True, description="Whether this category is active")


class KBCategoryCreate(KBCategoryBase):
    """Schema for creating a new knowledge base category."""
    slug: Optional[str] = Field(None, min_length=1, max_length=100, description="URL-friendly slug")
    
    @validator('slug', pre=True)
    def generate_slug(cls, v, values):
        """Generate a slug from the name if not provided."""
        if not v and 'name' in values:
            # Convert to lowercase, replace spaces with hyphens, remove special chars
            slug = re.sub(r'[^a-z0-9\-]', '', values['name'].lower().replace(' ', '-'))
            return slug
        return v


class KBCategoryUpdate(BaseModel):
    """Schema for updating an existing knowledge base category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    icon: Optional[str] = Field(None, max_length=50)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class KBCategoryResponse(KBCategoryBase):
    """Schema for knowledge base category response."""
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class KBArticleBase(BaseModel):
    """Base schema for knowledge base articles."""
    title: str = Field(..., min_length=1, max_length=255, description="Article title")
    content: str = Field(..., description="Article content in Markdown format")
    excerpt: Optional[str] = Field(None, max_length=500, description="Short excerpt/summary of the article")
    category_id: int = Field(..., description="ID of the category this article belongs to")
    is_published: Optional[bool] = Field(False, description="Whether this article is published")
    is_featured: Optional[bool] = Field(False, description="Whether this article is featured")
    is_internal: Optional[bool] = Field(False, description="Whether this article is for internal use only")
    meta_title: Optional[str] = Field(None, max_length=255, description="SEO meta title")
    meta_description: Optional[str] = Field(None, max_length=500, description="SEO meta description")
    keywords: Optional[List[str]] = Field(None, description="SEO keywords")
    related_article_ids: Optional[List[int]] = Field(None, description="IDs of related articles")
    tag_ids: Optional[List[int]] = Field(None, description="IDs of tags associated with the article")


class KBArticleCreate(KBArticleBase):
    """Schema for creating a new knowledge base article."""
    slug: Optional[str] = Field(None, min_length=1, max_length=255, description="URL-friendly slug")
    
    @validator('slug', pre=True)
    def generate_slug(cls, v, values):
        """Generate a slug from the title if not provided."""
        if not v and 'title' in values:
            # Convert to lowercase, replace spaces with hyphens, remove special chars
            slug = re.sub(r'[^a-z0-9\-]', '', values['title'].lower().replace(' ', '-'))
            return slug
        return v
    
    @validator('excerpt', pre=True)
    def generate_excerpt(cls, v, values):
        """Generate an excerpt from the content if not provided."""
        if not v and 'content' in values:
            # Take first 150 characters of content, strip markdown
            content = re.sub(r'[#*_~`\[\]\(\)\{\}]', '', values['content'])
            excerpt = content[:150] + ('...' if len(content) > 150 else '')
            return excerpt
        return v


class KBArticleUpdate(BaseModel):
    """Schema for updating an existing knowledge base article."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    excerpt: Optional[str] = Field(None, max_length=500)
    category_id: Optional[int] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_internal: Optional[bool] = None
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=500)
    keywords: Optional[List[str]] = None
    related_article_ids: Optional[List[int]] = None
    tag_ids: Optional[List[int]] = None


class KBArticleResponse(KBArticleBase):
    """Schema for knowledge base article response."""
    id: int
    slug: str
    author_id: int
    last_updated_by: Optional[int] = None
    view_count: int
    helpful_count: int
    not_helpful_count: int
    helpfulness_ratio: float
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
