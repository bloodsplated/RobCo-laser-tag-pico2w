import runpy
import sys
import types

import pytest

import shared_utils


def _run_code(monkeypatch, *, gun_sn="ABC123", async_side_effect=None, async_return=None, debug_env=None):
    class _HW:
        def __init__(self):
            shared_utils.data().gun_sn = gun_sn
            self.cleaned = False

        async def async_start_all(self):
            if async_side_effect is not None:
                raise async_side_effect
            return async_return

        def cleanup(self):
            self.cleaned = True

    class _GL:
        pass

    fake_hw_mod = types.ModuleType("shared_hardware")
    fake_hw_mod.Hardware = _HW

    fake_gl_mod = types.ModuleType("shared_gamelogic")
    fake_gl_mod.GameLoader = _GL

    class _Micro:
        def __init__(self):
            self.reset_calls = 0

        def reset(self):
            self.reset_calls += 1

    class _Storage:
        def __init__(self):
            self.erase_calls = 0

        def erase_filesystem(self):
            self.erase_calls += 1

    micro = _Micro()
    storage = _Storage()

    monkeypatch.setitem(sys.modules, "shared_hardware", fake_hw_mod)
    monkeypatch.setitem(sys.modules, "shared_gamelogic", fake_gl_mod)
    monkeypatch.setitem(sys.modules, "microcontroller", micro)
    monkeypatch.setitem(sys.modules, "storage", storage)

    if debug_env is None:
        monkeypatch.delenv("DEBUG", raising=False)
    else:
        monkeypatch.setenv("DEBUG", debug_env)

    with pytest.raises(SystemExit) as exc:
        runpy.run_path("src/code.py")

    assert exc.value.code == 0
    return micro, storage


def test_code_runs_to_cleanup(monkeypatch):
    _run_code(monkeypatch, gun_sn="ABC123", async_return=None)




def test_code_invalid_serial_hits_exception_handler(monkeypatch):
    logs = {"error": []}
    monkeypatch.setattr(
        shared_utils.MyLogger,
        "error",
        lambda self, *parts: logs["error"].append(parts),
        raising=True,
    )

    _run_code(monkeypatch, gun_sn="A", async_return=None)

    assert any(parts and "[ERROR] in code.py" in str(parts[0]) for parts in logs["error"])


def test_code_generic_async_exception_hits_exception_handler(monkeypatch):
    logs = {"error": []}
    monkeypatch.setattr(
        shared_utils.MyLogger,
        "error",
        lambda self, *parts: logs["error"].append(parts),
        raising=True,
    )

    _run_code(monkeypatch, gun_sn="ABC123", async_side_effect=RuntimeError("boom"))

    assert any(parts and "[ERROR] in code.py" in str(parts[0]) for parts in logs["error"])


def test_code_exit_command_erase_filesystem(monkeypatch):
    micro, storage = _run_code(monkeypatch, gun_sn="ABC123", async_return="erase_filesystem")
    assert storage.erase_calls == 1
    assert micro.reset_calls == 1


def test_code_exit_command_hardware_reboot(monkeypatch):
    micro, storage = _run_code(monkeypatch, gun_sn="ABC123", async_return="hardware_reboot")
    assert storage.erase_calls == 0
    assert micro.reset_calls == 1
