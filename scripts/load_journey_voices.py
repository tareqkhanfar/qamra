"""Load the QR voices of «رحلتي الأولى للتعلّم» into storage: now `qamra_worker.journey_voices`, which ships in
the worker image (scripts/ does not) and reads the reviewed clips from content/journey/clips. On a server:

    docker compose exec worker python -m qamra_worker.journey_voices [--check]

Locally (with the .env's database and storage): `uv run python scripts/load_journey_voices.py [--check]
[DIR]`, DIR being a folder of <code>.mp3 + durations.json (default: content/journey/clips).
"""

import sys

from qamra_worker.journey_voices import main

if __name__ == "__main__":
    args = sys.argv[1:]
    folder = [a for a in args if not a.startswith("--")]
    sys.exit(main([a for a in args if a.startswith("--")] + (["--dir", folder[0]] if folder else [])))
