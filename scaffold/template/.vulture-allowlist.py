# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Vulture allow-list — names that vulture reports as unused but are NOT dead code.
#
# Vulture is a static analyzer: it cannot see names that are used only via a
# framework, serialization, dynamic dispatch, or a plugin entry point. Listing a
# name here marks it "used" so `vulture src/<module> .vulture-allowlist.py
# --min-confidence 80` stops flagging it.
#
# RULES
#   * Every entry MUST have a one-line reason. An unexplained suppression is
#     exactly how real dead code hides behind the gate.
#   * Prefer the narrowest form. Delete an entry the moment it no longer applies.
#   * Regenerate a first draft with:  uv run vulture src/<module> --make-whitelist
#
# The bare-name / attribute-access lines below are the vulture whitelist format:
# each reference counts as a "use" at parse time (vulture never executes this
# file). This file is excluded from ruff/mypy via pyproject so the bare names do
# not trip F821 / undefined-name.

# --- Pydantic v2 --------------------------------------------------------------
# Config and validators are invoked by pydantic's metaclass, never called by us.
model_config          # pydantic v2 model configuration attribute
field_validator       # decorated validators referenced by name at model build
model_validator       # whole-model validators, likewise framework-invoked
model_dump            # serialization entry point called by callers/tests only
model_dump_json       # JSON serialization entry point
cls                   # @classmethod validator receiver; a language binding, never dead code

# --- Gradio / web UI (only if this repo grows a UI) ---------------------------
# Event handlers and component callbacks are wired by the framework at runtime.
# demo                # top-level Blocks/Interface object launched by the server
# on_click            # button/event callbacks passed to .click(fn=...)

# --- pytest -------------------------------------------------------------------
# Fixtures and hookimpls are discovered by name; they look "unused" to vulture.
# pytest_configure    # pytest hook, called by the plugin manager
