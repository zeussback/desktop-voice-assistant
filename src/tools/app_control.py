"""Application launch and process termination tool for Windows."""

import functools
import glob
import logging
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional
import psutil
from src.tools.base import BaseTool, ConfirmationPolicy, ToolResult

logger = logging.getLogger(__name__)

# Common Windows built-in aliases
BUILTIN_APPS = {
    "hesap makinesi": "calc.exe",
    "hesap": "calc.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "not defteri": "notepad.exe",
    "notepad": "notepad.exe",
    "dosya gezgini": "explorer.exe",
    "explorer": "explorer.exe",
    "komut istemi": "cmd.exe",
    "cmd": "cmd.exe",
    "terminal": "wt.exe",
    "görev yöneticisi": "taskmgr.exe",
    "task manager": "taskmgr.exe",
    "paint": "mspaint.exe",
}


def _clean_app_name(name: str) -> str:
    """Normalize app name by stripping Turkish suffixes (e.g. spotify'ı -> spotify)."""
    clean = name.strip().lower()
    # Remove common Turkish accusative / dative suffixes ('ı, 'i, 'u, 'ü, 'yı, 'yi, vb.)
    clean = re.sub(r"['’](?:i|ı|u|ü|yi|yı|yu|yü|e|a|ye|ya)$", "", clean)
    # Also strip punctuation
    clean = clean.strip(".,;:!?\"'")
    return clean


@functools.lru_cache(maxsize=1)
def _find_start_menu_shortcuts() -> List[str]:
    """Scan Windows Start Menu directories for .lnk shortcuts."""
    paths = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%LocalAppData%\Programs"),
    ]
    shortcuts = []
    for p in paths:
        if os.path.exists(p):
            for file_path in glob.glob(os.path.join(p, "**", "*.lnk"), recursive=True):
                shortcuts.append(file_path)
    return shortcuts


def _resolve_app_path(app_name: str) -> Optional[str]:
    """Find the executable or shortcut path for a given application name."""
    clean_name = _clean_app_name(app_name)

    # 1. Built-in common applications
    if clean_name in BUILTIN_APPS:
        target = BUILTIN_APPS[clean_name]
        if shutil.which(target):
            return target
        return target

    # 2. Check system PATH
    found = shutil.which(clean_name) or shutil.which(f"{clean_name}.exe")
    if found:
        return found

    # 3. Search Start Menu shortcuts
    shortcuts = _find_start_menu_shortcuts()
    # Exact base match
    for sc in shortcuts:
        base = os.path.splitext(os.path.basename(sc))[0].lower()
        if base == clean_name:
            return sc

    # Substring match (e.g. "spotify" in "Spotify.lnk", "chrome" in "Google Chrome.lnk")
    for sc in shortcuts:
        base = os.path.splitext(os.path.basename(sc))[0].lower()
        if clean_name in base:
            return sc

    return None


class AppControlTool(BaseTool):
    """Launches or terminates Windows applications."""

    name = "control_application"
    description = (
        "Bilgisayarda yüklü olan masaüstü uygulamalarını açar veya çalışan "
        "uygulamaları kapatır (sonlandırır)."
    )
    confirmation_policy = ConfirmationPolicy.IMMEDIATE

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "action": {
                        "type": "STRING",
                        "description": "Uygulama eylemi: 'launch_app' (aç) veya 'close_app' (kapat)",
                        "enum": ["launch_app", "close_app"]
                    },
                    "app_name": {
                        "type": "STRING",
                        "description": "Açılacak veya kapatılacak uygulamanın adı (örn: 'Spotify', 'Chrome', 'Not Defteri', 'Discord')."
                    }
                },
                "required": ["action", "app_name"]
            }
        }

    def _launch(self, app_path: str) -> None:
        """Launch the application path."""
        try:
            os.startfile(app_path)
        except Exception:
            subprocess.Popen([app_path], shell=True)

    def _terminate_process(self, clean_name: str) -> int:
        """Find and terminate running processes matching the name. Returns count terminated."""
        terminated_count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pname = (proc.info.get('name') or '').lower()
                # Check match against clean_name
                # e.g. "spotify.exe", "chrome.exe", "code.exe"
                if clean_name in pname or pname.startswith(clean_name):
                    proc.terminate()
                    terminated_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return terminated_count

    def execute(
        self,
        action: str,
        app_name: Optional[str] = None,
        **kwargs: Any
    ) -> ToolResult:
        if not app_name or not app_name.strip():
            return ToolResult(
                success=False,
                message="Lütfen bir uygulama adı belirtiniz efendim."
            )

        clean_name = _clean_app_name(app_name)

        try:
            if action == "launch_app":
                target_path = _resolve_app_path(clean_name)
                if not target_path:
                    logger.warning(f"Application not found: {app_name} (clean: {clean_name})")
                    return ToolResult(
                        success=False,
                        message=f"Efendim, '{app_name}' uygulamasını bilgisayarınızda bulamadım."
                    )

                logger.info(f"Launching {app_name} via {target_path}")
                self._launch(target_path)
                return ToolResult(
                    success=True,
                    message=f"'{app_name}' uygulaması açıldı efendim.",
                    data={"app_name": app_name, "path": target_path}
                )

            elif action == "close_app":
                logger.info(f"Terminating processes matching {clean_name}")
                count = self._terminate_process(clean_name)
                if count > 0:
                    return ToolResult(
                        success=True,
                        message=f"'{app_name}' uygulaması kapatıldı efendim.",
                        data={"app_name": app_name, "processes_terminated": count}
                    )
                else:
                    return ToolResult(
                        success=False,
                        message=f"Efendim, '{app_name}' uygulaması şu anda zaten çalışmıyor."
                    )

            else:
                return ToolResult(
                    success=False,
                    message=f"Bilinmeyen uygulama eylemi: '{action}' efendim."
                )

        except Exception as e:
            logger.error(f"AppControlTool hatası: {e}", exc_info=True)
            return ToolResult(
                success=False,
                message=f"'{app_name}' uygulaması yönetilirken bir hata oluştu efendim: {str(e)}"
            )
