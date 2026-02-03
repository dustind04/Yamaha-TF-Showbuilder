"""
Channel models for TF-Rack inputs and outputs.
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base


class ChannelType(str, Enum):
    INPUT = "input"
    AUX = "aux"
    STEREO = "stereo"
    MATRIX = "matrix"
    DCA = "dca"
    FX_SEND = "fx_send"
    FX_RETURN = "fx_return"


class Channel(Base):
    """Channel configuration model."""
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    channel_number = Column(Integer, nullable=False)
    channel_type = Column(SQLEnum(ChannelType), nullable=False)
    name = Column(String(32), default="")
    color = Column(String(16), default="white")
    icon = Column(String(32), default="")

    # Fader and levels
    fader_level = Column(Float, default=-90.0)  # dB, -90 (off) to +10
    pan = Column(Float, default=0.0)  # -100 to +100
    mute = Column(Boolean, default=False)
    on = Column(Boolean, default=True)

    # Input settings
    phantom_power = Column(Boolean, default=False)
    gain = Column(Float, default=0.0)  # dB
    phase_invert = Column(Boolean, default=False)

    # EQ settings (stored as JSON)
    eq_enabled = Column(Boolean, default=True)
    eq_settings = Column(JSON, default=lambda: {
        "hpf_enabled": False,
        "hpf_frequency": 80,
        "low": {"frequency": 100, "gain": 0, "q": 1.0, "type": "shelf"},
        "low_mid": {"frequency": 400, "gain": 0, "q": 1.0, "type": "peak"},
        "high_mid": {"frequency": 2000, "gain": 0, "q": 1.0, "type": "peak"},
        "high": {"frequency": 8000, "gain": 0, "q": 1.0, "type": "shelf"}
    })

    # Compressor settings (stored as JSON)
    comp_enabled = Column(Boolean, default=False)
    comp_settings = Column(JSON, default=lambda: {
        "threshold": -10,
        "ratio": 4.0,
        "attack": 25,
        "release": 200,
        "gain": 0,
        "knee": "medium"
    })

    # Gate settings (stored as JSON)
    gate_enabled = Column(Boolean, default=False)
    gate_settings = Column(JSON, default=lambda: {
        "threshold": -60,
        "range": -80,
        "attack": 1,
        "hold": 100,
        "release": 200
    })

    # Aux sends (stored as JSON - dict of aux number to send level)
    aux_sends = Column(JSON, default=dict)

    # Patching info
    physical_input = Column(String(32), nullable=True)
    dante_channel = Column(String(64), nullable=True)

    def __repr__(self):
        return f"<Channel {self.channel_type.value} {self.channel_number}: {self.name}>"
