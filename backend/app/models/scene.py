"""
Scene models for storing and recalling mixer configurations.
"""

from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Scene(Base):
    """Scene/snapshot configuration."""
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, index=True)
    scene_number = Column(Integer, nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    description = Column(String(256), nullable=True)

    # Scene metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Fade time in seconds (0-60)
    fade_time = Column(Float, default=0.0)

    # Full mixer state stored as JSON
    mixer_state = Column(JSON, default=dict)

    # E-ink display labels (channel -> label mapping)
    eink_labels = Column(JSON, default=dict)

    # Relationships
    channels = relationship("SceneChannel", back_populates="scene", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Scene {self.scene_number}: {self.name}>"


class SceneChannel(Base):
    """Individual channel state within a scene."""
    __tablename__ = "scene_channels"

    id = Column(Integer, primary_key=True, index=True)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)

    # Recall safe flags
    recall_fader = Column(Integer, default=1)  # 1 = recall, 0 = safe
    recall_on = Column(Integer, default=1)
    recall_eq = Column(Integer, default=1)
    recall_comp = Column(Integer, default=1)
    recall_gate = Column(Integer, default=1)
    recall_sends = Column(Integer, default=1)

    # Channel state snapshot
    channel_state = Column(JSON, default=dict)

    # Relationships
    scene = relationship("Scene", back_populates="channels")

    def __repr__(self):
        return f"<SceneChannel scene={self.scene_id} channel={self.channel_id}>"
