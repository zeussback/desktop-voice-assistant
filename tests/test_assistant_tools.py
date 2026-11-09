"""Integration tests for AssistantController tool execution and confirmation lifecycle."""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication

from src.brain.provider_base import BrainResponse
from src.core.assistant import AssistantController
from src.tools import create_default_tool_registry
from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult
from src.tools.registry import ToolRegistry


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_components():
    brain = MagicMock()
    voice = MagicMock()
    voice.synthesize.return_value = b"RIFFFAKEWAVDATA"
    recorder = MagicMock()
    recorder.start_recording.return_value = True
    recorder.stop_recording.return_value = b"FAKE_AUDIO_BYTES_LONGER_THAN_100_" * 4
    widget = MagicMock()
    player = MagicMock()
    player.is_playing.return_value = False

    return {
        "brain": brain,
        "voice": voice,
        "recorder": recorder,
        "widget": widget,
        "player": player,
    }


def test_create_default_tool_registry():
    registry = create_default_tool_registry()
    tools = registry.list_tools()

    expected = [
        "control_system_audio",
        "control_media",
        "control_system_brightness",
        "open_web_browser",
        "control_application",
        "control_system_power",
        "inspect_screen",
        "manage_calendar",
        "manage_gmail",
        "get_morning_briefing",
    ]
    for exp in expected:
        assert exp in tools

    decls = registry.get_declarations()
    assert len(decls) == len(expected)


def test_assistant_controller_executes_tool_response(qapp, mock_components):
    registry = ToolRegistry()
    controller = AssistantController(
        brain=mock_components["brain"],
        voice=mock_components["voice"],
        recorder=mock_components["recorder"],
        widget=mock_components["widget"],
        player=mock_components["player"],
        tool_registry=registry,
    )

    mock_components["brain"].generate_response.return_value = BrainResponse(
        text="Spotify açıldı efendim.",
        provider="gemini",
        tool_called="control_application",
        tool_result={"success": True, "message": "Spotify açıldı efendim."},
    )

    controller._process_audio_worker(b"FAKE_AUDIO_DATA_LONG_ENOUGH_" * 5)

    mock_components["voice"].synthesize.assert_called_with("Spotify açıldı efendim.")
    mock_components["player"].play_bytes.assert_called_once()
    assert controller.pending_confirmation is None


def test_assistant_controller_confirmation_lifecycle_approved(qapp, mock_components):
    registry = ToolRegistry()
    mock_power_tool = MagicMock(spec=BaseTool)
    mock_power_tool.name = "control_system_power"
    mock_power_tool.description = "Power control"
    mock_power_tool.confirmation_policy = ConfirmationPolicy.REQUIRE_CONFIRMATION
    mock_power_tool.execute.return_value = ToolResult(
        success=True, message="Bilgisayarınız kapatılıyor efendim. Görüşmek üzere."
    )
    registry.register(mock_power_tool)

    controller = AssistantController(
        brain=mock_components["brain"],
        voice=mock_components["voice"],
        recorder=mock_components["recorder"],
        widget=mock_components["widget"],
        player=mock_components["player"],
        tool_registry=registry,
    )

    # 1. Turn: Brain says confirmation needed
    mock_components["brain"].generate_response.return_value = BrainResponse(
        text="Bilgisayarı kapatmak istediğinizden emin misiniz efendim?",
        provider="gemini",
        tool_called="control_system_power",
        needs_confirmation=True,
        confirmation_prompt="Bilgisayarı kapatmak istediğinizden emin misiniz efendim?",
        tool_result={"data": {"pending_args": {"action": "shutdown"}}},
    )

    controller._process_audio_worker(b"FAKE_AUDIO_DATA_LONG_ENOUGH_" * 5)

    assert controller.pending_confirmation is not None
    assert controller.pending_confirmation["tool_name"] == "control_system_power"
    mock_components["voice"].synthesize.assert_called_with(
        "Bilgisayarı kapatmak istediğinizden emin misiniz efendim?"
    )

    # 2. Turn: User says "Evet, kapat" -> Confirmed
    mock_components["voice"].reset_mock()
    mock_components["brain"].generate_response.return_value = BrainResponse(
        text="Evet, kapatıyorum efendim.",
        provider="gemini",
    )

    controller._process_audio_worker(b"FAKE_AUDIO_DATA_LONG_ENOUGH_" * 5)

    assert controller.pending_confirmation is None
    mock_power_tool.execute.assert_called_once_with(action="shutdown")
    mock_components["voice"].synthesize.assert_called_with(
        "Bilgisayarınız kapatılıyor efendim. Görüşmek üzere."
    )


def test_assistant_controller_confirmation_lifecycle_cancelled(qapp, mock_components):
    registry = ToolRegistry()
    mock_power_tool = MagicMock(spec=BaseTool)
    mock_power_tool.name = "control_system_power"
    mock_power_tool.confirmation_policy = ConfirmationPolicy.REQUIRE_CONFIRMATION
    registry.register(mock_power_tool)

    controller = AssistantController(
        brain=mock_components["brain"],
        voice=mock_components["voice"],
        recorder=mock_components["recorder"],
        widget=mock_components["widget"],
        player=mock_components["player"],
        tool_registry=registry,
    )

    # Set pending confirmation
    controller.pending_confirmation = {
        "tool_name": "control_system_power",
        "args": {"action": "shutdown"},
        "prompt": "Emin misiniz?",
    }

    # User says "Hayır iptal et"
    mock_components["brain"].generate_response.return_value = BrainResponse(
        text="Hayır, vazgeçtim iptal et.",
        provider="gemini",
    )

    controller._process_audio_worker(b"FAKE_AUDIO_DATA_LONG_ENOUGH_" * 5)

    assert controller.pending_confirmation is None
    mock_power_tool.execute.assert_not_called()
    mock_components["voice"].synthesize.assert_called_with("İşlemi iptal ettim efendim.")
