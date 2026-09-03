# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Make dependency-free gate modules importable exactly as direct scripts see them."""

from __future__ import annotations

import sys
from pathlib import Path


GATE_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(GATE_DIR))
