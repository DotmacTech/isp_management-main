"""
IP Pool Management Service for the Network Management Module.
"""

import ipaddress
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import NotFoundException, ValidationError, ConflictError
from core.services import BaseService
from modules.network.models import IPPool, IPPoolType, IPAddress, IPAddressStatus

logger = logging.getLogger(__name__)


class IPPoolService(BaseService):
    """Service for managing IP address pools and allocations."""
    
    async def create_pool(
        self,
        session: AsyncSession,
        name: str,
        network: str,
        pool_type: IPPoolType,
        gateway: Optional[str] = None,
        dns_servers: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> IPPool:
        """
        Create a new IP address pool.
        
        Args:
            session: Database session
            name: Pool name
            network: Network CIDR notation (e.g., "192.168.1.0/24")
            pool_type: Type of IP pool
            gateway: Gateway IP address
            dns_servers: List of DNS server IP addresses
            description: Pool description
            
        Returns:
            The created IP pool
            
        Raises:
            ValidationError: If the pool data is invalid
            ConflictError: If a pool with the same network already exists
        """
        # Validate network CIDR
        try:
            net = ipaddress.ip_network(network, strict=False)
        except ValueError as e:
            raise ValidationError(f"Invalid network CIDR: {str(e)}")
        
        # Check if pool with the same network already exists
        existing = await session.execute(
            select(IPPool).where(IPPool.network == network)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"IP pool with network {network} already exists")
        
        # Validate gateway if provided
        if gateway:
            try:
                gw = ipaddress.ip_address(gateway)
                if gw not in net:
                    raise ValidationError(f"Gateway {gateway} is not in network {network}")
            except ValueError as e:
                raise ValidationError(f"Invalid gateway IP: {str(e)}")
        
        # Validate DNS servers if provided
        if dns_servers:
            for dns in dns_servers:
                try:
                    ipaddress.ip_address(dns)
                except ValueError as e:
                    raise ValidationError(f"Invalid DNS server IP {dns}: {str(e)}")
        
        # Create new IP pool
        ip_pool = IPPool(
            name=name,
            network=network,
            pool_type=pool_type,
            gateway=gateway,
            dns_servers=dns_servers,
            description=description,
            is_active=True
        )
        
        session.add(ip_pool)
        await session.flush()
        
        # Generate IP addresses for the pool
        await self._generate_ip_addresses(session, ip_pool)
        
        logger.info(f"Created new IP pool: {ip_pool.name} ({ip_pool.id}) with network {network}")
        return ip_pool
    
    async def _generate_ip_addresses(self, session: AsyncSession, ip_pool: IPPool) -> None:
        """
        Generate IP addresses for a pool.
        
        Args:
            session: Database session
            ip_pool: The IP pool
        """
        network = ipaddress.ip_network(ip_pool.network, strict=False)
        
        # Skip network and broadcast addresses for IPv4
        start_idx = 1 if network.version == 4 else 0
        end_idx = -1 if network.version == 4 and network.num_addresses > 1 else None
        
        # Skip gateway address if defined
        gateway_ip = None
        if ip_pool.gateway:
            gateway_ip = ipaddress.ip_address(ip_pool.gateway)
        
        # Create IP address objects
        ip_addresses = []
        for ip in list(network.hosts())[start_idx:end_idx]:
            # Skip gateway
            if gateway_ip and ip == gateway_ip:
                continue
                
            ip_addresses.append(
                IPAddress(
                    address=str(ip),
                    status=IPAddressStatus.AVAILABLE,
                    pool_id=ip_pool.id
                )
            )
        
        # Bulk insert IP addresses
        if ip_addresses:
            session.add_all(ip_addresses)
            await session.flush()
            
        logger.info(f"Generated {len(ip_addresses)} IP addresses for pool {ip_pool.id}")
    
    async def get_pool(self, session: AsyncSession, pool_id: int) -> IPPool:
        """
        Get an IP pool by ID.
        
        Args:
            session: Database session
            pool_id: IP pool ID
            
        Returns:
            The IP pool
            
        Raises:
            NotFoundException: If the IP pool is not found
        """
        pool = await session.get(IPPool, pool_id)
        if not pool:
            raise NotFoundException(f"IP pool with ID {pool_id} not found")
        return pool
    
    async def get_pools(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        pool_type: Optional[IPPoolType] = None,
        is_active: Optional[bool] = None
    ) -> List[IPPool]:
        """
        Get a list of IP pools with optional filtering.
        
        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            pool_type: Filter by pool type
            is_active: Filter by active status
            
        Returns:
            List of IP pools
        """
        query = select(IPPool)
        
        # Apply filters
        if pool_type:
            query = query.where(IPPool.pool_type == pool_type)
        if is_active is not None:
            query = query.where(IPPool.is_active == is_active)
            
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def allocate_ip(
        self,
        session: AsyncSession,
        pool_id: int,
        assigned_to_id: int,
        assigned_to_type: str,
        specific_ip: Optional[str] = None
    ) -> IPAddress:
        """
        Allocate an IP address from a pool.
        
        Args:
            session: Database session
            pool_id: IP pool ID
            assigned_to_id: ID of the entity the IP is assigned to
            assigned_to_type: Type of entity (e.g., "customer", "device")
            specific_ip: Specific IP address to allocate (if None, the next available IP is used)
            
        Returns:
            The allocated IP address
            
        Raises:
            NotFoundException: If the IP pool is not found
            ValidationError: If the specific IP is invalid or not in the pool
            ConflictError: If the specific IP is already allocated
        """
        # Get the IP pool
        pool = await self.get_pool(session, pool_id)
        
        if specific_ip:
            # Validate the specific IP
            try:
                ip = ipaddress.ip_address(specific_ip)
                network = ipaddress.ip_network(pool.network, strict=False)
                if ip not in network:
                    raise ValidationError(f"IP address {specific_ip} is not in network {pool.network}")
            except ValueError as e:
                raise ValidationError(f"Invalid IP address {specific_ip}: {str(e)}")
            
            # Check if the IP exists and is available
            query = select(IPAddress).where(
                and_(
                    IPAddress.address == specific_ip,
                    IPAddress.pool_id == pool_id
                )
            )
            result = await session.execute(query)
            ip_address = result.scalar_one_or_none()
            
            if not ip_address:
                raise NotFoundException(f"IP address {specific_ip} not found in pool {pool_id}")
            
            if ip_address.status != IPAddressStatus.AVAILABLE:
                raise ConflictError(f"IP address {specific_ip} is not available (status: {ip_address.status.value})")
        else:
            # Get the next available IP address
            query = select(IPAddress).where(
                and_(
                    IPAddress.pool_id == pool_id,
                    IPAddress.status == IPAddressStatus.AVAILABLE
                )
            ).limit(1)
            
            result = await session.execute(query)
            ip_address = result.scalar_one_or_none()
            
            if not ip_address:
                raise ConflictError(f"No available IP addresses in pool {pool_id}")
        
        # Update the IP address
        ip_address.status = IPAddressStatus.ALLOCATED
        ip_address.assigned_to_id = assigned_to_id
        ip_address.assigned_to_type = assigned_to_type
        ip_address.assigned_at = datetime.now()
        
        await session.flush()
        logger.info(f"Allocated IP {ip_address.address} to {assigned_to_type} {assigned_to_id}")
        
        return ip_address
    
    async def release_ip(
        self,
        session: AsyncSession,
        ip_address: str
    ) -> IPAddress:
        """
        Release an allocated IP address.
        
        Args:
            session: Database session
            ip_address: The IP address to release
            
        Returns:
            The released IP address
            
        Raises:
            NotFoundException: If the IP address is not found
        """
        # Find the IP address
        query = select(IPAddress).where(IPAddress.address == ip_address)
        result = await session.execute(query)
        ip = result.scalar_one_or_none()
        
        if not ip:
            raise NotFoundException(f"IP address {ip_address} not found")
        
        # Update the IP address
        ip.status = IPAddressStatus.AVAILABLE
        ip.assigned_to_id = None
        ip.assigned_to_type = None
        ip.assigned_at = None
        
        await session.flush()
        logger.info(f"Released IP {ip_address}")
        
        return ip
    
    async def get_pool_usage(self, session: AsyncSession, pool_id: int) -> Dict[str, Any]:
        """
        Get usage statistics for an IP pool.
        
        Args:
            session: Database session
            pool_id: IP pool ID
            
        Returns:
            Dictionary with usage statistics
            
        Raises:
            NotFoundException: If the IP pool is not found
        """
        # Get the IP pool
        pool = await self.get_pool(session, pool_id)
        
        # Count IPs by status
        query = select(
            IPAddress.status,
            func.count(IPAddress.id).label("count")
        ).where(
            IPAddress.pool_id == pool_id
        ).group_by(
            IPAddress.status
        )
        
        result = await session.execute(query)
        status_counts = {status.value: count for status, count in result.all()}
        
        # Calculate total IPs
        network = ipaddress.ip_network(pool.network, strict=False)
        total_ips = network.num_addresses
        if network.version == 4 and total_ips > 2:
            # Subtract network and broadcast addresses for IPv4
            total_ips -= 2
        
        # Calculate usage percentages
        allocated = status_counts.get(IPAddressStatus.ALLOCATED.value, 0)
        reserved = status_counts.get(IPAddressStatus.RESERVED.value, 0)
        available = status_counts.get(IPAddressStatus.AVAILABLE.value, 0)
        quarantined = status_counts.get(IPAddressStatus.QUARANTINED.value, 0)
        
        usage_percent = (allocated + reserved) / total_ips * 100 if total_ips > 0 else 0
        
        return {
            "pool_id": pool.id,
            "name": pool.name,
            "network": pool.network,
            "total_ips": total_ips,
            "allocated": allocated,
            "reserved": reserved,
            "available": available,
            "quarantined": quarantined,
            "usage_percent": round(usage_percent, 2)
        }
