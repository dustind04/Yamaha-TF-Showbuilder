"""
Patch/routing models for audio connections.
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class PatchType(str, Enum):
    ANALOG_TO_CHANNEL = "analog_to_channel"
    DANTE_TO_CHANNEL = "dante_to_channel"
    CHANNEL_TO_DANTE = "channel_to_dante"
    CHANNEL_TO_AUX = "channel_to_aux"
    AUX_TO_DANTE = "aux_to_dante"
    DIRECT_OUT = "direct_out"


class Patch(Base):
    """Audio patch/routing configuration."""
    __tablename__ = "patches"

    id = Column(Integer, primary_key=True, index=True)
    patch_type = Column(SQLEnum(PatchType), nullable=False)

    # Source information
    source_device = Column(String(64), nullable=False)  # e.g., "TF-RACK", "TIO-1608-D-1"
    source_port = Column(Integer, nullable=False)
    source_channel_name = Column(String(64), nullable=True)

    # Destination information
    dest_device = Column(String(64), nullable=False)
    dest_port = Column(Integer, nullable=False)
    dest_channel_name = Column(String(64), nullable=True)

    # Associated channel ID if applicable
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)

    # Dante specific
    dante_flow_id = Column(String(128), nullable=True)

    def __repr__(self):
        return f"<Patch {self.source_device}:{self.source_port} -> {self.dest_device}:{self.dest_port}>"
