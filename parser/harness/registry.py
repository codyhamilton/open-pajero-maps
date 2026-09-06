"""Check discovery: import every module in `parser/harness/checks/` and
collect its module-level `CHECKS` list. Ordering is by module name, then
list order within the module -- deterministic regardless of filesystem
iteration order, and stable as later units add more `checks/*.py` modules
without editing this file."""
from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import checks as checks_pkg
from harness.context import Check


def discover() -> list[Check]:
    all_checks: list[Check] = []
    module_infos = sorted(pkgutil.iter_modules(checks_pkg.__path__), key=lambda m: m.name)
    for mod_info in module_infos:
        module = importlib.import_module(f"harness.checks.{mod_info.name}")
        module_checks = getattr(module, "CHECKS", [])
        all_checks.extend(module_checks)
    return all_checks
