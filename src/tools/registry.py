"""Central registry for managing, introspecting, and executing tools."""

import logging
from typing import Any, Dict, List, Optional
from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Manages tool registration, Gemini schema generation, and invocation."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a new tool instance."""
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Expected BaseTool instance, got {type(tool).__name__}")
        if not getattr(tool, "name", None):
            raise ValueError("Tool must define a non-empty 'name' attribute.")
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")

        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """Return a list of all registered tool names."""
        return list(self._tools.keys())

    def get_declarations(self) -> List[Dict[str, Any]]:
        """Return Gemini-compatible function declaration dictionaries for all registered tools."""
        return [tool.get_declaration() for tool in self._tools.values()]

    def execute(self, name: str, args: Optional[Dict[str, Any]] = None, confirmed: bool = False) -> ToolResult:
        """Execute a tool by name with arguments.
        
        Args:
            name: The tool's unique identifier.
            args: Key-value dictionary of arguments for the tool.
            confirmed: Whether the user has explicitly confirmed the action (for confirmation-required tools).
        """
        tool = self._tools.get(name)
        if not tool:
            logger.warning(f"Tool not found: {name}")
            return ToolResult(
                success=False,
                message=f"'{name}' adında bir araç bulunamadı efendim."
            )

        # Check confirmation policy
        if tool.confirmation_policy == ConfirmationPolicy.REQUIRE_CONFIRMATION and not confirmed:
            prompt = getattr(tool, "confirmation_prompt", None) or f"{name} işlemini gerçekleştirmek istediğinizden emin misiniz efendim?"
            return ToolResult(
                success=False,
                message=prompt,
                needs_confirmation=True,
                confirmation_prompt=prompt,
                data={"pending_tool": name, "pending_args": args or {}}
            )

        kwargs = args or {}
        try:
            logger.info(f"Executing tool '{name}' with args: {kwargs}")
            return tool.execute(**kwargs)
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"'{name}' işlemi gerçekleştirilirken bir hata oluştu efendim: {str(e)}"
            )
