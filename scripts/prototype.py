"""Phase 0 prototype command, kept for the original CLI (CLAUDE.md §9). It now runs the Addendum 3 pipeline.

  uv run scripts/prototype.py --photo kid.jpg --name "سلمى" --gender f --age 5 \\
      --theme first-day --style watercolor --lang ar [--provider fal|gemini|openai|sketch|fake]

Same as `scripts/sample_book.py` (which has more options: --hijab, --glasses, --mode, --message …).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sample_book import main

if __name__ == "__main__":
    sys.exit(main())
