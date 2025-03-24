"""
Network Nodes API Router for the ISP Management Platform

This module provides API endpoints for managing network nodes in the monitoring system.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel, IPvAnyAddress, Field

from modules.core.database import get_db
from modules.core.auth import get_current_user, check_permissions
from modules.monitoring.models import NetworkNode, NodeType
from modules.monitoring.schemas.network_node import (
    NetworkNodeCreate, 
    NetworkNodeUpdate, 
    NetworkNodeResponse
)

router = APIRouter(
    prefix="/network-nodes",
    tags=["network-nodes"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[NetworkNodeResponse])
async def get_network_nodes(
    skip: int = Query(0, description="Skip N items"),
    limit: int = Query(100, description="Limit to N items"),
    node_type: Optional[str] = Query(None, description="Filter by node type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    search: Optional[str] = Query(None, description="Search by name or IP address"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a list of network nodes with optional filtering.
    
    Requires monitoring:read permission.
    """
    check_permissions(current_user, "monitoring:read")
    
    query = db.query(NetworkNode)
    
    # Apply filters
    if node_type:
        try:
            node_type_enum = NodeType(node_type)
            query = query.filter(NetworkNode.type == node_type_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid node type: {node_type}")
    
    if is_active is not None:
        query = query.filter(NetworkNode.is_active == is_active)
    
    if location:
        query = query.filter(NetworkNode.location.ilike(f"%{location}%"))
    
    if search:
        query = query.filter(
            (NetworkNode.name.ilike(f"%{search}%")) | 
            (NetworkNode.ip_address.ilike(f"%{search}%"))
        )
    
    # Apply pagination
    nodes = query.offset(skip).limit(limit).all()
    return nodes


@router.get("/{node_id}", response_model=NetworkNodeResponse)
async def get_network_node(
    node_id: str = Path(..., description="The ID of the network node to get"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific network node by ID.
    
    Requires monitoring:read permission.
    """
    check_permissions(current_user, "monitoring:read")
    
    node = db.query(NetworkNode).filter(NetworkNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Network node with ID {node_id} not found")
    
    return node


@router.post("/", response_model=NetworkNodeResponse, status_code=201)
async def create_network_node(
    node: NetworkNodeCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new network node.
    
    Requires monitoring:write permission.
    """
    check_permissions(current_user, "monitoring:write")
    
    # Check if a node with the same ID already exists
    existing_node = db.query(NetworkNode).filter(NetworkNode.id == node.id).first()
    if existing_node:
        raise HTTPException(status_code=400, detail=f"Network node with ID {node.id} already exists")
    
    # Check if a node with the same IP address already exists
    existing_ip = db.query(NetworkNode).filter(NetworkNode.ip_address == node.ip_address).first()
    if existing_ip:
        raise HTTPException(status_code=400, detail=f"Network node with IP address {node.ip_address} already exists")
    
    # Create new network node
    db_node = NetworkNode(**node.dict())
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    
    return db_node


@router.put("/{node_id}", response_model=NetworkNodeResponse)
async def update_network_node(
    node: NetworkNodeUpdate,
    node_id: str = Path(..., description="The ID of the network node to update"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing network node.
    
    Requires monitoring:write permission.
    """
    check_permissions(current_user, "monitoring:write")
    
    # Get the existing node
    db_node = db.query(NetworkNode).filter(NetworkNode.id == node_id).first()
    if not db_node:
        raise HTTPException(status_code=404, detail=f"Network node with ID {node_id} not found")
    
    # Check if IP address is being changed and if it's already in use
    if node.ip_address and node.ip_address != db_node.ip_address:
        existing_ip = db.query(NetworkNode).filter(
            NetworkNode.ip_address == node.ip_address,
            NetworkNode.id != node_id
        ).first()
        if existing_ip:
            raise HTTPException(status_code=400, detail=f"Network node with IP address {node.ip_address} already exists")
    
    # Update node attributes
    update_data = node.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_node, key, value)
    
    db.commit()
    db.refresh(db_node)
    
    return db_node


@router.delete("/{node_id}", status_code=204)
async def delete_network_node(
    node_id: str = Path(..., description="The ID of the network node to delete"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a network node.
    
    Requires monitoring:delete permission.
    """
    check_permissions(current_user, "monitoring:delete")
    
    # Get the existing node
    db_node = db.query(NetworkNode).filter(NetworkNode.id == node_id).first()
    if not db_node:
        raise HTTPException(status_code=404, detail=f"Network node with ID {node_id} not found")
    
    # Delete the node
    db.delete(db_node)
    db.commit()
    
    return None
