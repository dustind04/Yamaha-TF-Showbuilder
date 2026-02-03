"""
E-Ink Display Manager

Manages communication with e-ink displays for showing channel labels
above physical inputs on the TF-Rack or TIO stage boxes.

Supports common e-ink display modules via USB/Serial communication.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    import usb.core
    import usb.util
except ImportError:
    usb = None

logger = logging.getLogger(__name__)


@dataclass
class DisplayConfig:
    """Configuration for an e-ink display."""
    index: int
    width: int = 296
    height: int = 128
    rotation: int = 0  # 0, 90, 180, 270
    inverted: bool = False
    font_size: int = 24
    supports_color: bool = False
    partial_refresh: bool = True


@dataclass
class DisplayContent:
    """Content to display on an e-ink screen."""
    text: str
    subtext: str = ""
    icon: str = ""
    color: str = "black"
    background: str = "white"
    alignment: str = "center"  # left, center, right


class EInkDisplay:
    """
    Represents a single e-ink display unit.

    Supports multiple display types:
    - Waveshare e-Paper displays (2.9", 4.2", etc.)
    - Good Display modules
    - Generic SPI/USB e-ink displays
    """

    def __init__(self, config: DisplayConfig, device_path: Optional[str] = None):
        self.config = config
        self.device_path = device_path
        self.device = None
        self.current_content: Optional[DisplayContent] = None
        self.last_update: Optional[datetime] = None
        self.is_connected = False

    async def connect(self) -> bool:
        """Connect to the display device."""
        try:
            # For USB devices, find by index or path
            if usb:
                # Find Waveshare or compatible e-ink USB devices
                devices = list(usb.core.find(find_all=True, idVendor=0x1a86))  # CH340
                if self.config.index < len(devices):
                    self.device = devices[self.config.index]
                    self.is_connected = True
                    logger.info(f"Connected to e-ink display {self.config.index}")
                    return True

            logger.warning(f"E-ink display {self.config.index} not found")
            return False

        except Exception as e:
            logger.error(f"Failed to connect to e-ink display: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the display."""
        self.is_connected = False
        self.device = None

    def _create_image(self, content: DisplayContent) -> Optional[bytes]:
        """Create image buffer for the display content."""
        if not Image:
            logger.error("PIL/Pillow not available")
            return None

        # Create image with background color
        bg_color = 255 if content.background == "white" else 0
        img = Image.new('1', (self.config.width, self.config.height), bg_color)
        draw = ImageDraw.Draw(img)

        # Load font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                                       self.config.font_size)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                                             self.config.font_size - 8)
        except Exception:
            font = ImageFont.load_default()
            small_font = font

        text_color = 0 if content.color == "black" else 255

        # Draw main text
        text = content.text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Calculate position based on alignment
        if content.alignment == "center":
            x = (self.config.width - text_width) // 2
        elif content.alignment == "right":
            x = self.config.width - text_width - 10
        else:
            x = 10

        y = (self.config.height - text_height) // 2 - 10

        draw.text((x, y), text, font=font, fill=text_color)

        # Draw subtext if present
        if content.subtext:
            sub_bbox = draw.textbbox((0, 0), content.subtext, font=small_font)
            sub_width = sub_bbox[2] - sub_bbox[0]
            sub_x = (self.config.width - sub_width) // 2
            sub_y = y + text_height + 5
            draw.text((sub_x, sub_y), content.subtext, font=small_font, fill=text_color)

        # Apply rotation if needed
        if self.config.rotation:
            img = img.rotate(self.config.rotation, expand=True)

        # Invert if needed
        if self.config.inverted:
            img = Image.eval(img, lambda x: 255 - x)

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='BMP')
        return buffer.getvalue()

    async def update(self, content: DisplayContent, partial: bool = True) -> bool:
        """
        Update the display with new content.

        Args:
            content: Content to display
            partial: Use partial refresh if supported (faster, less flicker)

        Returns:
            True if update successful
        """
        if not self.is_connected:
            logger.warning(f"Display {self.config.index} not connected")
            return False

        try:
            # Create image
            image_data = self._create_image(content)
            if not image_data:
                return False

            # Send to display (implementation depends on display type)
            await self._send_to_display(image_data, partial)

            self.current_content = content
            self.last_update = datetime.now()

            logger.debug(f"Updated display {self.config.index}: {content.text}")
            return True

        except Exception as e:
            logger.error(f"Failed to update display {self.config.index}: {e}")
            return False

    async def _send_to_display(self, image_data: bytes, partial: bool):
        """Send image data to the physical display."""
        # This would be implemented based on specific display protocol
        # For Waveshare displays, this typically involves:
        # 1. Send init command
        # 2. Set window
        # 3. Send image data
        # 4. Trigger refresh
        pass

    async def clear(self):
        """Clear the display to white."""
        content = DisplayContent(text="", background="white")
        await self.update(content, partial=False)


