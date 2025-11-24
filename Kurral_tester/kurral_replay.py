#!/usr/bin/env python3
"""
Lightweight wrapper for the Kurral replay CLI that lives entirely inside the
`Kurral_tester` package. Run this from any agent directory, e.g.:

    python ..\\Kurral_tester\\kurral_replay.py artifacts/<artifact_id>.kurral --verbose
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repository root is on sys.path so absolute imports work even when
# this script is executed from an agent folder.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Kurral_tester.cli.replay_cli import main


if __name__ == "__main__":
    main()

