#!/usr/bin/env python
"""CLI script for running AI tagging of olympiad problems."""

import asyncio
import argparse
import sys
import logging
from typing import List

# Add backend to path
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.ai_tagging import main

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main_cli():
    """Parse CLI arguments and run tagging service."""
    parser = argparse.ArgumentParser(
        description="AI-powered problem tagging using Google Gemini API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Tag all untagged problems
  python tag_problems.py

  # Tag specific problems by ID
  python tag_problems.py --ids 1 5 12 99

  # Set custom batch size
  python tag_problems.py --batch-size 5

  # Set debug logging
  python tag_problems.py --debug
        """
    )
    
    parser.add_argument(
        "--ids",
        type=int,
        nargs="+",
        default=None,
        help="Specific problem IDs to tag (if not set, tags all untagged)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of problems per batch (default: 10)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Gemini API key (if not set, uses GEMINI_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Set API key if provided
    if args.api_key:
        os.environ["GEMINI_API_KEY"] = args.api_key
    
    # Run tagging
    try:
        result = asyncio.run(main(problem_ids=args.ids))
        
        # Exit with appropriate code
        sys.exit(0 if result.failed == 0 else 1)
    
    except KeyboardInterrupt:
        print("\n\nTagging interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
