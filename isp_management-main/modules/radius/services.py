from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, not_
from fastapi import HTTPException
import json
import secrets
import hashlib
import hmac
import time
import socket
import struct
import logging
from cryptography.fernet import Fernet

from backend_core.models import (
    RadiusProfile, RadiusAccounting, User, 
    NasDevice, NasVendorAttribute, 
    RadiusBandwidthPolicy, RadiusProfileAttribute,
    RadiusCoALog
)
from .schemas import (
    RadiusProfileCreate, RadiusProfileUpdate,
    RadiusAuthRequest, RadiusAuthResponse,
    RadiusAccountingStart, RadiusAccountingUpdate, RadiusAccountingStop,
    NasDeviceCreate, NasDeviceUpdate,
    NasVendorAttributeCreate, NasVendorAttributeUpdate,
    RadiusBandwidthPolicyCreate, RadiusBandwidthPolicyUpdate,
    RadiusProfileAttributeCreate, RadiusProfileAttributeUpdate,
    RadiusCoARequest, RadiusCoAResponse,
    SessionStatistics, UserSessionStatistics, NasSessionStatistics,
    BandwidthUsageReport
)
from backend_core.auth_service import get_password_hash, verify_password
from backend_core.config import settings

# Configure logging
logger = logging.getLogger("radius_service")

