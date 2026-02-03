"""
Wireless Microphone Monitoring Service

Inspired by Micboard (https://github.com/karlcswanson/micboard)
Monitors Shure wireless devices for:
- Battery levels
- RF signal strength
- Audio levels
- Device status

Supports:
- Shure ULX-D
- Shure QLX-D
- Shure Axient Digital
- Shure PSM 1000 (IEM)
"""

import asyncio
import logging
import socket
import struct
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DeviceType(str, Enum):
    ULXD = "ulxd"
    QLXD = "qlxd"
    AXIENT = "axient"
    PSM1000 = "psm1000"
    UNKNOWN = "unknown"


class BatteryStatus(str, Enum):
    FULL = "full"
    GOOD = "good"
    LOW = "low"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class WirelessChannel:
    """Status of a single wireless channel/receiver."""
    slot: int
    name: str = ""
    type: str = ""  # "handheld", "bodypack", "iem"

    # RF metrics
    rf_level: int = 0  # 0-100
    antenna_a: int = 0
    antenna_b: int = 0
    diversity: str = "A"  # "A", "B", "AB"

    # Audio
    audio_level: int = 0  # 0-100
    audio_peak: bool = False
    muted: bool = False

    # Battery
    battery_percent: int = 0
    battery_bars: int = 0  # 0-5
    battery_status: BatteryStatus = BatteryStatus.UNKNOWN
    battery_runtime: int = 0  # minutes remaining

    # Transmitter info
    tx_type: str = ""  # "ULXD1", "ULXD2", etc.
    tx_power: str = ""  # "HIGH", "NORMAL", "LOW"
    frequency: str = ""
    group_channel: str = ""  # e.g., "G50 CH01"

    # Status
    active: bool = False
    interference: bool = False
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class WirelessDevice:
    """A wireless receiver unit (may have multiple channels)."""
    ip_address: str
    device_type: DeviceType
    name: str = ""
    model: str = ""
    firmware: str = ""
    channels: Dict[int, WirelessChannel] = field(default_factory=dict)
    online: bool = False
    last_seen: datetime = field(default_factory=datetime.now)


class ShureProtocol:
    """
    Shure wireless device communication protocol.

    Uses UDP for device discovery and TCP for status monitoring.
    Based on Shure's network protocol documentation.
    """

    # Shure discovery port
    DISCOVERY_PORT = 2202

    # Status update port
    STATUS_PORT = 2203

    # Command codes
    CMD_GET_STATUS = b"< GET 0 ALL >"
    CMD_GET_BATTERY = b"< GET BATT_BARS >"
    CMD_GET_RF = b"< GET RF_LEVEL >"
    CMD_GET_AUDIO = b"< GET AUDIO_LEVEL >"

    @staticmethod
    def parse_status_line(line: str) -> Dict[str, Any]:
        """Parse a Shure status response line."""
        # Format: < REP slot param value >
        parts = line.strip("< >").split()
        if len(parts) >= 4 and parts[0] == "REP":
            return {
                "slot": int(parts[1]),
                "param": parts[2],
                "value": " ".join(parts[3:])
            }
        return {}

    @staticmethod
    def battery_bars_to_status(bars: int) -> BatteryStatus:
        """Convert battery bars to status."""
        if bars >= 4:
            return BatteryStatus.FULL
        elif bars >= 3:
            return BatteryStatus.GOOD
        elif bars >= 2:
            return BatteryStatus.LOW
        elif bars >= 1:
            return BatteryStatus.CRITICAL
        return BatteryStatus.UNKNOWN


