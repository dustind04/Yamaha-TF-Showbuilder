"""
Dante Device Discovery Service

Uses mDNS/DNS-SD to discover Dante audio devices on the network,
including TIO-1608-D stage boxes and other Dante-enabled equipment.
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from zeroconf import ServiceListener, Zeroconf, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser

logger = logging.getLogger(__name__)


@dataclass
class DanteDevice:
    """Represents a discovered Dante device."""
    name: str
    ip_address: str
    port: int = 0
    model: str = ""
    manufacturer: str = ""
    mac_address: str = ""
    sample_rate: int = 48000
    input_channels: int = 0
    output_channels: int = 0
    dante_version: str = ""
    is_online: bool = True
    last_seen: datetime = field(default_factory=datetime.now)
    properties: Dict[str, Any] = field(default_factory=dict)


class DanteServiceListener(ServiceListener):
    """Listener for Dante mDNS service announcements."""

    def __init__(self, callback: Callable[[str, DanteDevice], None], async_zc: 'AsyncZeroconf'):
        self.callback = callback
        self.async_zc = async_zc

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is discovered."""
        import asyncio
        asyncio.create_task(self._async_add_service(type_, name))

    async def _async_add_service(self, type_: str, name: str) -> None:
        """Async handler for service discovery."""
        try:
            from zeroconf.asyncio import AsyncServiceInfo
            info = AsyncServiceInfo(type_, name)
            await info.async_request(self.async_zc.zeroconf, 3000)
            if info:
                device = self._parse_service_info(info)
                self.callback("add", device)
        except Exception as e:
            logger.debug(f"Could not get service info for {name}: {e}")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is removed."""
        device = DanteDevice(name=name, ip_address="", is_online=False)
        self.callback("remove", device)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is updated."""
        import asyncio
        asyncio.create_task(self._async_update_service(type_, name))

    async def _async_update_service(self, type_: str, name: str) -> None:
        """Async handler for service updates."""
        try:
            from zeroconf.asyncio import AsyncServiceInfo
            info = AsyncServiceInfo(type_, name)
            await info.async_request(self.async_zc.zeroconf, 3000)
            if info:
                device = self._parse_service_info(info)
                self.callback("update", device)
        except Exception as e:
            logger.debug(f"Could not get service info for {name}: {e}")

    def _parse_service_info(self, info: ServiceInfo) -> DanteDevice:
        """Parse mDNS service info into DanteDevice."""
        # Extract IP address
        addresses = info.parsed_addresses()
        ip_address = addresses[0] if addresses else ""

        # Extract properties
        properties = {}
        if info.properties:
            for key, value in info.properties.items():
                if isinstance(key, bytes):
                    key = key.decode('utf-8', errors='ignore')
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='ignore')
                properties[key] = value

        # Determine device type from properties or name
        model = properties.get('model', '')
        manufacturer = properties.get('manufacturer', 'Yamaha')

        # TIO-1608-D specific detection
        name_lower = info.name.lower()
        if 'tio' in name_lower or 'tio-1608' in name_lower:
            model = model or 'TIO-1608-D'
            manufacturer = 'Yamaha'

        return DanteDevice(
            name=info.name.split('.')[0],  # Remove service type suffix
            ip_address=ip_address,
            port=info.port,
            model=model,
            manufacturer=manufacturer,
            properties=properties,
            input_channels=self._get_channel_count(properties, 'inputs', 16),
            output_channels=self._get_channel_count(properties, 'outputs', 8),
        )

    def _get_channel_count(self, props: Dict, key: str, default: int) -> int:
        """Extract channel count from properties."""
        value = props.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default


