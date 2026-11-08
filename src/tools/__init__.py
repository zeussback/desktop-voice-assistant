"""Tools module for Jarvis Desktop Voice Assistant."""

from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult
from src.tools.registry import ToolRegistry


def create_default_tool_registry() -> ToolRegistry:
    """Create and return a ToolRegistry populated with all standard OS and system tools."""
    from src.tools.system_audio import SystemAudioTool
    from src.tools.media_control import MediaControlTool
    from src.tools.system_brightness import SystemBrightnessTool
    from src.tools.web_browser import WebBrowserTool
    from src.tools.app_control import AppControlTool
    from src.tools.system_power import SystemPowerTool

    registry = ToolRegistry()
    registry.register(SystemAudioTool())
    registry.register(MediaControlTool())
    registry.register(SystemBrightnessTool())
    registry.register(WebBrowserTool())
    registry.register(AppControlTool())
    registry.register(SystemPowerTool())
    return registry


__all__ = [
    "BaseTool",
    "ConfirmationPolicy",
    "ToolResult",
    "ToolRegistry",
    "create_default_tool_registry",
]
