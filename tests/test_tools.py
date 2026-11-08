"""Unit tests for Tool Engine core (BaseTool, ToolResult, ToolRegistry)."""

import pytest
from typing import Any, Dict
from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult
from src.tools.registry import ToolRegistry


class DummyEchoTool(BaseTool):
    name = "dummy_echo"
    description = "Echoes the provided message."
    confirmation_policy = ConfirmationPolicy.IMMEDIATE

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "text": {
                        "type": "STRING",
                        "description": "Text to echo"
                    }
                },
                "required": ["text"]
            }
        }

    def execute(self, text: str = "") -> ToolResult:
        return ToolResult(
            success=True,
            message=f"Echo: {text}",
            data={"echoed": text}
        )


class DummyDangerousTool(BaseTool):
    name = "dummy_dangerous"
    description = "A dangerous operation requiring confirmation."
    confirmation_policy = ConfirmationPolicy.REQUIRE_CONFIRMATION
    confirmation_prompt = "Bu tehlikeli işlemi onaylıyor musunuz efendim?"

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "OBJECT", "properties": {}}
        }

    def execute(self) -> ToolResult:
        return ToolResult(success=True, message="Tehlikeli işlem başarıyla tamamlandı efendim.")


class DummyFaultyTool(BaseTool):
    name = "dummy_faulty"
    description = "A tool that throws an error."

    def get_declaration(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description}

    def execute(self) -> ToolResult:
        raise RuntimeError("Donanım hatası")


def test_tool_result_defaults():
    res = ToolResult(message="İşlem tamamlandı")
    assert res.success is True
    assert res.message == "İşlem tamamlandı"
    assert res.data is None
    assert res.needs_confirmation is False


def test_tool_registry_registration_and_listing():
    registry = ToolRegistry()
    assert registry.list_tools() == []

    tool = DummyEchoTool()
    registry.register(tool)
    assert registry.list_tools() == ["dummy_echo"]
    assert registry.get("dummy_echo") is tool
    assert registry.get("non_existent") is None


def test_tool_registry_rejects_duplicates_and_invalid():
    registry = ToolRegistry()
    tool = DummyEchoTool()
    registry.register(tool)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(DummyEchoTool())

    with pytest.raises(TypeError):
        registry.register("not_a_tool")  # type: ignore


def test_tool_registry_get_declarations():
    registry = ToolRegistry()
    tool = DummyEchoTool()
    registry.register(tool)

    decls = registry.get_declarations()
    assert len(decls) == 1
    assert decls[0]["name"] == "dummy_echo"
    assert "parameters" in decls[0]
    assert decls[0]["parameters"]["type"] == "OBJECT"


def test_tool_registry_execute_success():
    registry = ToolRegistry()
    registry.register(DummyEchoTool())

    res = registry.execute("dummy_echo", {"text": "merhaba"})
    assert res.success is True
    assert res.message == "Echo: merhaba"
    assert res.data == {"echoed": "merhaba"}


def test_tool_registry_execute_missing_tool():
    registry = ToolRegistry()
    res = registry.execute("unknown_tool", {})
    assert res.success is False
    assert "bulunamadı" in res.message


def test_tool_registry_execute_exception_handling():
    registry = ToolRegistry()
    registry.register(DummyFaultyTool())

    res = registry.execute("dummy_faulty")
    assert res.success is False
    assert "bir hata oluştu" in res.message
    assert "Donanım hatası" in res.message


def test_tool_registry_confirmation_flow():
    registry = ToolRegistry()
    registry.register(DummyDangerousTool())

    # When not confirmed, should return confirmation prompt
    res1 = registry.execute("dummy_dangerous", confirmed=False)
    assert res1.success is False
    assert res1.needs_confirmation is True
    assert "onaylıyor musunuz efendim?" in res1.message
    assert res1.data["pending_tool"] == "dummy_dangerous"

    # When confirmed, should execute
    res2 = registry.execute("dummy_dangerous", confirmed=True)
    assert res2.success is True
    assert res2.needs_confirmation is False
    assert "tamamlandı" in res2.message
