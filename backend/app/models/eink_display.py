"""
E-ink display models for input labeling.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.core.database import Base


class EInkDisplay(Base):
    """E-ink display unit for channel labeling."""
    __tablename__ = "eink_displays"

    id = Column(Integer, primary_key=True, index=True)
    display_index = Column(Integer, nullable=False, unique=True)  # Physical position (0-15 for 16 displays)

    # USB/Serial identification
    device_id = Column(String(64), nullable=True)  # USB device ID
    serial_port = Column(String(64), nullable=True)  # Serial port path

    # Current display state
    current_text = Column(String(32), default="")
    current_icon = Column(String(32), default="")
    current_color = Column(String(16), default="black")  # Text color for color e-ink
    inverted = Column(Boolean, default=False)

    # Associated channel
    channel_number = Column(Integer, nullable=True)
    channel_type = Column(String(16), default="input")

    # Status
    is_connected = Column(Boolean, default=False)
    last_update = Column(DateTime, nullable=True)
    error_count = Column(Integer, default=0)

    # Display specs
    width = Column(Integer, default=296)  # Pixels
    height = Column(Integer, default=128)  # Pixels
    supports_partial_refresh = Column(Boolean, default=True)

    def __repr__(self):
        return f"<EInkDisplay {self.display_index}: '{self.current_text}'>"
