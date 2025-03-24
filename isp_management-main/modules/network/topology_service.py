"""
Network Topology Service for the Network Management Module.
"""

import logging
import json
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple, Union, Set
from datetime import datetime
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import NotFoundException, ValidationError
from core.services import BaseService
from modules.network.models import Device, DeviceType, DeviceStatus

logger = logging.getLogger(__name__)


class TopologyService(BaseService):
    """Service for managing and visualizing network topology."""
    
    async def discover_topology(
        self,
        session: AsyncSession,
        root_device_id: Optional[int] = None,
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Discover network topology starting from a root device.
        
        Args:
            session: Database session
            root_device_id: ID of the root device to start discovery from
            max_depth: Maximum depth of discovery
            
        Returns:
            Dictionary representing the discovered topology
            
        Raises:
            NotFoundException: If the root device is not found
        """
        # If no root device is specified, use all active devices as roots
        if root_device_id is None:
            # Get all active devices
            query = select(Device).where(Device.status == DeviceStatus.ACTIVE)
            result = await session.execute(query)
            devices = result.scalars().all()
            
            if not devices:
                return {"nodes": [], "links": []}
            
            # Discover topology from each device
            topologies = []
            for device in devices:
                topology = await self._discover_from_device(session, device, max_depth)
                topologies.append(topology)
            
            # Merge topologies
            return self._merge_topologies(topologies)
        else:
            # Get the root device
            device = await session.get(Device, root_device_id)
            if not device:
                raise NotFoundException(f"Device with ID {root_device_id} not found")
            
            # Discover topology from the root device
            return await self._discover_from_device(session, device, max_depth)
    
    async def _discover_from_device(
        self,
        session: AsyncSession,
        device: Device,
        max_depth: int,
        current_depth: int = 0,
        visited: Optional[Set[int]] = None
    ) -> Dict[str, Any]:
        """
        Recursively discover network topology from a device.
        
        Args:
            session: Database session
            device: The device to discover from
            max_depth: Maximum depth of discovery
            current_depth: Current depth of discovery
            visited: Set of visited device IDs
            
        Returns:
            Dictionary representing the discovered topology
        """
        if visited is None:
            visited = set()
        
        # Add current device to visited set
        visited.add(device.id)
        
        # Create node for current device
        node = {
            "id": device.id,
            "name": device.name,
            "type": device.device_type.value,
            "status": device.status.value,
            "ip_address": device.ip_address,
            "manufacturer": device.manufacturer,
            "model": device.model
        }
        
        nodes = [node]
        links = []
        
        # Stop if we've reached the maximum depth
        if current_depth >= max_depth:
            return {"nodes": nodes, "links": links}
        
        # In a real implementation, this would query the device for its neighbors
        # For now, we'll simulate neighbor discovery based on device type
        
        # Get potential neighbors based on device type
        potential_neighbors = await self._get_potential_neighbors(session, device)
        
        # Add neighbors to topology
        for neighbor in potential_neighbors:
            if neighbor.id not in visited:
                # Add link between current device and neighbor
                links.append({
                    "source": device.id,
                    "target": neighbor.id,
                    "type": "physical"  # This could be different based on connection type
                })
                
                # Recursively discover from neighbor
                neighbor_topology = await self._discover_from_device(
                    session, neighbor, max_depth, current_depth + 1, visited
                )
                
                # Add neighbor nodes and links to topology
                nodes.extend(neighbor_topology["nodes"])
                links.extend(neighbor_topology["links"])
        
        return {"nodes": nodes, "links": links}
    
    async def _get_potential_neighbors(
        self,
        session: AsyncSession,
        device: Device
    ) -> List[Device]:
        """
        Get potential neighbors of a device based on its type.
        
        Args:
            session: Database session
            device: The device to get neighbors for
            
        Returns:
            List of potential neighbor devices
        """
        # In a real implementation, this would query the device for its neighbors
        # For now, we'll simulate neighbor discovery based on device type and IP subnet
        
        # Extract subnet from device IP
        ip_parts = device.ip_address.split(".")
        subnet_prefix = ".".join(ip_parts[:3])
        
        # Get devices in the same subnet
        query = select(Device).where(
            and_(
                Device.id != device.id,
                Device.ip_address.like(f"{subnet_prefix}.%"),
                Device.status == DeviceStatus.ACTIVE
            )
        )
        
        # Apply additional filters based on device type
        if device.device_type == DeviceType.ROUTER:
            # Routers connect to other routers, switches, and firewalls
            query = query.where(
                Device.device_type.in_([DeviceType.ROUTER, DeviceType.SWITCH, DeviceType.FIREWALL])
            )
        elif device.device_type == DeviceType.SWITCH:
            # Switches connect to routers, other switches, and access points
            query = query.where(
                Device.device_type.in_([DeviceType.ROUTER, DeviceType.SWITCH, DeviceType.ACCESS_POINT])
            )
        elif device.device_type == DeviceType.FIREWALL:
            # Firewalls connect to routers and switches
            query = query.where(
                Device.device_type.in_([DeviceType.ROUTER, DeviceType.SWITCH])
            )
        elif device.device_type == DeviceType.ACCESS_POINT:
            # Access points connect to switches
            query = query.where(
                Device.device_type == DeviceType.SWITCH
            )
        elif device.device_type == DeviceType.OLT:
            # OLTs connect to routers, switches, and ONUs
            query = query.where(
                Device.device_type.in_([DeviceType.ROUTER, DeviceType.SWITCH, DeviceType.ONU])
            )
        elif device.device_type == DeviceType.ONU:
            # ONUs connect to OLTs
            query = query.where(
                Device.device_type == DeviceType.OLT
            )
        
        result = await session.execute(query)
        return result.scalars().all()
    
    def _merge_topologies(self, topologies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple topologies into a single topology.
        
        Args:
            topologies: List of topologies to merge
            
        Returns:
            Merged topology
        """
        merged_nodes = {}
        merged_links = {}
        
        # Merge nodes and links
        for topology in topologies:
            for node in topology["nodes"]:
                merged_nodes[node["id"]] = node
            
            for link in topology["links"]:
                link_key = f"{link['source']}-{link['target']}"
                merged_links[link_key] = link
        
        return {
            "nodes": list(merged_nodes.values()),
            "links": list(merged_links.values())
        }
    
    async def export_topology(
        self,
        session: AsyncSession,
        format: str = "json",
        root_device_id: Optional[int] = None,
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Export network topology in various formats.
        
        Args:
            session: Database session
            format: Export format (json, graphml, gexf)
            root_device_id: ID of the root device to start discovery from
            max_depth: Maximum depth of discovery
            
        Returns:
            Dictionary with the exported topology
            
        Raises:
            ValidationError: If the export format is invalid
        """
        # Discover topology
        topology = await self.discover_topology(session, root_device_id, max_depth)
        
        # Convert to NetworkX graph
        G = nx.Graph()
        
        # Add nodes
        for node in topology["nodes"]:
            G.add_node(
                node["id"],
                name=node["name"],
                type=node["type"],
                status=node["status"],
                ip_address=node["ip_address"]
            )
        
        # Add links
        for link in topology["links"]:
            G.add_edge(
                link["source"],
                link["target"],
                type=link["type"]
            )
        
        # Export in requested format
        if format == "json":
            return {
                "format": "json",
                "data": topology
            }
        elif format == "graphml":
            # Export as GraphML
            import io
            output = io.StringIO()
            nx.write_graphml(G, output)
            return {
                "format": "graphml",
                "data": output.getvalue()
            }
        elif format == "gexf":
            # Export as GEXF
            import io
            output = io.StringIO()
            nx.write_gexf(G, output)
            return {
                "format": "gexf",
                "data": output.getvalue()
            }
        else:
            raise ValidationError(f"Unsupported export format: {format}")
    
    async def get_device_neighbors(
        self,
        session: AsyncSession,
        device_id: int,
        max_depth: int = 1
    ) -> Dict[str, Any]:
        """
        Get the neighbors of a device.
        
        Args:
            session: Database session
            device_id: Device ID
            max_depth: Maximum depth of neighbor discovery
            
        Returns:
            Dictionary with the device's neighbors
            
        Raises:
            NotFoundException: If the device is not found
        """
        # Get the device
        device = await session.get(Device, device_id)
        if not device:
            raise NotFoundException(f"Device with ID {device_id} not found")
        
        # Discover topology from the device with limited depth
        topology = await self._discover_from_device(session, device, max_depth)
        
        # Remove the device itself from the nodes
        nodes = [node for node in topology["nodes"] if node["id"] != device_id]
        
        # Filter links to only include direct connections to the device
        direct_links = [
            link for link in topology["links"]
            if link["source"] == device_id or link["target"] == device_id
        ]
        
        return {
            "device_id": device_id,
            "device_name": device.name,
            "neighbors": nodes,
            "connections": direct_links
        }
    
    async def analyze_topology(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Analyze network topology for insights.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary with topology analysis
        """
        # Discover full topology
        topology = await self.discover_topology(session)
        
        # Convert to NetworkX graph
        G = nx.Graph()
        
        # Add nodes
        for node in topology["nodes"]:
            G.add_node(
                node["id"],
                name=node["name"],
                type=node["type"],
                status=node["status"]
            )
        
        # Add links
        for link in topology["links"]:
            G.add_edge(
                link["source"],
                link["target"],
                type=link["type"]
            )
        
        # Calculate basic metrics
        try:
            avg_degree = sum(dict(G.degree()).values()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0
            density = nx.density(G)
            connected_components = list(nx.connected_components(G))
            num_connected_components = len(connected_components)
            
            # Find central nodes
            if G.number_of_nodes() > 0:
                degree_centrality = nx.degree_centrality(G)
                betweenness_centrality = nx.betweenness_centrality(G)
                closeness_centrality = nx.closeness_centrality(G)
                
                # Get top 5 central nodes by degree
                top_degree_nodes = sorted(
                    degree_centrality.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                # Get top 5 central nodes by betweenness
                top_betweenness_nodes = sorted(
                    betweenness_centrality.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            else:
                top_degree_nodes = []
                top_betweenness_nodes = []
            
            # Count nodes by type
            node_types = {}
            for node in topology["nodes"]:
                node_type = node["type"]
                if node_type in node_types:
                    node_types[node_type] += 1
                else:
                    node_types[node_type] = 1
            
            # Identify potential bottlenecks
            potential_bottlenecks = []
            if G.number_of_nodes() > 0:
                for node_id, bc in top_betweenness_nodes:
                    if bc > 0.5:  # Arbitrary threshold
                        node_data = next((n for n in topology["nodes"] if n["id"] == node_id), None)
                        if node_data:
                            potential_bottlenecks.append({
                                "id": node_id,
                                "name": node_data["name"],
                                "type": node_data["type"],
                                "betweenness_centrality": bc
                            })
            
            return {
                "metrics": {
                    "node_count": G.number_of_nodes(),
                    "link_count": G.number_of_edges(),
                    "average_degree": avg_degree,
                    "density": density,
                    "connected_components": num_connected_components
                },
                "node_types": node_types,
                "central_nodes": {
                    "by_degree": [
                        {
                            "id": node_id,
                            "name": next(n["name"] for n in topology["nodes"] if n["id"] == node_id),
                            "centrality": centrality
                        }
                        for node_id, centrality in top_degree_nodes
                    ],
                    "by_betweenness": [
                        {
                            "id": node_id,
                            "name": next(n["name"] for n in topology["nodes"] if n["id"] == node_id),
                            "centrality": centrality
                        }
                        for node_id, centrality in top_betweenness_nodes
                    ]
                },
                "potential_bottlenecks": potential_bottlenecks
            }
        except Exception as e:
            logger.error(f"Error analyzing topology: {str(e)}")
            return {
                "error": f"Failed to analyze topology: {str(e)}",
                "metrics": {
                    "node_count": G.number_of_nodes(),
                    "link_count": G.number_of_edges()
                }
            }