class DanteDiscoveryService:
    """
    Service for discovering and tracking Dante devices on the network.

    Uses mDNS to discover devices announcing the following services:
    - _netaudio-arc._udp.local. (Dante ARC)
    - _netaudio-cmc._udp.local. (Dante Controller)
    - _netaudio-dbc._udp.local. (Dante Browser)
    """

    DANTE_SERVICE_TYPES = [
        "_netaudio-arc._udp.local.",
        "_netaudio-cmc._udp.local.",
        "_netaudio-dbc._udp.local.",
    ]

    def __init__(self):
        self.zeroconf: Optional[AsyncZeroconf] = None
        self.browsers: List[AsyncServiceBrowser] = []
        self.devices: Dict[str, DanteDevice] = {}
        self._callbacks: List[Callable[[str, DanteDevice], None]] = []
        self._running = False

    async def start_discovery(self):
        """Start discovering Dante devices."""
        if self._running:
            return

        self._running = True
        logger.info("Starting Dante device discovery...")

        self.zeroconf = AsyncZeroconf()

        # Create listener with async zeroconf reference
        listener = DanteServiceListener(self._on_device_event, self.zeroconf)

        # Browse for each Dante service type
        for service_type in self.DANTE_SERVICE_TYPES:
            browser = AsyncServiceBrowser(
                self.zeroconf.zeroconf,
                service_type,
                listener
            )
            self.browsers.append(browser)
            logger.debug(f"Browsing for {service_type}")

        logger.info("Dante discovery started")

    async def stop_discovery(self):
        """Stop device discovery."""
        self._running = False

        for browser in self.browsers:
            try:
                await browser.async_cancel()
            except AttributeError:
                # Older API - try cancel()
                try:
                    browser.cancel()
                except Exception:
                    pass
            except Exception as e:
                logger.debug(f"Error canceling browser: {e}")
        self.browsers.clear()

        if self.zeroconf:
            try:
                await self.zeroconf.async_close()
            except Exception as e:
                logger.debug(f"Error closing zeroconf: {e}")
            self.zeroconf = None

        logger.info("Dante discovery stopped")

    def _on_device_event(self, event: str, device: DanteDevice):
        """Handle device discovery events."""
        if event == "add":
            self.devices[device.name] = device
            logger.info(f"Discovered Dante device: {device.name} ({device.ip_address})")
        elif event == "remove":
            if device.name in self.devices:
                self.devices[device.name].is_online = False
                logger.info(f"Dante device offline: {device.name}")
        elif event == "update":
            if device.name in self.devices:
                self.devices[device.name] = device
                logger.debug(f"Updated Dante device: {device.name}")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(event, device)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def register_callback(self, callback: Callable[[str, DanteDevice], None]):
        """Register a callback for device events."""
        self._callbacks.append(callback)

    def get_devices(self) -> List[DanteDevice]:
        """Get list of all discovered devices."""
        return list(self.devices.values())

    def get_device(self, name: str) -> Optional[DanteDevice]:
        """Get a specific device by name."""
        return self.devices.get(name)

    def get_online_devices(self) -> List[DanteDevice]:
        """Get list of online devices."""
        return [d for d in self.devices.values() if d.is_online]

    def get_tio_devices(self) -> List[DanteDevice]:
        """Get list of TIO stage box devices."""
        return [d for d in self.devices.values()
                if 'tio' in d.model.lower() or 'tio' in d.name.lower()]


class DanteControlService:
    """
    Service for controlling Dante routing.

    Note: Full Dante routing control requires Dante Controller API
    or direct AES67/Dante protocol implementation. This provides
    a simplified interface for common operations.
    """

    def __init__(self, discovery: DanteDiscoveryService):
        self.discovery = discovery

    async def create_subscription(
        self,
        receiver_device: str,
        receiver_channel: int,
        transmitter_device: str,
        transmitter_channel: int
    ) -> bool:
        """
        Create a Dante audio subscription (route).

        Args:
            receiver_device: Name of receiving device
            receiver_channel: Input channel on receiver
            transmitter_device: Name of transmitting device
            transmitter_channel: Output channel on transmitter

        Returns:
            True if subscription created successfully
        """
        # In a full implementation, this would use Dante Controller API
        # or direct protocol communication
        logger.info(
            f"Creating subscription: {transmitter_device}:{transmitter_channel} -> "
            f"{receiver_device}:{receiver_channel}"
        )
        # Placeholder for actual implementation
        return True

    async def remove_subscription(
        self,
        receiver_device: str,
        receiver_channel: int
    ) -> bool:
        """Remove a Dante audio subscription."""
        logger.info(f"Removing subscription on {receiver_device}:{receiver_channel}")
        return True

    async def get_subscriptions(self, device: str) -> List[Dict[str, Any]]:
        """Get all subscriptions for a device."""
        # Placeholder
        return []

    async def set_device_name(self, device: str, new_name: str) -> bool:
        """Set the Dante device name."""
        logger.info(f"Renaming device {device} to {new_name}")
        return True

    async def set_sample_rate(self, device: str, sample_rate: int) -> bool:
        """Set device sample rate."""
        if sample_rate not in [44100, 48000, 88200, 96000]:
            return False
        logger.info(f"Setting {device} sample rate to {sample_rate}")
        return True
