"""
UNMS Network Topology Service.
"""
import logging
from typing import Dict, List, Any, Optional

from ..core import UNMSAPI
from .client import NetworkClient

logger = logging.getLogger('unms')


class TopologyService:
    """
    Service for working with UNMS network topology.
    
    This service provides methods for analyzing and manipulating network topology data.
    """
    
    def __init__(self, api_client: UNMSAPI):
        """
        Initialize the topology service.
        
        Args:
            api_client: UNMS API client instance
        """
        self.api = api_client
        self.client = NetworkClient(api_client)
    
    async def get_complete_topology(self) -> Dict[str, Any]:
        """
        Get the complete network topology with enhanced data.
        
        Returns:
            Enhanced topology data
        """
        # Get basic topology
        topology = await self.client.get_topology()
        
        # Enhance with additional information
        return self._enhance_topology(topology)
    
    def _enhance_topology(self, topology: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance topology data with additional calculated information.
        
        Args:
            topology: Basic topology data
            
        Returns:
            Enhanced topology data
        """
        enhanced = topology.copy()
        
        # Add node counts
        if 'nodes' in enhanced:
            enhanced['node_count'] = len(enhanced['nodes'])
            
            # Count by type
            type_counts = {}
            for node in enhanced['nodes']:
                node_type = node.get('type', 'unknown')
                if node_type not in type_counts:
                    type_counts[node_type] = 0
                type_counts[node_type] += 1
            
            enhanced['node_types'] = type_counts
        
        # Add link counts
        if 'links' in enhanced:
            enhanced['link_count'] = len(enhanced['links'])
            
            # Count by type
            type_counts = {}
            for link in enhanced['links']:
                link_type = link.get('type', 'unknown')
                if link_type not in type_counts:
                    type_counts[link_type] = 0
                type_counts[link_type] += 1
            
            enhanced['link_types'] = type_counts
        
        return enhanced
    
    async def find_path(self, source_id: str, target_id: str) -> List[Dict[str, Any]]:
        """
        Find the network path between two devices.
        
        Args:
            source_id: ID of the source device
            target_id: ID of the target device
            
        Returns:
            List of nodes and links representing the path
        """
        # Get topology
        topology = await self.client.get_topology()
        
        # Find path using breadth-first search
        return self._find_path_bfs(topology, source_id, target_id)
    
    def _find_path_bfs(self, topology: Dict[str, Any], 
                     source_id: str, target_id: str) -> List[Dict[str, Any]]:
        """
        Find a path using breadth-first search.
        
        Args:
            topology: Network topology data
            source_id: ID of the source device
            target_id: ID of the target device
            
        Returns:
            List of nodes and links representing the path
        """
        if 'nodes' not in topology or 'links' not in topology:
            return []
        
        # Create adjacency list
        adjacency = {}
        for node in topology['nodes']:
            node_id = node['id']
            adjacency[node_id] = []
        
        for link in topology['links']:
            source = link.get('source')
            target = link.get('target')
            if source in adjacency and target in adjacency:
                adjacency[source].append({'node': target, 'link': link})
                adjacency[target].append({'node': source, 'link': link})
        
        # BFS
        visited = {source_id: None}
        queue = [source_id]
        
        while queue:
            current = queue.pop(0)
            
            if current == target_id:
                break
            
            for neighbor in adjacency.get(current, []):
                neighbor_id = neighbor['node']
                if neighbor_id not in visited:
                    visited[neighbor_id] = (current, neighbor['link'])
                    queue.append(neighbor_id)
        
        # Reconstruct path
        if target_id not in visited:
            return []
        
        path = []
        current = target_id
        
        while current != source_id:
            prev, link = visited[current]
            
            # Find node in topology
            node = next((n for n in topology['nodes'] if n['id'] == current), None)
            
            path.append({
                'node': node,
                'link': link
            })
            
            current = prev
        
        # Add source node
        source_node = next((n for n in topology['nodes'] if n['id'] == source_id), None)
        path.append({'node': source_node, 'link': None})
        
        # Reverse to get correct order
        path.reverse()
        
        return path
