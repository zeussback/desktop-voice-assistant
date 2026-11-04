from unittest.mock import MagicMock
import pytest

from src.core.hotkey_listener import GlobalHotkeyListener


def test_hotkey_listener_init():
    """HotkeyListener başlatma ve varsayılan durumunu test eder."""
    callback = MagicMock()
    listener = GlobalHotkeyListener(hotkey="ctrl+space", on_toggle=callback)
    assert listener.hotkey == "ctrl+space"
    assert not listener.is_active


def test_hotkey_listener_toggle_flip():
    """Toggle tetiklendiğinde durumun tersine döndüğünü ve callback'in çağrıldığını test eder."""
    callback = MagicMock()
    listener = GlobalHotkeyListener(hotkey="ctrl+space", on_toggle=callback)

    # 1. Basış -> Dinleme başlar (active=True)
    listener.trigger_toggle()
    assert listener.is_active
    callback.assert_called_once_with(True)

    # 2. Basış -> Dinleme biter (active=False)
    listener.trigger_toggle()
    assert not listener.is_active
    assert callback.call_count == 2
    callback.assert_called_with(False)
