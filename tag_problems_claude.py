#!/usr/bin/env python
"""CLI for Claude tagging of olympiad problems (parallel provider to tag_problems.py).

Routes through the TrueFoundry gateway by default. Auth via ANTHROPIC_AUTH_TOKEN (Bearer),
model via CLAUDE_MODEL, endpoint via ANTHROPIC_BASE_URL — all read from the env or
backend/.env. Results are stored in `claude_metadata` (Gemini's data is untouched).

Examples:
  python tag_problems_claude.py --ids 1 2 3      # metered sample first
  python tag_problems_claude.py                  # all Claude-untagged problems
  CLAUDE_MODEL=claude-haiku-4-5 python tag_problems_claude.py   # cheaper model
"""

import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.ai_tagging.claude_tagger_service import main

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def main_cli():
    parser = argparse.ArgumentParser(
        description="Claude-powered problem tagging via an Anthropic-compatible gateway.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--ids", type=int, nargs="+", default=None,
                        help="Specific problem IDs to tag (default: all Claude-untagged).")
    parser.add_argument("--model", type=str, default=None,
                        help="Override CLAUDE_MODEL for this run.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    if args.model:
        os.environ["CLAUDE_MODEL"] = args.model

    try:
        result = asyncio.run(main(problem_ids=args.ids))
        sys.exit(0 if result.failed == 0 else 1)
    except KeyboardInterrupt:
        print("\n\nTagging interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
