"""
Network Service for the ISP Management Platform Monitoring Module

This module provides services for managing network nodes and collecting network performance metrics.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from modules.monitoring.models import NetworkNode, NodeType, SystemMetric, MetricType
from modules.monitoring.schemas.network_node import NetworkNodeCreate, NetworkNodeUpdate
from modules.monitoring.collectors.network_performance_collector import NetworkPerformanceCollector
from modules.monitoring.elasticsearch import ElasticsearchClient

logger = logging.getLogger(__name__)


class NetworkService:
    """
    Service for managing network nodes and collecting network performance metrics.
    """
    
    def __init__(self, db: Session):
        """Initialize the network service with a database session."""
        self.db = db
        self.es_client = ElasticsearchClient()
    
    def get_all_nodes(
        self, 
        skip: int = 0, 
        limit: int = 100,
        node_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        location: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[NetworkNode]:
        """
        Get all network nodes with optional filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            node_type: Filter by node type
            is_active: Filter by active status
            location: Filter by location
            search: Search by name or IP address
            
        Returns:
            List of NetworkNode objects
        """
        query = self.db.query(NetworkNode)
        
        # Apply filters
        if node_type:
            try:
                node_type_enum = NodeType(node_type)
                query = query.filter(NetworkNode.type == node_type_enum)
            except ValueError:
                logger.warning(f"Invalid node type: {node_type}")
        
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
        return query.offset(skip).limit(limit).all()
    
    def get_node_by_id(self, node_id: str) -> Optional[NetworkNode]:
        """
        Get a network node by ID.
        
        Args:
            node_id: ID of the network node
            
        Returns:
            NetworkNode object or None if not found
        """
        return self.db.query(NetworkNode).filter(NetworkNode.id == node_id).first()
    
    def get_node_by_ip(self, ip_address: str) -> Optional[NetworkNode]:
        """
        Get a network node by IP address.
        
        Args:
            ip_address: IP address of the network node
            
        Returns:
            NetworkNode object or None if not found
        """
        return self.db.query(NetworkNode).filter(NetworkNode.ip_address == ip_address).first()
    
    def create_node(self, node: NetworkNodeCreate) -> NetworkNode:
        """
        Create a new network node.
        
        Args:
            node: NetworkNodeCreate object
            
        Returns:
            Created NetworkNode object
            
        Raises:
            ValueError: If a node with the same ID or IP address already exists
        """
        # Check if a node with the same ID already exists
        existing_node = self.get_node_by_id(node.id)
        if existing_node:
            raise ValueError(f"Network node with ID {node.id} already exists")
        
        # Check if a node with the same IP address already exists
        existing_ip = self.get_node_by_ip(node.ip_address)
        if existing_ip:
            raise ValueError(f"Network node with IP address {node.ip_address} already exists")
        
        # Create new network node
        db_node = NetworkNode(**node.model_dump())
        self.db.add(db_node)
        self.db.commit()
        self.db.refresh(db_node)
        
        logger.info(f"Created network node: {db_node.name} ({db_node.id})")
        return db_node
    
    def update_node(self, node_id: str, node: NetworkNodeUpdate) -> NetworkNode:
        """
        Update an existing network node.
        
        Args:
            node_id: ID of the network node to update
            node: NetworkNodeUpdate object
            
        Returns:
            Updated NetworkNode object
            
        Raises:
            ValueError: If the node does not exist or if the IP address is already in use
        """
        # Get the existing node
        db_node = self.get_node_by_id(node_id)
        if not db_node:
            raise ValueError(f"Network node with ID {node_id} not found")
        
        # Check if IP address is being updated and if it's already in use
        if node.ip_address and node.ip_address != db_node.ip_address:
            existing_ip = self.get_node_by_ip(node.ip_address)
            if existing_ip:
                raise ValueError(f"Network node with IP address {node.ip_address} already exists")
        
        # Update node attributes
        update_data = node.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_node, key, value)
        
        # Update timestamp
        db_node.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_node)
        
        logger.info(f"Updated network node: {db_node.name} ({db_node.id})")
        return db_node
    
    def delete_node(self, node_id: str) -> bool:
        """
        Delete a network node.
        
        Args:
            node_id: ID of the network node to delete
            
        Returns:
            True if the node was deleted, False otherwise
            
        Raises:
            ValueError: If the node does not exist
        """
        # Get the existing node
        db_node = self.get_node_by_id(node_id)
        if not db_node:
            raise ValueError(f"Network node with ID {node_id} not found")
        
        # Delete the node
        self.db.delete(db_node)
        self.db.commit()
        
        logger.info(f"Deleted network node: {db_node.name} ({db_node.id})")
        return True
    
    def collect_network_metrics(self) -> Dict[str, Any]:
        """
        Collect network performance metrics for all active nodes.
        
        Returns:
            Dictionary with collection results
        """
        logger.info("Starting network metrics collection")
        
        # Create collector
        collector = NetworkPerformanceCollector(self.db)
        
        # Collect metrics
        collector.collect_all_metrics()
        
        # Save to database
        db_metrics = collector.save_to_database()
        
        # Send to Elasticsearch
        es_metrics = collector.send_to_elasticsearch()
        
        logger.info(f"Collected {len(db_metrics)} network metrics")
        
        return {
            "metrics_collected": len(db_metrics),
            "metrics_sent_to_elasticsearch": len(es_metrics),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_network_metrics(
        self,
        node_id: Optional[str] = None,
        metric_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get network metrics from Elasticsearch.
        
        Args:
            node_id: Filter by node ID
            metric_type: Filter by metric type
            start_time: Start time for metrics
            end_time: End time for metrics
            limit: Maximum number of metrics to return
            
        Returns:
            List of metric dictionaries
        """
        # Build Elasticsearch query
        query = {
            "bool": {
                "must": []
            }
        }
        
        if node_id:
            query["bool"]["must"].append({"term": {"node_id": node_id}})
        
        if metric_type:
            query["bool"]["must"].append({"term": {"metric_type": metric_type}})
        
        if start_time or end_time:
            time_range = {}
            if start_time:
                time_range["gte"] = start_time.isoformat()
            if end_time:
                time_range["lte"] = end_time.isoformat()
            
            query["bool"]["must"].append({"range": {"@timestamp": time_range}})
        
        # Execute Elasticsearch query
        try:
            index_pattern = "isp-network-metrics-*"
            search_body = {
                "query": query,
                "size": limit,
                "sort": [{"@timestamp": {"order": "desc"}}]
            }
            
            result = self.es_client.search(index=index_pattern, body=search_body)
            
            # Extract metrics from search results
            metrics = []
            for hit in result.get("hits", {}).get("hits", []):
                metrics.append(hit["_source"])
            
            return metrics
        
        except Exception as e:
            logger.error(f"Error querying Elasticsearch for network metrics: {str(e)}")
            return []
    
    def get_node_status_summary(self) -> Dict[str, Any]:
        """
        Get a summary of network node status.
        
        Returns:
            Dictionary with node status summary
        """
        total_nodes = self.db.query(func.count(NetworkNode.id)).scalar()
        active_nodes = self.db.query(func.count(NetworkNode.id)).filter(NetworkNode.is_active == True).scalar()
        inactive_nodes = total_nodes - active_nodes
        
        node_types = self.db.query(
            NetworkNode.type,
            func.count(NetworkNode.id)
        ).group_by(NetworkNode.type).all()
        
        type_counts = {str(node_type.name): count for node_type, count in node_types}
        
        return {
            "total_nodes": total_nodes,
            "active_nodes": active_nodes,
            "inactive_nodes": inactive_nodes,
            "node_types": type_counts,
            "timestamp": datetime.utcnow().isoformat()
        }
