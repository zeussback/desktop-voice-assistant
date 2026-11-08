"""Unit tests for OS control tools (SystemAudioTool, MediaControlTool, etc.)."""

import pytest
from unittest.mock import MagicMock, patch
from src.tools.system_audio import SystemAudioTool
from src.tools.media_control import (
    MediaControlTool,
    VK_MEDIA_PLAY_PAUSE,
    VK_MEDIA_NEXT_TRACK,
    VK_MEDIA_PREV_TRACK,
    VK_MEDIA_STOP,
)


@pytest.fixture
def mock_volume():
    mock = MagicMock()
    mock.GetMasterVolumeLevelScalar.return_value = 0.50
    mock.GetMute.return_value = 0
    return mock


@pytest.fixture
def audio_tool(mock_volume):
    tool = SystemAudioTool()
    tool._get_endpoint_volume = MagicMock(return_value=mock_volume)
    return tool


def test_system_audio_tool_declaration():
    tool = SystemAudioTool()
    decl = tool.get_declaration()
    assert decl["name"] == "control_system_audio"
    assert "parameters" in decl
    assert "action" in decl["parameters"]["properties"]


def test_system_audio_set_volume(audio_tool, mock_volume):
    res = audio_tool.execute("set_volume", level=75)
    assert res.success is True
    assert "75" in res.message
    mock_volume.SetMasterVolumeLevelScalar.assert_called_once_with(0.75, None)


def test_system_audio_set_volume_clamping(audio_tool, mock_volume):
    res = audio_tool.execute("set_volume", level=150)
    assert res.success is True
    assert "100" in res.message
    mock_volume.SetMasterVolumeLevelScalar.assert_called_once_with(1.0, None)

    mock_volume.reset_mock()
    res2 = audio_tool.execute("set_volume", level=-20)
    assert res2.success is True
    assert "0" in res2.message
    mock_volume.SetMasterVolumeLevelScalar.assert_called_once_with(0.0, None)


def test_system_audio_set_volume_missing_level(audio_tool):
    res = audio_tool.execute("set_volume")
    assert res.success is False
    assert "belirtmelisiniz" in res.message


def test_system_audio_change_volume(audio_tool, mock_volume):
    mock_volume.GetMasterVolumeLevelScalar.return_value = 0.40
    res = audio_tool.execute("change_volume", delta=15)
    assert res.success is True
    assert "55" in res.message
    mock_volume.SetMasterVolumeLevelScalar.assert_called_once_with(0.55, None)


def test_system_audio_change_volume_missing_delta(audio_tool):
    res = audio_tool.execute("change_volume")
    assert res.success is False
    assert "miktarını" in res.message


def test_system_audio_get_volume(audio_tool, mock_volume):
    mock_volume.GetMasterVolumeLevelScalar.return_value = 0.62
    mock_volume.GetMute.return_value = 0
    res = audio_tool.execute("get_volume")
    assert res.success is True
    assert "62" in res.message
    assert res.data["volume"] == 62
    assert res.data["is_muted"] is False


def test_system_audio_mute_and_unmute(audio_tool, mock_volume):
    res_mute = audio_tool.execute("mute")
    assert res_mute.success is True
    mock_volume.SetMute.assert_called_with(1, None)

    mock_volume.GetMasterVolumeLevelScalar.return_value = 0.50
    res_unmute = audio_tool.execute("unmute")
    assert res_unmute.success is True
    mock_volume.SetMute.assert_called_with(0, None)


def test_system_audio_invalid_action(audio_tool):
    res = audio_tool.execute("invalid_action")
    assert res.success is False
    assert "Geçersiz" in res.message


def test_system_audio_exception_handling(audio_tool):
    audio_tool._get_endpoint_volume = MagicMock(side_effect=RuntimeError("COM Hatası"))
    res = audio_tool.execute("get_volume")
    assert res.success is False
    assert "bir hata oluştu" in res.message
    assert "COM Hatası" in res.message


def test_media_control_declaration():
    tool = MediaControlTool()
    decl = tool.get_declaration()
    assert decl["name"] == "control_media"
    assert "action" in decl["parameters"]["properties"]


@patch("src.tools.media_control._send_media_key")
def test_media_control_actions(mock_send_key):
    tool = MediaControlTool()

    res_play = tool.execute("play_pause")
    assert res_play.success is True
    mock_send_key.assert_called_with(VK_MEDIA_PLAY_PAUSE)

    res_next = tool.execute("next_track")
    assert res_next.success is True
    mock_send_key.assert_called_with(VK_MEDIA_NEXT_TRACK)

    res_prev = tool.execute("previous_track")
    assert res_prev.success is True
    mock_send_key.assert_called_with(VK_MEDIA_PREV_TRACK)

    res_stop = tool.execute("stop")
    assert res_stop.success is True
    mock_send_key.assert_called_with(VK_MEDIA_STOP)


