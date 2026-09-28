"""Check and render a curriculum plan (run from the repository root).

python -m qamra_workbook.plan check kg2    # rule problems (exit 1 when any) and page counts
python -m qamra_workbook.plan render kg2   # also writes docs/workbook/plan-kg2.md and, in Arabic for the
                                           # educator, docs/workbook/educator-kg2.md
"""

import sys
from collections import Counter
from pathlib import Path

from qamra_workbook.curriculum import load, problems, render_educator, render_markdown

CURRICULUM_DIR = Path("content/workbook/curriculum")
DOCS_DIR = Path("docs/workbook")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] not in ("check", "render"):
        print(__doc__)
        return 2
    command, level = args
    source = CURRICULUM_DIR / f"{level}.yaml"
    plan = load(source)
    found = problems(plan)
    for v in plan.volumes:
        subjects = dict(Counter(p.subject for p in v.pages))
        print(f"V{v.volume}: {len(v.pages)} pages, {v.weeks} weeks, {subjects}")
    for line in found:
        print("✗", line)
    print(f"{len(found)} problem(s)")
    if command == "render":
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        for out, text in (
            (DOCS_DIR / f"plan-{level}.md", render_markdown(plan, str(source))),
            (DOCS_DIR / f"educator-{level}.md", render_educator(plan, str(source))),
        ):
            out.write_text(text, encoding="utf-8")
            print("wrote", out)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