class EInkManager:
    """
    Manager for multiple e-ink displays.

    Handles discovery, initialization, and coordinated updates
    of all e-ink displays in the system.
    """

    def __init__(self, display_count: int = 16):
        self.display_count = display_count
        self.displays: Dict[int, EInkDisplay] = {}
        self.channel_mapping: Dict[int, int] = {}  # channel -> display index
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize all e-ink displays."""
        logger.info(f"Initializing {self.display_count} e-ink displays...")

        for i in range(self.display_count):
            config = DisplayConfig(index=i)
            display = EInkDisplay(config)

            if await display.connect():
                self.displays[i] = display
                # Default: display index matches channel number
                self.channel_mapping[i + 1] = i

        self._initialized = True
        logger.info(f"Initialized {len(self.displays)} e-ink displays")
        return len(self.displays) > 0

    async def shutdown(self):
        """Shutdown all displays."""
        for display in self.displays.values():
            await display.disconnect()
        self.displays.clear()
        self._initialized = False

    async def update_channel_label(
        self,
        channel: int,
        name: str,
        subtext: str = "",
        color: str = "black"
    ) -> bool:
        """
        Update the label for a specific channel.

        Args:
            channel: Channel number (1-based)
            name: Main text to display
            subtext: Secondary text (e.g., instrument type)
            color: Text color
        """
        display_index = self.channel_mapping.get(channel)
        if display_index is None:
            logger.warning(f"No display mapped for channel {channel}")
            return False

        display = self.displays.get(display_index)
        if not display:
            logger.warning(f"Display {display_index} not available")
            return False

        content = DisplayContent(
            text=name,
            subtext=subtext,
            color=color
        )

        return await display.update(content)

    async def update_all_labels(self, labels: Dict[int, Tuple[str, str]]) -> int:
        """
        Update multiple channel labels at once.

        Args:
            labels: Dict mapping channel -> (name, subtext)

        Returns:
            Number of successfully updated displays
        """
        success_count = 0
        tasks = []

        for channel, (name, subtext) in labels.items():
            task = self.update_channel_label(channel, name, subtext)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if result is True:
                success_count += 1

        return success_count

    async def clear_all(self):
        """Clear all displays."""
        tasks = [display.clear() for display in self.displays.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

    def set_channel_mapping(self, channel: int, display_index: int):
        """Map a channel to a specific display."""
        self.channel_mapping[channel] = display_index

    def get_display_status(self) -> List[Dict]:
        """Get status of all displays."""
        status = []
        for i in range(self.display_count):
            display = self.displays.get(i)
            if display:
                status.append({
                    "index": i,
                    "connected": display.is_connected,
                    "current_text": display.current_content.text if display.current_content else "",
                    "last_update": display.last_update.isoformat() if display.last_update else None
                })
            else:
                status.append({
                    "index": i,
                    "connected": False,
                    "current_text": "",
                    "last_update": None
                })
        return status
