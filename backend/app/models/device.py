"""
Device models for TF-Rack and Dante devices.
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, JSON, Enum as SQLEnum, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class DeviceType(str, Enum):
    TF_RACK = "tf_rack"
    TIO_1608_D = "tio_1608_d"
    DANTE_GENERIC = "dante_generic"


class Device(Base):
    """Network audio device."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_type = Column(SQLEnum(DeviceType), nullable=False)
    name = Column(String(64), nullable=False)

    # Network info
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    mac_address = Column(String(17), nullable=True)

    # Dante info
    dante_name = Column(String(64), nullable=True)
    dante_model = Column(String(64), nullable=True)
    dante_manufacturer = Column(String(64), nullable=True)

    # Connection status
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, nullable=True)

    # Device capabilities
    input_count = Column(Integer, default=0)
    output_count = Column(Integer, default=0)
    sample_rate = Column(Integer, default=48000)

    # Additional properties
    properties = Column(JSON, default=dict)

    # Discovery timestamp
    discovered_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Device {self.device_type.value}: {self.name} ({self.ip_address})>"