class RadiusService:
    def __init__(self, db: Session):
        self.db = db
        # Initialize encryption key for RADIUS secrets
        # In production, this should be stored securely and not hardcoded
        self.secret_key = settings.RADIUS_SECRET_KEY.encode() if hasattr(settings, 'RADIUS_SECRET_KEY') else b'your-secret-key-for-radius-encryption'
        self.cipher_suite = Fernet(self.secret_key)

    def encrypt_secret(self, secret: str) -> str:
        """Encrypts a RADIUS shared secret."""
        return self.cipher_suite.encrypt(secret.encode()).decode()

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypts a RADIUS shared secret."""
        return self.cipher_suite.decrypt(encrypted_secret.encode()).decode()

    def create_radius_profile(self, profile_data: RadiusProfileCreate) -> RadiusProfile:
        """Creates a new RADIUS profile for a user."""
        # Check if user exists
        user = self.db.query(User).filter(User.id == profile_data.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if profile already exists
        existing_profile = (
            self.db.query(RadiusProfile)
            .filter(RadiusProfile.user_id == profile_data.user_id)
            .first()
        )
        if existing_profile:
            raise HTTPException(status_code=400, detail="RADIUS profile already exists for this user")
        
        # Create new profile
        hashed_password = get_password_hash(profile_data.password)
        profile = RadiusProfile(
            user_id=profile_data.user_id,
            username=profile_data.username,
            password_hash=hashed_password,
            speed_limit=profile_data.speed_limit,
            data_cap=profile_data.data_cap,
            service_type=profile_data.service_type,
            simultaneous_use=profile_data.simultaneous_use,
            acct_interim_interval=profile_data.acct_interim_interval,
            session_timeout=profile_data.session_timeout,
            idle_timeout=profile_data.idle_timeout,
            bandwidth_policy_id=profile_data.bandwidth_policy_id
        )
        
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_radius_profile(self, profile_id: int, profile_data: RadiusProfileUpdate) -> RadiusProfile:
        """Updates an existing RADIUS profile."""
        profile = self.db.query(RadiusProfile).filter(RadiusProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="RADIUS profile not found")
        
        # Update fields if provided
        if profile_data.speed_limit is not None:
            profile.speed_limit = profile_data.speed_limit
        if profile_data.data_cap is not None:
            profile.data_cap = profile_data.data_cap
        if profile_data.service_type is not None:
            profile.service_type = profile_data.service_type
        if profile_data.simultaneous_use is not None:
            profile.simultaneous_use = profile_data.simultaneous_use
        if profile_data.acct_interim_interval is not None:
            profile.acct_interim_interval = profile_data.acct_interim_interval
        if profile_data.session_timeout is not None:
            profile.session_timeout = profile_data.session_timeout
        if profile_data.idle_timeout is not None:
            profile.idle_timeout = profile_data.idle_timeout
        if profile_data.bandwidth_policy_id is not None:
            profile.bandwidth_policy_id = profile_data.bandwidth_policy_id
        if profile_data.password is not None:
            profile.password_hash = get_password_hash(profile_data.password)
        
        profile.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(profile)
        
        # If profile was updated and there are active sessions, send CoA to apply changes
        active_sessions = (
            self.db.query(RadiusAccounting)
            .filter(
                RadiusAccounting.profile_id == profile_id,
                RadiusAccounting.stop_time == None
            )
            .all()
        )
        
        for session in active_sessions:
            if session.nas_id:
                try:
                    self.send_coa_request(
                        RadiusCoARequest(
                            profile_id=profile_id,
                            nas_id=session.nas_id,
                            session_id=session.session_id,
                            coa_type="update",
                            attributes=self._get_profile_attributes(profile)
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to send CoA for profile {profile_id}, session {session.session_id}: {str(e)}")
        
        return profile

    def get_radius_profile(self, profile_id: int) -> Optional[RadiusProfile]:
        """Retrieves a RADIUS profile by ID."""
        return self.db.query(RadiusProfile).filter(RadiusProfile.id == profile_id).first()

    def get_profile_by_username(self, username: str) -> Optional[RadiusProfile]:
        """Retrieves a RADIUS profile by username."""
        return self.db.query(RadiusProfile).filter(RadiusProfile.username == username).first()

    def _get_profile_attributes(self, profile: RadiusProfile) -> Dict[str, Any]:
        """Gets all attributes for a RADIUS profile, including from bandwidth policy."""
        attributes = {
            "Service-Type": profile.service_type,
            "Session-Timeout": profile.session_timeout if profile.session_timeout > 0 else None,
            "Idle-Timeout": profile.idle_timeout if profile.idle_timeout > 0 else None,
            "Acct-Interim-Interval": profile.acct_interim_interval
        }
        
        # Add bandwidth policy attributes if present
        if profile.bandwidth_policy:
            policy = profile.bandwidth_policy
            
            # Standard attributes
            if policy.download_rate > 0:
                attributes["WISPr-Bandwidth-Max-Down"] = policy.download_rate * 1000  # Convert to bps
            if policy.upload_rate > 0:
                attributes["WISPr-Bandwidth-Max-Up"] = policy.upload_rate * 1000  # Convert to bps
                
            # Vendor-specific attributes (Mikrotik example)
            if policy.download_rate > 0 and policy.upload_rate > 0:
                attributes["Mikrotik-Rate-Limit"] = f"{policy.upload_rate}k/{policy.download_rate}k"
                
            # Burst attributes if present
            if policy.burst_download_rate and policy.burst_upload_rate and policy.burst_threshold and policy.burst_time:
                attributes["Mikrotik-Rate-Limit"] = (
                    f"{policy.upload_rate}k/{policy.download_rate}k "
                    f"{policy.burst_upload_rate}k/{policy.burst_download_rate}k "
                    f"{policy.burst_threshold}/{policy.burst_time}s"
                )
        
        # Add custom profile attributes
        custom_attributes = self.db.query(RadiusProfileAttribute).filter(
            RadiusProfileAttribute.profile_id == profile.id
        ).all()
        
        for attr in custom_attributes:
            if attr.vendor_id and attr.vendor_type:
                # Format as vendor-specific
                vendor_key = f"Vendor-{attr.vendor_id}-{attr.vendor_type}"
                attributes[vendor_key] = attr.attribute_value
            else:
                # Standard attribute
                attributes[attr.attribute_name] = attr.attribute_value
        
        return attributes

    def authenticate_user(self, auth_request: RadiusAuthRequest) -> RadiusAuthResponse:
        """Authenticates a RADIUS user."""
        profile = self.get_profile_by_username(auth_request.username)
        
        # Check if profile exists
        if not profile:
            return RadiusAuthResponse(
                status="reject",
                message="User not found"
            )
        
        # Check if user is active
        if not profile.user.is_active:
            return RadiusAuthResponse(
                status="reject",
                message="User is suspended"
            )
        
        # Verify password
        if not verify_password(auth_request.password, profile.password_hash):
            return RadiusAuthResponse(
                status="reject",
                message="Invalid password"
            )
        
        # Check for simultaneous use limit
        if profile.simultaneous_use > 0:
            active_sessions = (
                self.db.query(RadiusAccounting)
                .filter(
                    RadiusAccounting.profile_id == profile.id,
                    RadiusAccounting.stop_time == None
                )
                .count()
            )
            
            if active_sessions >= profile.simultaneous_use:
                return RadiusAuthResponse(
                    status="reject",
                    message=f"Maximum number of simultaneous sessions ({profile.simultaneous_use}) reached"
                )
        
        # Authentication successful, return attributes
        attributes = self._get_profile_attributes(profile)
        
        # Log the successful authentication
        logger.info(f"User {auth_request.username} authenticated from NAS {auth_request.nas_ip_address}")
        
        return RadiusAuthResponse(
            status="accept",
            message="Authentication successful",
            attributes=attributes
        )

    def start_accounting_session(self, accounting_data: RadiusAccountingStart) -> RadiusAccounting:
        """Starts a RADIUS accounting session."""
        # Check if session already exists
        existing_session = (
            self.db.query(RadiusAccounting)
            .filter(RadiusAccounting.session_id == accounting_data.session_id)
            .first()
        )
        if existing_session:
            raise HTTPException(status_code=400, detail="Session already exists")
        
        # Create new accounting record
        accounting = RadiusAccounting(
            session_id=accounting_data.session_id,
            profile_id=accounting_data.profile_id,
            nas_ip_address=accounting_data.nas_ip_address,
            bytes_in=accounting_data.bytes_in,
            bytes_out=accounting_data.bytes_out,
            session_time=accounting_data.session_time,
            start_time=datetime.utcnow(),
            nas_id=accounting_data.nas_id,
            framed_ip_address=accounting_data.framed_ip_address,
            framed_protocol=accounting_data.framed_protocol,
            calling_station_id=accounting_data.calling_station_id,
            called_station_id=accounting_data.called_station_id,
            acct_authentic=accounting_data.acct_authentic,
            acct_input_octets=accounting_data.acct_input_octets,
            acct_output_octets=accounting_data.acct_output_octets,
            acct_input_packets=accounting_data.acct_input_packets,
            acct_output_packets=accounting_data.acct_output_packets,
            acct_session_id=accounting_data.acct_session_id,
            acct_multi_session_id=accounting_data.acct_multi_session_id,
            acct_link_count=accounting_data.acct_link_count
        )
        
        self.db.add(accounting)
        self.db.commit()
        self.db.refresh(accounting)
        
        # Log the session start
        logger.info(f"Started accounting session {accounting_data.session_id} for profile {accounting_data.profile_id}")
        
        return accounting

    def update_accounting_session(self, accounting_data: RadiusAccountingUpdate) -> RadiusAccounting:
        """Updates a RADIUS accounting session (interim update)."""
        # Find the session
        session = (
            self.db.query(RadiusAccounting)
            .filter(RadiusAccounting.session_id == accounting_data.session_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update session data
        session.bytes_in = accounting_data.bytes_in
        session.bytes_out = accounting_data.bytes_out
        session.session_time = accounting_data.session_time
        session.acct_input_octets = accounting_data.acct_input_octets
        session.acct_output_octets = accounting_data.acct_output_octets
        session.acct_input_packets = accounting_data.acct_input_packets
        session.acct_output_packets = accounting_data.acct_output_packets
        session.acct_interim_updates += 1
        session.last_interim_update = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(session)
        
        # Check for data cap exceeded
        profile = self.db.query(RadiusProfile).filter(RadiusProfile.id == session.profile_id).first()
        if profile and profile.data_cap > 0:
            total_usage = session.bytes_in + session.bytes_out
            if total_usage > profile.data_cap * 1024 * 1024:  # Convert MB to bytes
                # Data cap exceeded, disconnect user
                try:
                    self.send_coa_request(
                        RadiusCoARequest(
                            profile_id=profile.id,
                            nas_id=session.nas_id if session.nas_id else 0,
                            session_id=session.session_id,
                            coa_type="disconnect",
                            attributes={"Terminate-Cause": "Data-Cap-Exceeded"}
                        )
                    )
                    logger.info(f"Data cap exceeded for profile {profile.id}, sent disconnect request")
                except Exception as e:
                    logger.error(f"Failed to send disconnect for data cap: {str(e)}")
        
        return session

    def stop_accounting_session(self, accounting_data: RadiusAccountingStop) -> RadiusAccounting:
        """Stops a RADIUS accounting session."""
        # Find the session
        session = (
            self.db.query(RadiusAccounting)
            .filter(RadiusAccounting.session_id == accounting_data.session_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update session data
        session.bytes_in = accounting_data.bytes_in
        session.bytes_out = accounting_data.bytes_out
        session.session_time = accounting_data.session_time
        session.stop_time = datetime.utcnow()
        session.terminate_cause = accounting_data.terminate_cause
        session.acct_input_octets = accounting_data.acct_input_octets
        session.acct_output_octets = accounting_data.acct_output_octets
        session.acct_input_packets = accounting_data.acct_input_packets
        session.acct_output_packets = accounting_data.acct_output_packets
        
        self.db.commit()
        self.db.refresh(session)
        
        # Log the session stop
        logger.info(
            f"Stopped accounting session {accounting_data.session_id} for profile {session.profile_id}. "
            f"Duration: {session.session_time}s, Download: {session.bytes_in} bytes, Upload: {session.bytes_out} bytes"
        )
        
        # Here you might want to integrate with the Billing module
        # to update usage-based billing if applicable
        
        return session

    def get_active_sessions(self, skip: int = 0, limit: int = 100) -> List[RadiusAccounting]:
        """Gets all active RADIUS sessions."""
        return (
            self.db.query(RadiusAccounting)
            .filter(RadiusAccounting.stop_time == None)
            .order_by(RadiusAccounting.start_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_user_sessions(self, user_id: int, skip: int = 0, limit: int = 100) -> List[RadiusAccounting]:
        """Gets all sessions for a specific user."""
        return (
            self.db.query(RadiusAccounting)
            .join(RadiusProfile, RadiusAccounting.profile_id == RadiusProfile.id)
            .filter(RadiusProfile.user_id == user_id)
            .order_by(RadiusAccounting.start_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_nas_sessions(self, nas_id: int, skip: int = 0, limit: int = 100) -> List[RadiusAccounting]:
        """Gets all sessions for a specific NAS device."""
        return (
            self.db.query(RadiusAccounting)
            .filter(RadiusAccounting.nas_id == nas_id)
            .order_by(RadiusAccounting.start_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_session_statistics(self) -> SessionStatistics:
        """Gets overall session statistics."""
        total_sessions = self.db.query(func.count(RadiusAccounting.id)).scalar()
        active_sessions = self.db.query(func.count(RadiusAccounting.id)).filter(RadiusAccounting.stop_time == None).scalar()
        
        # Calculate total bytes
        bytes_stats = (
            self.db.query(
                func.sum(RadiusAccounting.bytes_in).label("total_bytes_in"),
                func.sum(RadiusAccounting.bytes_out).label("total_bytes_out")
            )
            .first()
        )
        
        total_bytes_in = bytes_stats.total_bytes_in or 0
        total_bytes_out = bytes_stats.total_bytes_out or 0
        
        # Calculate average session time for completed sessions
        avg_session_time = (
            self.db.query(func.avg(RadiusAccounting.session_time))
            .filter(RadiusAccounting.stop_time != None)
            .scalar() or 0
        )
        
        return SessionStatistics(
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_bytes_in=total_bytes_in,
            total_bytes_out=total_bytes_out,
            average_session_time=float(avg_session_time)
        )

    def get_user_session_statistics(self, user_id: int) -> UserSessionStatistics:
        """Gets session statistics for a specific user."""
        # Get user information
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get profile ID
        profile = self.db.query(RadiusProfile).filter(RadiusProfile.user_id == user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="RADIUS profile not found for user")
        
        # Calculate statistics
        total_sessions = self.db.query(func.count(RadiusAccounting.id)).filter(RadiusAccounting.profile_id == profile.id).scalar()
        active_sessions = self.db.query(func.count(RadiusAccounting.id)).filter(
            RadiusAccounting.profile_id == profile.id,
            RadiusAccounting.stop_time == None
        ).scalar()
        
        # Calculate total bytes
        bytes_stats = (
            self.db.query(
                func.sum(RadiusAccounting.bytes_in).label("total_bytes_in"),
                func.sum(RadiusAccounting.bytes_out).label("total_bytes_out")
            )
            .filter(RadiusAccounting.profile_id == profile.id)
            .first()
        )
        
        total_bytes_in = bytes_stats.total_bytes_in or 0
        total_bytes_out = bytes_stats.total_bytes_out or 0
        
        # Calculate average session time for completed sessions
        avg_session_time = (
            self.db.query(func.avg(RadiusAccounting.session_time))
            .filter(
                RadiusAccounting.profile_id == profile.id,
                RadiusAccounting.stop_time != None
            )
            .scalar() or 0
        )
        
        return UserSessionStatistics(
            user_id=user_id,
            username=user.username,
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_bytes_in=total_bytes_in,
            total_bytes_out=total_bytes_out,
            average_session_time=float(avg_session_time)
        )

    def get_nas_session_statistics(self, nas_id: int) -> NasSessionStatistics:
        """Gets session statistics for a specific NAS device."""
        # Get NAS information
        nas = self.db.query(NasDevice).filter(NasDevice.id == nas_id).first()
        if not nas:
            raise HTTPException(status_code=404, detail="NAS device not found")
        
        # Calculate statistics
        total_sessions = self.db.query(func.count(RadiusAccounting.id)).filter(RadiusAccounting.nas_id == nas_id).scalar()
        active_sessions = self.db.query(func.count(RadiusAccounting.id)).filter(
            RadiusAccounting.nas_id == nas_id,
            RadiusAccounting.stop_time == None
        ).scalar()
        
        # Calculate total bytes
        bytes_stats = (
            self.db.query(
                func.sum(RadiusAccounting.bytes_in).label("total_bytes_in"),
                func.sum(RadiusAccounting.bytes_out).label("total_bytes_out")
            )
            .filter(RadiusAccounting.nas_id == nas_id)
            .first()
        )
        
        total_bytes_in = bytes_stats.total_bytes_in or 0
        total_bytes_out = bytes_stats.total_bytes_out or 0
        
        # Calculate average session time for completed sessions
        avg_session_time = (
            self.db.query(func.avg(RadiusAccounting.session_time))
            .filter(
                RadiusAccounting.nas_id == nas_id,
                RadiusAccounting.stop_time != None
            )
            .scalar() or 0
        )
        
        return NasSessionStatistics(
            nas_id=nas_id,
            nas_name=nas.name,
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_bytes_in=total_bytes_in,
            total_bytes_out=total_bytes_out,
            average_session_time=float(avg_session_time)
        )

    def generate_bandwidth_usage_report(self, user_id: int, start_date: datetime, end_date: datetime) -> BandwidthUsageReport:
        """Generates a bandwidth usage report for a specific user within a date range."""
        # Get user information
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get profile ID
        profile = self.db.query(RadiusProfile).filter(RadiusProfile.user_id == user_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="RADIUS profile not found for user")
        
        # Get sessions within date range
        sessions = (
            self.db.query(RadiusAccounting)
            .filter(
                RadiusAccounting.profile_id == profile.id,
                RadiusAccounting.start_time >= start_date,
                or_(
                    RadiusAccounting.stop_time <= end_date,
                    RadiusAccounting.stop_time == None
                )
            )
            .all()
        )
        
        # Calculate totals
        download_bytes = sum(session.bytes_in for session in sessions)
        upload_bytes = sum(session.bytes_out for session in sessions)
        total_bytes = download_bytes + upload_bytes
        
        # Calculate rates
        total_time_seconds = sum(
            (session.stop_time or datetime.utcnow()) - session.start_time
            for session in sessions
        ).total_seconds()
        
        # Avoid division by zero
        if total_time_seconds > 0:
            avg_download_rate = (download_bytes * 8) / total_time_seconds / 1000  # kbps
            avg_upload_rate = (upload_bytes * 8) / total_time_seconds / 1000      # kbps
            
            # Find peak rates (simplified - in reality would need more detailed data)
            peak_download_rate = max((session.bytes_in * 8) / max(session.session_time, 1) / 1000 for session in sessions) if sessions else 0
            peak_upload_rate = max((session.bytes_out * 8) / max(session.session_time, 1) / 1000 for session in sessions) if sessions else 0
        else:
            avg_download_rate = 0
            avg_upload_rate = 0
            peak_download_rate = 0
            peak_upload_rate = 0
        
        return BandwidthUsageReport(
            user_id=user_id,
            username=user.username,
            total_bytes=total_bytes,
            download_bytes=download_bytes,
            upload_bytes=upload_bytes,
            period_start=start_date,
            period_end=end_date,
            average_download_rate=avg_download_rate,
            average_upload_rate=avg_upload_rate,
            peak_download_rate=peak_download_rate,
            peak_upload_rate=peak_upload_rate
        )

    # NAS Device Management
    def create_nas_device(self, device_data: NasDeviceCreate) -> NasDevice:
        """Creates a new NAS device."""
        # Check if device with same IP already exists
        existing_device = (
            self.db.query(NasDevice)
            .filter(NasDevice.ip_address == device_data.ip_address)
            .first()
        )
        if existing_device:
            raise HTTPException(status_code=400, detail="NAS device with this IP address already exists")
        
        # Encrypt the shared secret
        encrypted_secret = self.encrypt_secret(device_data.secret)
        
        # Create new device
        device = NasDevice(
            name=device_data.name,
            ip_address=device_data.ip_address,
            secret=encrypted_secret,
            vendor=device_data.vendor,
            model=device_data.model,
            location=device_data.location,
            type=device_data.type,
            description=device_data.description,
            ports=device_data.ports,
            community=device_data.community,
            version=device_data.version,
            config_json=device_data.config_json,
            is_active=device_data.is_active,
            last_seen=datetime.utcnow()
        )
        
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        
        logger.info(f"Created new NAS device: {device.name} ({device.ip_address})")
        
        return device

    def update_nas_device(self, device_id: int, device_data: NasDeviceUpdate) -> NasDevice:
        """Updates an existing NAS device."""
        device = self.db.query(NasDevice).filter(NasDevice.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="NAS device not found")
        
        # Update fields if provided
        if device_data.name is not None:
            device.name = device_data.name
        if device_data.vendor is not None:
            device.vendor = device_data.vendor
        if device_data.model is not None:
            device.model = device_data.model
        if device_data.location is not None:
            device.location = device_data.location
        if device_data.type is not None:
            device.type = device_data.type
        if device_data.description is not None:
            device.description = device_data.description
        if device_data.ports is not None:
            device.ports = device_data.ports
        if device_data.community is not None:
            device.community = device_data.community
        if device_data.version is not None:
            device.version = device_data.version
        if device_data.config_json is not None:
            device.config_json = device_data.config_json
        if device_data.is_active is not None:
            device.is_active = device_data.is_active
        if device_data.secret is not None:
            device.secret = self.encrypt_secret(device_data.secret)
        
        device.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(device)
        
        logger.info(f"Updated NAS device: {device.name} (ID: {device.id})")
        
        return device

    def get_nas_device(self, device_id: int) -> Optional[NasDevice]:
        """Retrieves a NAS device by ID."""
        return self.db.query(NasDevice).filter(NasDevice.id == device_id).first()

    def get_nas_device_by_ip(self, ip_address: str) -> Optional[NasDevice]:
        """Retrieves a NAS device by IP address."""
        return self.db.query(NasDevice).filter(NasDevice.ip_address == ip_address).first()

    def list_nas_devices(self, skip: int = 0, limit: int = 100, vendor: Optional[str] = None) -> List[NasDevice]:
        """Lists all NAS devices, optionally filtered by vendor."""
        query = self.db.query(NasDevice)
        
        if vendor:
            query = query.filter(NasDevice.vendor == vendor)
        
        return query.order_by(NasDevice.name).offset(skip).limit(limit).all()

    def delete_nas_device(self, device_id: int) -> bool:
        """Deletes a NAS device."""
        device = self.db.query(NasDevice).filter(NasDevice.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="NAS device not found")
        
        # Check if there are active sessions using this NAS
        active_sessions = (
            self.db.query(func.count(RadiusAccounting.id))
            .filter(
                RadiusAccounting.nas_id == device_id,
                RadiusAccounting.stop_time == None
            )
            .scalar()
        )
        
        if active_sessions > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete NAS device with {active_sessions} active sessions"
            )
        
        # Delete vendor attributes first
        self.db.query(NasVendorAttribute).filter(NasVendorAttribute.nas_id == device_id).delete()
        
        # Delete the device
        self.db.delete(device)
        self.db.commit()
        
        logger.info(f"Deleted NAS device: {device.name} (ID: {device.id})")
        
        return True

    # NAS Vendor Attributes Management
    def create_nas_vendor_attribute(self, attr_data: NasVendorAttributeCreate) -> NasVendorAttribute:
        """Creates a new vendor-specific attribute for a NAS device."""
        # Check if NAS exists
        nas = self.db.query(NasDevice).filter(NasDevice.id == attr_data.nas_id).first()
        if not nas:
            raise HTTPException(status_code=404, detail="NAS device not found")
        
        # Create new attribute
        attribute = NasVendorAttribute(
            nas_id=attr_data.nas_id,
            attribute_name=attr_data.attribute_name,
            attribute_value=attr_data.attribute_value,
            vendor_type=attr_data.vendor_type,
            vendor_id=attr_data.vendor_id,
            description=attr_data.description
        )
        
        self.db.add(attribute)
        self.db.commit()
        self.db.refresh(attribute)
        
        return attribute

    def update_nas_vendor_attribute(self, attr_id: int, attr_data: NasVendorAttributeUpdate) -> NasVendorAttribute:
        """Updates an existing vendor-specific attribute."""
        attribute = self.db.query(NasVendorAttribute).filter(NasVendorAttribute.id == attr_id).first()
        if not attribute:
            raise HTTPException(status_code=404, detail="Vendor attribute not found")
        
        # Update fields if provided
        if attr_data.attribute_name is not None:
            attribute.attribute_name = attr_data.attribute_name
        if attr_data.attribute_value is not None:
            attribute.attribute_value = attr_data.attribute_value
        if attr_data.vendor_type is not None:
            attribute.vendor_type = attr_data.vendor_type
        if attr_data.vendor_id is not None:
            attribute.vendor_id = attr_data.vendor_id
        if attr_data.description is not None:
            attribute.description = attr_data.description
        
        attribute.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(attribute)
        
        return attribute

    def get_nas_vendor_attributes(self, nas_id: int) -> List[NasVendorAttribute]:
        """Gets all vendor-specific attributes for a NAS device."""
        return self.db.query(NasVendorAttribute).filter(NasVendorAttribute.nas_id == nas_id).all()

    def delete_nas_vendor_attribute(self, attr_id: int) -> bool:
        """Deletes a vendor-specific attribute."""
        attribute = self.db.query(NasVendorAttribute).filter(NasVendorAttribute.id == attr_id).first()
        if not attribute:
            raise HTTPException(status_code=404, detail="Vendor attribute not found")
        
        self.db.delete(attribute)
        self.db.commit()
        
        return True

    # Bandwidth Policy Management
    def create_bandwidth_policy(self, policy_data: RadiusBandwidthPolicyCreate) -> RadiusBandwidthPolicy:
        """Creates a new bandwidth policy."""
        # Check if policy with same name already exists
        existing_policy = (
            self.db.query(RadiusBandwidthPolicy)
            .filter(RadiusBandwidthPolicy.name == policy_data.name)
            .first()
        )
        if existing_policy:
            raise HTTPException(status_code=400, detail="Bandwidth policy with this name already exists")
        
        # Create new policy
        policy = RadiusBandwidthPolicy(
            name=policy_data.name,
            description=policy_data.description,
            download_rate=policy_data.download_rate,
            upload_rate=policy_data.upload_rate,
            burst_download_rate=policy_data.burst_download_rate,
            burst_upload_rate=policy_data.burst_upload_rate,
            burst_threshold=policy_data.burst_threshold,
            burst_time=policy_data.burst_time,
            priority=policy_data.priority,
            time_based_limits=policy_data.time_based_limits,
            is_active=policy_data.is_active
        )
        
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        
        logger.info(f"Created new bandwidth policy: {policy.name} ({policy.download_rate}/{policy.upload_rate} kbps)")
        
        return policy

    def update_bandwidth_policy(self, policy_id: int, policy_data: RadiusBandwidthPolicyUpdate) -> RadiusBandwidthPolicy:
        """Updates an existing bandwidth policy."""
        policy = self.db.query(RadiusBandwidthPolicy).filter(RadiusBandwidthPolicy.id == policy_id).first()
        if not policy:
            raise HTTPException(status_code=404, detail="Bandwidth policy not found")
        
        # Check name uniqueness if changing name
        if policy_data.name is not None and policy_data.name != policy.name:
            existing_policy = (
                self.db.query(RadiusBandwidthPolicy)
                .filter(RadiusBandwidthPolicy.name == policy_data.name)
                .first()
            )
            if existing_policy:
                raise HTTPException(status_code=400, detail="Bandwidth policy with this name already exists")
        
        # Update fields if provided
        if policy_data.name is not None:
            policy.name = policy_data.name
        if policy_data.description is not None:
            policy.description = policy_data.description
        if policy_data.download_rate is not None:
            policy.download_rate = policy_data.download_rate
        if policy_data.upload_rate is not None:
            policy.upload_rate = policy_data.upload_rate
        if policy_data.burst_download_rate is not None:
            policy.burst_download_rate = policy_data.burst_download_rate
        if policy_data.burst_upload_rate is not None:
            policy.burst_upload_rate = policy_data.burst_upload_rate
        if policy_data.burst_threshold is not None:
            policy.burst_threshold = policy_data.burst_threshold
        if policy_data.burst_time is not None:
            policy.burst_time = policy_data.burst_time
        if policy_data.priority is not None:
            policy.priority = policy_data.priority
        if policy_data.time_based_limits is not None:
            policy.time_based_limits = policy_data.time_based_limits
        if policy_data.is_active is not None:
            policy.is_active = policy_data.is_active
        
        policy.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(policy)
        
        # If policy was updated, send CoA to all active sessions using this policy
        profiles_with_policy = self.db.query(RadiusProfile).filter(
            RadiusProfile.bandwidth_policy_id == policy_id
        ).all()
        
        for profile in profiles_with_policy:
            active_sessions = (
                self.db.query(RadiusAccounting)
                .filter(
                    RadiusAccounting.profile_id == profile.id,
                    RadiusAccounting.stop_time == None
                )
                .all()
            )
            
            for session in active_sessions:
                if session.nas_id:
                    try:
                        self.send_coa_request(
                            RadiusCoARequest(
                                profile_id=profile.id,
                                nas_id=session.nas_id,
                                session_id=session.session_id,
                                coa_type="update",
                                attributes=self._get_profile_attributes(profile)
                            )
                        )
                    except Exception as e:
                        logger.error(f"Failed to send CoA for policy update: {str(e)}")
        
        return policy

    def get_bandwidth_policy(self, policy_id: int) -> Optional[RadiusBandwidthPolicy]:
        """Retrieves a bandwidth policy by ID."""
        return self.db.query(RadiusBandwidthPolicy).filter(RadiusBandwidthPolicy.id == policy_id).first()

    def list_bandwidth_policies(self, skip: int = 0, limit: int = 100, active_only: bool = False) -> List[RadiusBandwidthPolicy]:
        """Lists all bandwidth policies."""
        query = self.db.query(RadiusBandwidthPolicy)
        
        if active_only:
            query = query.filter(RadiusBandwidthPolicy.is_active == True)
        
        return query.order_by(RadiusBandwidthPolicy.name).offset(skip).limit(limit).all()

    def delete_bandwidth_policy(self, policy_id: int) -> bool:
        """Deletes a bandwidth policy."""
        policy = self.db.query(RadiusBandwidthPolicy).filter(RadiusBandwidthPolicy.id == policy_id).first()
        if not policy:
            raise HTTPException(status_code=404, detail="Bandwidth policy not found")
        
        # Check if any profiles are using this policy
        profiles_using_policy = (
            self.db.query(func.count(RadiusProfile.id))
            .filter(RadiusProfile.bandwidth_policy_id == policy_id)
            .scalar()
        )
        
        if profiles_using_policy > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete policy that is being used by {profiles_using_policy} profiles"
            )
        
        self.db.delete(policy)
        self.db.commit()
        
        logger.info(f"Deleted bandwidth policy: {policy.name} (ID: {policy.id})")
        
        return True

    # Profile Attributes Management
    def create_profile_attribute(self, attr_data: RadiusProfileAttributeCreate) -> RadiusProfileAttribute:
        """Creates a new attribute for a RADIUS profile."""
        # Check if profile exists
        profile = self.db.query(RadiusProfile).filter(RadiusProfile.id == attr_data.profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="RADIUS profile not found")
        
        # Create new attribute
        attribute = RadiusProfileAttribute(
            profile_id=attr_data.profile_id,
            attribute_name=attr_data.attribute_name,
            attribute_value=attr_data.attribute_value,
            vendor_id=attr_data.vendor_id,
            vendor_type=attr_data.vendor_type
        )
        
        self.db.add(attribute)
        self.db.commit()
        self.db.refresh(attribute)
        
        # If there are active sessions for this profile, send CoA to apply the new attribute
        active_sessions = (
            self.db.query(RadiusAccounting)
            .filter(
                RadiusAccounting.profile_id == profile.id,
                RadiusAccounting.stop_time == None
            )
            .all()
        )
        
        for session in active_sessions:
            if session.nas_id:
                try:
                    self.send_coa_request(
                        RadiusCoARequest(
                            profile_id=profile.id,
                            nas_id=session.nas_id,
                            session_id=session.session_id,
                            coa_type="update",
                            attributes=self._get_profile_attributes(profile)
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to send CoA for new attribute: {str(e)}")
        
        return attribute

    def update_profile_attribute(self, attr_id: int, attr_data: RadiusProfileAttributeUpdate) -> RadiusProfileAttribute:
        """Updates an existing profile attribute."""
        attribute = self.db.query(RadiusProfileAttribute).filter(RadiusProfileAttribute.id == attr_id).first()
        if not attribute:
            raise HTTPException(status_code=404, detail="Profile attribute not found")
        
        # Update fields if provided
        if attr_data.attribute_name is not None:
            attribute.attribute_name = attr_data.attribute_name
        if attr_data.attribute_value is not None:
            attribute.attribute_value = attr_data.attribute_value
        if attr_data.vendor_id is not None:
            attribute.vendor_id = attr_data.vendor_id
        if attr_data.vendor_type is not None:
            attribute.vendor_type = attr_data.vendor_type
        
        attribute.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(attribute)
        
        # If attribute was updated, send CoA to all active sessions for this profile
        profile = self.db.query(RadiusProfile).filter(RadiusProfile.id == attribute.profile_id).first()
        if profile:
            active_sessions = (
                self.db.query(RadiusAccounting)
                .filter(
                    RadiusAccounting.profile_id == profile.id,
                    RadiusAccounting.stop_time == None
                )
                .all()
            )
            
            for session in active_sessions:
                if session.nas_id:
                    try:
                        self.send_coa_request(
                            RadiusCoARequest(
                                profile_id=profile.id,
                                nas_id=session.nas_id,
                                session_id=session.session_id,
                                coa_type="update",
                                attributes=self._get_profile_attributes(profile)
                            )
                        )
                    except Exception as e:
                        logger.error(f"Failed to send CoA for attribute update: {str(e)}")
        
        return attribute

    def get_profile_attributes(self, profile_id: int) -> List[RadiusProfileAttribute]:
        """Gets all attributes for a RADIUS profile."""
        return self.db.query(RadiusProfileAttribute).filter(RadiusProfileAttribute.profile_id == profile_id).all()

    def delete_profile_attribute(self, attr_id: int) -> bool:
        """Deletes a profile attribute."""
        attribute = self.db.query(RadiusProfileAttribute).filter(RadiusProfileAttribute.id == attr_id).first()
        if not attribute:
            raise HTTPException(status_code=404, detail="Profile attribute not found")
        
        profile_id = attribute.profile_id
        
        self.db.delete(attribute)
        self.db.commit()
        
        # If attribute was deleted, send CoA to all active sessions for this profile
        profile = self.db.query(RadiusProfile).filter(RadiusProfile.id == profile_id).first()
        if profile:
            active_sessions = (
                self.db.query(RadiusAccounting)
                .filter(
                    RadiusAccounting.profile_id == profile.id,
                    RadiusAccounting.stop_time == None
                )
                .all()
            )
            
            for session in active_sessions:
                if session.nas_id:
                    try:
                        self.send_coa_request(
                            RadiusCoARequest(
                                profile_id=profile.id,
                                nas_id=session.nas_id,
                                session_id=session.session_id,
                                coa_type="update",
                                attributes=self._get_profile_attributes(profile)
                            )
                        )
                    except Exception as e:
                        logger.error(f"Failed to send CoA after attribute deletion: {str(e)}")
        
        return True

    # CoA (Change of Authorization) functionality
    def send_coa_request(self, coa_request: RadiusCoARequest) -> RadiusCoAResponse:
        """Sends a CoA request to a NAS device."""
        # Get NAS device
        nas = self.db.query(NasDevice).filter(NasDevice.id == coa_request.nas_id).first()
        if not nas:
            raise HTTPException(status_code=404, detail="NAS device not found")
        
        # Get profile
        profile = self.db.query(RadiusProfile).filter(RadiusProfile.id == coa_request.profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="RADIUS profile not found")
        
        # Decrypt the shared secret
        secret = self.decrypt_secret(nas.secret)
        
        # Log the CoA request
        coa_log = RadiusCoALog(
            profile_id=coa_request.profile_id,
            nas_id=coa_request.nas_id,
            session_id=coa_request.session_id,
            coa_type=coa_request.coa_type,
            attributes_changed=coa_request.attributes,
            result="pending"
        )
        
        self.db.add(coa_log)
        self.db.commit()
        self.db.refresh(coa_log)
        
        try:
            # This would be the actual CoA packet construction and sending
            # For demonstration, we'll simulate a successful CoA
            
            # In a real implementation, this would use a RADIUS library to send
            # the CoA packet to the NAS device
            
            # For example, using pyrad:
            # from pyrad.client import Client
            # from pyrad.dictionary import Dictionary
            # import pyrad.packet
            
            # srv = Client(server=nas.ip_address, secret=secret.encode(),
            #              dict=Dictionary("dictionary"))
            
            # req = srv.CreateCoAPacket(code=pyrad.packet.CoARequest, **coa_request.attributes)
            # req["User-Name"] = profile.username
            # req["Session-Id"] = coa_request.session_id
            
            # reply = srv.SendPacket(req)
            # if reply.code == pyrad.packet.CoAACK:
            #     result = "success"
            # else:
            #     result = "failure"
            #     error_message = f"CoA rejected with code {reply.code}"
            
            # Simulate successful CoA
            time.sleep(0.5)  # Simulate network delay
            result = "success"
            error_message = None
            
            # Update the CoA log
            coa_log.result = result
            coa_log.error_message = error_message
            self.db.commit()
            
            logger.info(
                f"CoA {coa_request.coa_type} request sent to NAS {nas.name} "
                f"for profile {profile.username}, result: {result}"
            )
            
            return RadiusCoAResponse(
                id=coa_log.id,
                profile_id=coa_request.profile_id,
                nas_id=coa_request.nas_id,
                session_id=coa_request.session_id,
                coa_type=coa_request.coa_type,
                attributes_changed=coa_request.attributes,
                result=result,
                error_message=error_message,
                created_at=coa_log.created_at
            )
            
        except Exception as e:
            # Update the CoA log with the error
            coa_log.result = "failure"
            coa_log.error_message = str(e)
            self.db.commit()
            
            logger.error(
                f"Failed to send CoA {coa_request.coa_type} request to NAS {nas.name} "
                f"for profile {profile.username}: {str(e)}"
            )
            
            return RadiusCoAResponse(
                id=coa_log.id,
                profile_id=coa_request.profile_id,
                nas_id=coa_request.nas_id,
                session_id=coa_request.session_id,
                coa_type=coa_request.coa_type,
                attributes_changed=coa_request.attributes,
                result="failure",
                error_message=str(e),
                created_at=coa_log.created_at
            )

    def disconnect_user_session(self, session_id: str) -> bool:
        """Disconnects a specific user session."""
        session = (
            self.db.query(RadiusAccounting)
            .filter(
                RadiusAccounting.session_id == session_id,
                RadiusAccounting.stop_time == None
            )
            .first()
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Active session not found")
        
        if not session.nas_id:
            raise HTTPException(status_code=400, detail="Session does not have an associated NAS device")
        
        # Send disconnect request
        coa_response = self.send_coa_request(
            RadiusCoARequest(
                profile_id=session.profile_id,
                nas_id=session.nas_id,
                session_id=session.session_id,
                coa_type="disconnect",
                attributes={"Terminate-Cause": "Admin-Reset"}
            )
        )
        
        return coa_response.result == "success"

    def disconnect_user(self, username: str) -> Dict[str, Any]:
        """Disconnects all active sessions for a user."""
        profile = self.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        active_sessions = (
            self.db.query(RadiusAccounting)
            .filter(
                RadiusAccounting.profile_id == profile.id,
                RadiusAccounting.stop_time == None
            )
            .all()
        )
        
        results = {
            "total_sessions": len(active_sessions),
            "successful_disconnects": 0,
            "failed_disconnects": 0,
            "details": []
        }
        
        for session in active_sessions:
            if session.nas_id:
                try:
                    coa_response = self.send_coa_request(
                        RadiusCoARequest(
                            profile_id=profile.id,
                            nas_id=session.nas_id,
                            session_id=session.session_id,
                            coa_type="disconnect",
                            attributes={"Terminate-Cause": "Admin-Reset"}
                        )
                    )
                    
                    if coa_response.result == "success":
                        results["successful_disconnects"] += 1
                    else:
                        results["failed_disconnects"] += 1
                    
                    results["details"].append({
                        "session_id": session.session_id,
                        "nas_ip": session.nas_ip_address,
                        "result": coa_response.result,
                        "error": coa_response.error_message
                    })
                    
                except Exception as e:
                    results["failed_disconnects"] += 1
                    results["details"].append({
                        "session_id": session.session_id,
                        "nas_ip": session.nas_ip_address,
                        "result": "failure",
                        "error": str(e)
                    })
            else:
                results["failed_disconnects"] += 1
                results["details"].append({
                    "session_id": session.session_id,
                    "nas_ip": session.nas_ip_address,
                    "result": "failure",
                    "error": "No NAS device associated with session"
                })
        
        return results

    def get_coa_logs(self, profile_id: Optional[int] = None, nas_id: Optional[int] = None, 
                     skip: int = 0, limit: int = 100) -> List[RadiusCoALog]:
        """Gets CoA logs, optionally filtered by profile or NAS."""
        query = self.db.query(RadiusCoALog)
        
        if profile_id is not None:
            query = query.filter(RadiusCoALog.profile_id == profile_id)
        
        if nas_id is not None:
            query = query.filter(RadiusCoALog.nas_id == nas_id)
        
        return query.order_by(RadiusCoALog.created_at.desc()).offset(skip).limit(limit).all()
