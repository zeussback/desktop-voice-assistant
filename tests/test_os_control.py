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