def test_media_control_invalid_action():
    tool = MediaControlTool()
    res = tool.execute("unknown_media_action")
    assert res.success is False
    assert "Bilinmeyen" in res.message


# ==========================================
# SystemBrightnessTool Tests
# ==========================================
from src.tools.system_brightness import SystemBrightnessTool


def test_system_brightness_declaration():
    tool = SystemBrightnessTool()
    decl = tool.get_declaration()
    assert decl["name"] == "control_system_brightness"
    assert "action" in decl["parameters"]["properties"]


def test_system_brightness_set_volume():
    tool = SystemBrightnessTool()
    tool._set_brightness = MagicMock()

    res = tool.execute("set_brightness", level=60)
    assert res.success is True
    assert "60" in res.message
    tool._set_brightness.assert_called_once_with(60)


def test_system_brightness_set_clamping():
    tool = SystemBrightnessTool()
    tool._set_brightness = MagicMock()

    res = tool.execute("set_brightness", level=130)
    assert res.success is True
    assert "100" in res.message
    tool._set_brightness.assert_called_once_with(100)


def test_system_brightness_set_missing_level():
    tool = SystemBrightnessTool()
    res = tool.execute("set_brightness")
    assert res.success is False
    assert "seviye" in res.message


def test_system_brightness_change():
    tool = SystemBrightnessTool()
    tool._get_current_brightness = MagicMock(return_value=50)
    tool._set_brightness = MagicMock()

    res = tool.execute("change_brightness", delta=-20)
    assert res.success is True
    assert "30" in res.message
    tool._set_brightness.assert_called_once_with(30)


def test_system_brightness_change_missing_delta():
    tool = SystemBrightnessTool()
    res = tool.execute("change_brightness")
    assert res.success is False
    assert "miktarını" in res.message


def test_system_brightness_get():
    tool = SystemBrightnessTool()
    tool._get_current_brightness = MagicMock(return_value=85)

    res = tool.execute("get_brightness")
    assert res.success is True
    assert "85" in res.message
    assert res.data["brightness"] == 85


def test_system_brightness_unsupported_hardware():
    tool = SystemBrightnessTool()
    tool._get_current_brightness = MagicMock(side_effect=RuntimeError("DDC/CI error"))

    res = tool.execute("get_brightness")
    assert res.success is False
    assert "desteklemiyor" in res.message


# ==========================================
# WebBrowserTool Tests
# ==========================================
from src.tools.web_browser import WebBrowserTool


def test_web_browser_declaration():
    tool = WebBrowserTool()
    decl = tool.get_declaration()
    assert decl["name"] == "open_web_browser"
    assert "action" in decl["parameters"]["properties"]


@patch("webbrowser.open")
def test_web_browser_open_url_with_protocol(mock_open):
    tool = WebBrowserTool()
    res = tool.execute("open_url", url="https://www.youtube.com")
    assert res.success is True
    assert "https://www.youtube.com" in res.message
    mock_open.assert_called_once_with("https://www.youtube.com")


@patch("webbrowser.open")
def test_web_browser_open_url_prepends_https(mock_open):
    tool = WebBrowserTool()
    res = tool.execute("open_url", url="github.com")
    assert res.success is True
    mock_open.assert_called_once_with("https://github.com")


def test_web_browser_open_url_missing():
    tool = WebBrowserTool()
    res = tool.execute("open_url")
    assert res.success is False
    assert "belirtmelisiniz" in res.message


@patch("webbrowser.open")
def test_web_browser_search_google(mock_open):
    tool = WebBrowserTool()
    res = tool.execute("search_google", query="yapay zeka haberleri")
    assert res.success is True
    assert "yapay zeka haberleri" in res.message
    mock_open.assert_called_once_with("https://www.google.com/search?q=yapay+zeka+haberleri")


def test_web_browser_search_google_missing():
    tool = WebBrowserTool()
    res = tool.execute("search_google")
    assert res.success is False
    assert "ifadesi" in res.message


def test_web_browser_invalid_action():
    tool = WebBrowserTool()
    res = tool.execute("invalid_action")
    assert res.success is False
    assert "Bilinmeyen" in res.message
