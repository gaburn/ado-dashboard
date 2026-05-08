"""Bring the terminal window to the foreground.

Uses pure Win32 APIs (CreateToolhelp32Snapshot + EnumWindows + SetForegroundWindow)
to find and focus the terminal window hosting a given PID.  No PowerShell subprocess
is needed, so this completes in milliseconds instead of 2-3 seconds.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging

log = logging.getLogger(__name__)


def focus_terminal_by_pid(pid: int) -> tuple[bool, str]:
    """Bring the terminal window hosting *pid* to the foreground.

    Enumerates top-level windows to find one whose process tree
    contains *pid*, then calls SetForegroundWindow.
    """
    try:
        user32 = ctypes.windll.user32

        # Build the ancestor PID set using a process snapshot (pure Win32).
        ancestors = _get_ancestor_pids(pid)
        if not ancestors:
            return (False, f"Could not build ancestor chain for PID {pid}")

        log.debug("Ancestor PIDs for %d: %s", pid, ancestors)

        # Find a visible top-level window owned by any ancestor.
        found_hwnd = [0]  # mutable container for the callback

        @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        def _enum_callback(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True  # skip invisible windows
            window_pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if window_pid.value in ancestors:
                found_hwnd[0] = hwnd
                return False  # stop enumeration
            return True

        user32.EnumWindows(_enum_callback, 0)

        hwnd = found_hwnd[0]
        if not hwnd:
            return (False, f"No visible window found for PID {pid} or ancestors {ancestors}")

        # Restore the window if it was minimised.
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE

        # Alt-key trick: momentarily press Alt so Windows allows us to steal
        # foreground focus (bypasses the foreground-lock timeout).
        user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU (Alt) key down
        user32.keybd_event(0x12, 0, 2, 0)  # VK_MENU (Alt) key up

        ret = user32.SetForegroundWindow(hwnd)

        log.info("SetForegroundWindow(hwnd=%d) returned %d for PID %d", hwnd, ret, pid)
        return (True, f"Focused window (hwnd {hwnd})")

    except Exception as exc:
        log.warning("Failed to focus terminal for PID %d", pid, exc_info=True)
        return (False, f"Exception: {exc}")


def _get_ancestor_pids(pid: int) -> set[int]:
    """Return a set containing *pid* and all its ancestor PIDs.

    Uses CreateToolhelp32Snapshot for fast process enumeration (no PowerShell).
    """
    import ctypes.wintypes as wt

    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wt.DWORD),
            ("cntUsage", wt.DWORD),
            ("th32ProcessID", wt.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wt.DWORD),
            ("cntThreads", wt.DWORD),
            ("th32ParentProcessID", wt.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wt.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    kernel32 = ctypes.windll.kernel32

    # Take a snapshot of all processes.
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1:
        return set()

    try:
        # Build a parent map: child_pid -> parent_pid
        parent_map: dict[int, int] = {}
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)

        if kernel32.Process32First(snap, ctypes.byref(entry)):
            parent_map[entry.th32ProcessID] = entry.th32ParentProcessID
            while kernel32.Process32Next(snap, ctypes.byref(entry)):
                parent_map[entry.th32ProcessID] = entry.th32ParentProcessID
    finally:
        kernel32.CloseHandle(snap)

    # Walk up from pid, collecting every ancestor.
    ancestors: set[int] = set()
    current = pid
    for _ in range(20):  # safety limit to prevent infinite loops
        ancestors.add(current)
        parent = parent_map.get(current)
        if parent is None or parent == 0 or parent == current or parent in ancestors:
            break
        current = parent

    return ancestors
