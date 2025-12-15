#!/usr/bin/env python3
"""
Simple replay script - can be run from anywhere
Usage: python kurral/replay.py <kurral_id> [--artifacts-dir <dir>]
   or: python -m kurral.replay <kurral_id> [--artifacts-dir <dir>]
"""

import sys
from pathlib import Path

# Add project root to path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from kurral.agent_replay import replay_agent_artifact
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replay a Kurral artifact")
    parser.add_argument("kurral_id", nargs="?", help="Kurral ID (UUID) or partial UUID")
    parser.add_argument("--latest", action="store_true", help="Replay the latest artifact")
    parser.add_argument("--run-id", help="Replay by run_id")
    parser.add_argument("--artifacts-dir", type=Path, help="Path to artifacts directory (defaults to ./artifacts)")
    
    args = parser.parse_args()
    
    if args.latest:
        replay_agent_artifact(latest=True, artifacts_dir=args.artifacts_dir)
    elif args.run_id:
        replay_agent_artifact(run_id=args.run_id, artifacts_dir=args.artifacts_dir)
    elif args.kurral_id:
        replay_agent_artifact(kurral_id=args.kurral_id, artifacts_dir=args.artifacts_dir)
    else:
        print("Usage: python kurral/replay.py <kurral_id> [--artifacts-dir <dir>]")
        print("   or: python -m kurral.replay <kurral_id> [--artifacts-dir <dir>]")
        print("\nExample: python kurral/replay.py 810c48c1-fc9c-4ec4-a4f5-7fb7ed86506d")
        print("   or: python ../kurral/replay.py 810c48c1 (from level1agentK directory)")