class WirelessMonitorService:
    """
    Service for monitoring wireless microphone systems.

    Provides real-time monitoring of:
    - Battery levels and estimated runtime
    - RF signal strength with diversity indication
    - Audio levels with peak detection
    - Device online/offline status
    """

    def __init__(self):
        self.devices: Dict[str, WirelessDevice] = {}
        self._callbacks: List[Callable[[str, WirelessDevice], None]] = []
        self._running = False
        self._poll_interval = 1.0  # seconds

    async def start(self):
        """Start the wireless monitoring service."""
        if self._running:
            return

        self._running = True
        logger.info("Starting wireless monitor service")

        # Start polling task
        asyncio.create_task(self._poll_loop())

    async def stop(self):
        """Stop the wireless monitoring service."""
        self._running = False
        logger.info("Stopped wireless monitor service")

    def add_device(self, ip_address: str, device_type: DeviceType = DeviceType.ULXD, name: str = ""):
        """Add a wireless device to monitor."""
        if ip_address not in self.devices:
            device = WirelessDevice(
                ip_address=ip_address,
                device_type=device_type,
                name=name or ip_address
            )
            # Initialize channels based on device type
            if device_type in [DeviceType.ULXD, DeviceType.QLXD]:
                # Quad receiver has 4 channels
                for i in range(1, 5):
                    device.channels[i] = WirelessChannel(slot=i)
            elif device_type == DeviceType.AXIENT:
                for i in range(1, 5):
                    device.channels[i] = WirelessChannel(slot=i)
            elif device_type == DeviceType.PSM1000:
                # PSM1000 is typically 2-channel
                for i in range(1, 3):
                    device.channels[i] = WirelessChannel(slot=i, type="iem")

            self.devices[ip_address] = device
            logger.info(f"Added wireless device: {name} ({ip_address})")

    def remove_device(self, ip_address: str):
        """Remove a device from monitoring."""
        if ip_address in self.devices:
            del self.devices[ip_address]
            logger.info(f"Removed wireless device: {ip_address}")

    def register_callback(self, callback: Callable[[str, WirelessDevice], None]):
        """Register a callback for device updates."""
        self._callbacks.append(callback)

    async def _poll_loop(self):
        """Main polling loop for device status."""
        while self._running:
            for ip, device in self.devices.items():
                try:
                    await self._poll_device(device)
                    device.online = True
                    device.last_seen = datetime.now()
                except Exception as e:
                    logger.debug(f"Failed to poll {ip}: {e}")
                    device.online = False

                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback("update", device)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")

            await asyncio.sleep(self._poll_interval)

    async def _poll_device(self, device: WirelessDevice):
        """Poll a single device for status."""
        # In production, this would use actual Shure protocol
        # For demo, we'll simulate the data
        pass

    def get_all_status(self) -> List[Dict[str, Any]]:
        """Get status of all monitored devices."""
        result = []
        for ip, device in self.devices.items():
            channels = []
            for slot, channel in device.channels.items():
                channels.append({
                    "slot": slot,
                    "name": channel.name,
                    "type": channel.type,
                    "rf_level": channel.rf_level,
                    "audio_level": channel.audio_level,
                    "battery_percent": channel.battery_percent,
                    "battery_bars": channel.battery_bars,
                    "battery_status": channel.battery_status.value,
                    "battery_runtime": channel.battery_runtime,
                    "frequency": channel.frequency,
                    "active": channel.active,
                    "muted": channel.muted,
                    "interference": channel.interference
                })

            result.append({
                "ip_address": ip,
                "name": device.name,
                "model": device.model,
                "device_type": device.device_type.value,
                "online": device.online,
                "last_seen": device.last_seen.isoformat(),
                "channels": channels
            })

        return result

    def get_low_battery_alerts(self) -> List[Dict[str, Any]]:
        """Get list of channels with low battery."""
        alerts = []
        for ip, device in self.devices.items():
            for slot, channel in device.channels.items():
                if channel.battery_status in [BatteryStatus.LOW, BatteryStatus.CRITICAL]:
                    alerts.append({
                        "device": device.name,
                        "slot": slot,
                        "name": channel.name,
                        "battery_percent": channel.battery_percent,
                        "battery_status": channel.battery_status.value,
                        "runtime_minutes": channel.battery_runtime
                    })
        return alerts

    def get_rf_issues(self) -> List[Dict[str, Any]]:
        """Get list of channels with RF issues."""
        issues = []
        for ip, device in self.devices.items():
            for slot, channel in device.channels.items():
                if channel.interference or channel.rf_level < 20:
                    issues.append({
                        "device": device.name,
                        "slot": slot,
                        "name": channel.name,
                        "rf_level": channel.rf_level,
                        "interference": channel.interference,
                        "frequency": channel.frequency
                    })
        return issues


# Singleton instance
wireless_monitor = WirelessMonitorService()
