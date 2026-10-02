"""«قلبي يعرف الله»: candidates for the hadith of the register, and the scholar's readable PDF (Addendum 10
§3, §4.9).

    uv run python scripts/islamic_sources.py fetch [--only ID ...] [--search ID] [--offline]
    uv run python scripts/islamic_sources.py scholar-pdf [--out out/islamic/sources-for-scholar.pdf]

`fetch` asks the open dataset named in sources.yaml (fawazahmed0/hadith-api through jsdelivr, one JSON per
hadith
number) for each hadith's Arabic text, checks that the `expect` keywords of the entry are in it (letters
only), and
writes content/islamic/candidates.json: a CANDIDATE for previews and for the scholar, never a printable
text. It
also trial-cuts the span of every dua. Nothing is invented: a reference that does not match is reported, never
swapped for another hadith. `--search ID` looks at the numbers around a mismatching hadith for the same hadith
(the collections' numbering schemes differ), to correct the NUMBER in the register by hand.

`scholar-pdf` writes one readable RTL entry per source with its reference, where it is planned, the grading
the
drafter claims, the scholar's questions, the candidate text with its provenance and sign-off boxes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qamra_workbook.islamic_sources import (
    CANDIDATES,
    COLLECTION_AR,
    REPO,
    Register,
    Resolver,
    Source,
    SourceError,
    Span,
    cut,
    letters,
    load,
    sha256,
)

URL = "https://cdn.jsdelivr.net/gh/{dataset}@1/editions/{edition}/{number}.json"
USER_AGENT = "qamra-islamic-sources/1 (candidate fetch for scholar review)"


class Offline(Exception):
    """The dataset host cannot be reached."""


def get_json(url: str, timeout: float = 25.0, tries: int = 3) -> dict[str, Any] | None:
    """The JSON at `url`; None when the host says 404; `Offline` when it cannot be reached."""
    last: Exception | None = None
    for _ in range(tries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data if isinstance(data, dict) else None
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None
            last = err
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as err:
            last = err
    raise Offline(str(last))


def entry_of(data: dict[str, Any], number: int) -> dict[str, Any] | None:
    """The hadith `number` of a dataset file: {"hadiths": [{hadithnumber, arabicnumber, text, grades,
    reference}]}."""
    rows = data.get("hadiths") or []
    return next((r for r in rows if r.get("hadithnumber") == number), rows[0] if rows else None)


def missing_keywords(text: str, expect: list[str]) -> list[str]:
    """The `expect` keywords that are not in `text`, on the letters only. A keyword's definite article is
    optional (a text may write «لِلْمَسَاكِينِ» where the keyword says «المساكين»)."""
    folded = letters(text)
    out = []
    for word in expect:
        key = letters(word)
        if key not in folded and not (key.startswith("ال") and len(key) > 4 and key[2:] in folded):
            out.append(word)
    return out


class Editions:
    """The dataset's whole-edition files, downloaded once and cached under out/islamic/cache/. A
    collection's file
    numbers can differ from its standard numbers (Sahih Muslim's files run 1..7563, while `arabicnumber` is
    the
    familiar 1..3033), so a hadith that is not at its own number is looked up by `arabicnumber` here."""

    def __init__(self, dataset: str) -> None:
        self.dataset = dataset
        self.folder = REPO / "out/islamic/cache"
        self._rows: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def rows(self, edition: str) -> list[dict[str, Any]]:
        with self._lock:
            if edition not in self._rows:
                cached = self.folder / f"{edition}.json"
                if cached.is_file():
                    data: dict[str, Any] | None = json.loads(cached.read_text("utf-8"))
                else:
                    url = f"https://cdn.jsdelivr.net/gh/{self.dataset}@1/editions/{edition}.json"
                    data = get_json(url, timeout=180.0)
                    if data is not None:
                        self.folder.mkdir(parents=True, exist_ok=True)
                        cached.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                self._rows[edition] = list((data or {}).get("hadiths") or [])
            return self._rows[edition]

    def by_arabic_number(self, edition: str, number: int) -> list[dict[str, Any]]:
        """Every entry whose `arabicnumber` is `number` (sub-reports «73.01» included), in book order."""
        out = []
        for row in self.rows(edition):
            arabic = row.get("arabicnumber")
            if arabic is not None and str(arabic).split(".")[0] == str(number):
                out.append(row)
        return out


def fetch_one(src: Source, register: Register, editions: Editions) -> dict[str, Any]:
    """The candidate entry for one hadith source (never raises except `Offline`). The hadith is first looked
    up at its own number; when that is not it and the collection numbers its files differently, by the
    standard number (`arabicnumber`) in the whole edition. The register's number is never changed."""
    assert src.hadith is not None
    corpus = register.corpus.hadith
    edition = corpus.editions.get(src.hadith.collection)
    base: dict[str, Any] = {
        "id": src.id,
        "kind": "hadith",
        "dataset": corpus.dataset,
        "edition": edition or "",
        "number": src.hadith.number,
        "dataset_number": None,
        "numbering": "",
        "text": "",
        "sha256": "",
        "grades": [],
        "missing": [],
        "note": "",
    }
    if edition is None:
        return {
            **base,
            "reference_check": "not_found",
            "note": f"collection {src.hadith.collection!r} is not in the dataset",
        }
    url = URL.format(dataset=corpus.dataset, edition=edition, number=src.hadith.number)
    data = get_json(url)
    row = entry_of(data, src.hadith.number) if data else None
    first = _candidate(src, base, row, url, "hadithnumber")
    if first["reference_check"] == "matched":
        return first
    same_scheme = row is not None and str(row.get("arabicnumber")) == str(row.get("hadithnumber"))
    if same_scheme:  # this collection's files are numbered as the book is: nowhere else to look
        return first
    for other in editions.by_arabic_number(edition, src.hadith.number):
        found = _candidate(
            src, base, other, f"{edition}.json (arabicnumber {other.get('arabicnumber')})", "arabicnumber"
        )
        if found["reference_check"] == "matched":
            return found
    return first


def _candidate(
    src: Source, base: dict[str, Any], row: dict[str, Any] | None, url: str, numbering: str
) -> dict[str, Any]:
    if not row or not str(row.get("text", "")).strip():
        return {
            **base,
            "reference_check": "not_found",
            "note": f"no hadith at {base['edition']}/{base['number']}",
            "url": url,
        }
    text = str(row["text"]).strip()
    missing = missing_keywords(text, src.expect)
    notes = []
    if not src.expect:
        notes.append("no `expect` keywords to check")
    if numbering == "arabicnumber":
        notes.append(f"found by its standard number (the dataset's file number is {row.get('hadithnumber')})")
    return {
        **base,
        "url": url,
        "dataset_number": row.get("hadithnumber"),
        "numbering": numbering,
        "text": text,
        "sha256": sha256(text),
        "grades": row.get("grades") or [],
        "reference": row.get("reference") or {},
        "reference_check": "mismatch" if missing else "matched",
        "missing": missing,
        "note": "; ".join(notes),
    }


def trial_dua(src: Source, entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The trial extraction of a dua's span from its hadith's candidate text."""
    assert src.dua is not None
    base: dict[str, Any] = {
        "id": src.id,
        "kind": "dua",
        "from": src.dua.from_,
        "text": "",
        "sha256": "",
        "missing": [],
    }
    parent = entries.get(src.dua.from_)
    if parent is None or parent.get("reference_check") != "matched":
        why = (
            "its hadith is not in the register"
            if parent is None
            else f"its hadith is {parent.get('reference_check')}"
        )
        return {**base, "reference_check": "not_found", "note": why}
    try:
        words, starts = cut(parent["text"], Span(src.dua.start, src.dua.end))
    except SourceError as err:
        return {**base, "reference_check": "mismatch", "note": str(err)}
    note = f"the start marker matches {starts} places; the first is used" if starts > 1 else ""
    return {**base, "text": words, "sha256": sha256(words), "reference_check": "matched", "note": note}


def run_fetch(args: argparse.Namespace) -> int:
    register = load()
    wanted = set(args.only or [])
    hadith = [s for s in register.of_kind("hadith") if not wanted or s.id in wanted]
    previous = json.loads(CANDIDATES.read_text("utf-8")).get("entries", {}) if CANDIDATES.is_file() else {}
    entries: dict[str, dict[str, Any]] = dict(previous)
    if args.offline:
        print("offline: nothing fetched; candidates.json is unchanged")
        return 0
    unreachable: list[str] = []
    editions = Editions(register.corpus.hadith.dataset)

    def job(src: Source) -> tuple[Source, dict[str, Any] | None]:
        try:
            return src, fetch_one(src, register, editions)
        except Offline:
            return src, None

    with ThreadPoolExecutor(max_workers=8) as pool:
        for src, entry in pool.map(job, hadith):
            if entry is None:
                unreachable.append(src.id)
            else:
                entries[src.id] = entry
    if len(unreachable) == len(hadith) and hadith:
        print(f"offline: cannot reach {URL.split('/gh/')[0]}; candidates.json is unchanged")
        return 0
    for src in register.of_kind("dua"):
        if not wanted or src.id in wanted or (src.dua and src.dua.from_ in wanted):
            entries[src.id] = trial_dua(src, entries)
    known = {s.id for s in register.sources}
    entries = {k: v for k, v in entries.items() if k in known}  # a source removed from the register goes too
    payload = {
        "version": 1,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset": register.corpus.hadith.dataset,
        "note": (
            "CANDIDATES from an open dataset: for previews and the scholar's review. Never printed "
            "before approval."
        ),
        "entries": dict(sorted(entries.items())),
    }
    CANDIDATES.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print_table(register, entries, wanted, unreachable)
    return 0


def print_table(
    register: Register, entries: dict[str, dict[str, Any]], wanted: set[str], unreachable: list[str]
) -> None:
    rows = [["id", "kind", "reference", "check", "note"]]
    counts: Counter[tuple[str, str]] = Counter()
    for src in register.sources:
        e = entries.get(src.id)
        if (
            src.kind not in ("hadith", "dua")
            or e is None
            or (wanted and src.id not in wanted and e.get("from") not in wanted)
        ):
            continue
        if src.kind == "hadith":
            assert src.hadith is not None
            ref = f"{src.hadith.collection} {src.hadith.number}"
        else:
            assert src.dua is not None
            ref = f"from {src.dua.from_}"
        note = e.get("note", "")
        if e.get("missing"):
            note = "missing: " + "، ".join(e["missing"]) + (f"; {note}" if note else "")
        counts[(src.kind, e["reference_check"])] += 1
        rows.append([src.id, src.kind, ref, e["reference_check"], note])
    widths = [max(len(r[i]) for r in rows) for i in range(4)]
    for r in rows:
        print("  ".join(c.ljust(w) for c, w in zip(r[:4], widths, strict=True)), r[4])
    for kind in ("hadith", "dua"):
        got = {k: n for (kd, k), n in counts.items() if kd == kind}
        print(f"{kind}: " + ", ".join(f"{k} {n}" for k, n in sorted(got.items())))
    if unreachable:
        print(f"unreachable (kept the previous candidate, if any): {', '.join(unreachable)}")
    print(f"wrote {CANDIDATES.relative_to(REPO)}")


def run_search(args: argparse.Namespace) -> int:
    """The numbers around a hadith that contain its keywords: the same hadith under another numbering."""
    register = load()
    src = register.get(args.search)
    if src.hadith is None:
        print("--search takes a hadith id")
        return 1
    edition = register.corpus.hadith.editions.get(src.hadith.collection)
    if edition is None:
        print(f"collection {src.hadith.collection!r} is not in the dataset")
        return 1
    found = 0
    for number in range(max(1, src.hadith.number - args.window), src.hadith.number + args.window + 1):
        try:
            data = get_json(
                URL.format(dataset=register.corpus.hadith.dataset, edition=edition, number=number)
            )
        except Offline as err:
            print(f"offline: {err}")
            return 0
        row = entry_of(data, number) if data else None
        if row and not missing_keywords(str(row["text"]), src.expect):
            found += 1
            print(f"{edition}/{number}: {str(row['text'])[:230]}")
    print(f"{found} number(s) within ±{args.window} contain {src.expect}")
    return 0


# ---- the scholar's PDF ----------------------------------------------------------------------------------

ST_AR = {
    "proposed": "مقترح",
    "text_candidate": "نصّ مرشَّح",
    "text_verified": "نصّ موثَّق",
    "scholar_approved": "معتمد من المشرف",
}
KIND_AR = {"quran": "قرآن", "hadith": "حديث", "dua": "ذكر/دعاء", "sira": "سيرة", "ruling": "حكم"}
GROUP_AR = {
    "quran": "القرآن الكريم",
    "hadith": "الأحاديث الشريفة",
    "dua": "الأذكار والأدعية",
    "sira": "السيرة النبوية (مرجع يسمّيه المشرف)",
    "ruling": "أحكام مبسّطة (بلا نصّ خاص)",
}
_HINDI = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
MAX_WHERE = 6


def ar(value: object) -> str:
    return str(value).translate(_HINDI)


def planned(resolver: Resolver) -> dict[str, list[str]]:
    """Where each source is planned: the sample pages and every page of the volumes (through `islamic.load`),
    a dua also counting for its hadith and a ruling for its basis."""
    from qamra_workbook import islamic
    from qamra_workbook.islamic_checks import chain, load_pages, page_ids
    from qamra_workbook.islamic_sources import SAMPLES

    out: dict[str, list[str]] = {}

    def add(source_id: str, label: str) -> None:
        for each in chain(resolver, source_id):
            if label not in out.setdefault(each, []):
                out[each].append(label)

    if SAMPLES.is_file():
        for page in load_pages(SAMPLES):
            for source_id in page_ids(page):
                add(source_id, f"صفحة نموذجية {page['id']}")
    plan = islamic.load()
    for vid, pages in plan.pages.items():
        volume = plan.volumes[vid].get("title_ar", vid)
        for plan_page in pages:
            unit = plan.units.get(plan_page.unit or "", {}).get("title_ar", "")
            for source_id in plan_page.sources:
                label = (
                    f"{volume} · ص {ar(plan_page.n)} · {unit} "
                    f"{('— ' + plan_page.title) if plan_page.title else ''}"
                ).strip()
                add(source_id, label)
    return out


def reference_line(resolver: Resolver, src: Source) -> str:
    reg = resolver.register
    if src.quran:
        q = src.quran
        span = f"الآية {ar(q.from_)}" if q.from_ == q.to else f"الآيات {ar(q.from_)}–{ar(q.to)}"
        return f"القرآن الكريم · سورة رقم {ar(q.surah)} · {span}"
    if src.hadith:
        h = src.hadith
        line = f"{COLLECTION_AR.get(h.collection, h.collection)} · حديث رقم {ar(h.number)}"
        cand = resolver.candidates.get(src.id)
        if cand and cand.numbering == "arabicnumber":
            line += f" (الترقيم المعتاد للكتاب؛ رقم الملف في مجموعة البيانات {ar(cand.dataset_number)})"
        return line
    if src.dua:
        parent = reg.by_id[src.dua.from_]
        return f"مقتطف من الحديث «{parent.title_ar}» ({parent.id})"
    if src.kind == "ruling":
        return "حكم مبسّط بلا نصّ خاص: المرجع في «مبنيّ على»، ويسمّي المشرف الصيغة"
    return "لا مرجع بعدُ: يسمّي المشرف المصدر (واقعة من السيرة)"


def entry_for(resolver: Resolver, src: Source, where: dict[str, list[str]]) -> dict[str, Any]:
    reg = resolver.register
    cand = resolver.candidates.get(src.id)
    got = resolver.resolve(src.id) if not (src.dua and not resolver.candidates.get(src.dua.from_)) else None
    entry: dict[str, Any] = {
        "id": src.id,
        "title": src.title_ar,
        "kind": KIND_AR[src.kind],
        "status": got.status if got else src.status,
        "status_ar": ST_AR[got.status if got else src.status],
        "reference": reference_line(resolver, src),
        "cut": "",
        "basis": "؛ ".join(f"{reg.by_id[b].title_ar} ({b})" for b in src.basis if b in reg.by_id),
        "where": (
            where.get(src.id, [])[:MAX_WHERE]
            + (
                [f"… و{ar(len(where[src.id]) - MAX_WHERE)} موضعًا آخر"]
                if len(where.get(src.id, [])) > MAX_WHERE
                else []
            )
        ),
        "grading": src.grading_claimed,
        "dataset_grades": "؛ ".join(
            f"{g.get('name', '')}: {g.get('grade', '')}" for g in (cand.grades if cand else ()) if g
        ),
        "decision": src.scholar_decision if not src.decided else "",
        "text_kind": "none",
        "text": "",
        "lines": (),
        "provenance": "",
        "check_bad": False,
        "check_note": "",
        "pending": "",
    }
    if src.dua:
        entry["cut"] = (
            f"علامة البداية «{src.dua.start}» · علامة النهاية «{src.dua.end}» (للبحث فقط، لا تُطبعان)"
        )
    if src.kind in ("sira", "ruling"):
        entry["pending"] = (
            "لا نصّ لهذا البند: تُطبع الشروح المبسّطة فقط (وسمها «مُعدّة آليًّا») بعد أن يسمّي المشرف "
            "المصدر ويعتمد الصيغة."
        )
        return entry
    if src.kind == "quran":
        if got and got.text is not None:
            entry.update(text_kind="quran", lines=got.lines, provenance=got.provenance)
        else:
            entry["pending"] = (
                "ملف طنزيل الرسمي لم يُضَف إلى المستودع بعدُ؛ يُنسخ النصّ منه حرفيًّا عند الطباعة، ولا "
                "يُكتب من الذاكرة."
            )
        return entry
    parent_cand = resolver.candidates.get(src.dua.from_) if src.dua else cand
    if cand is None and not (src.dua and parent_cand):
        entry["pending"] = "لم يُجلب نصّ مرشَّح بعدُ (`scripts/islamic_sources.py fetch`)."
        return entry
    shown = cand.text if cand and cand.text else ""
    if got is not None and got.text is not None:
        entry.update(text_kind="candidate", text=got.text, provenance=got.provenance)
    elif cand is not None and cand.reference_check == "mismatch" and shown:
        missing = "، ".join(cand.missing)
        entry.update(
            text_kind="candidate",
            text=shown,
            check_bad=True,
            check_note=f"الكلمات المتوقعة غير موجودة: {missing}",
        )
        entry["provenance"] = f"{cand.dataset} · {cand.edition} · {cand.dataset_number or cand.number}"
    elif cand is not None and cand.reference_check == "mismatch":
        entry.update(text_kind="candidate", text="", check_bad=True, check_note=cand.note)
    else:
        why = (cand.note if cand else "") or "لم يُعثر على النصّ في مجموعة البيانات"
        entry["pending"] = f"لم يُعثر على نصّ مرشَّح ({why}). يُنسخ من المصدر المعتمد."
    return entry


def build_pdf_context(resolver: Resolver) -> dict[str, Any]:
    from qamra_workbook.islamic_checks import load_pages, scholar_queue
    from qamra_workbook.islamic_sources import SAMPLES, STATUSES, TEXT_KINDS

    where = planned(resolver)
    reg = resolver.register
    pages = load_pages(SAMPLES) if SAMPLES.is_file() else []
    groups = []
    for kind in ("quran", "hadith", "dua", "sira", "ruling"):
        rows = [entry_for(resolver, s, where) for s in reg.of_kind(kind)]
        if rows:
            groups.append({"title": GROUP_AR[kind], "entries": rows})
    summary = []
    for kind in ("quran", "hadith", "dua", "sira", "ruling"):
        have = [sum(1 for s in reg.of_kind(kind) if resolver.status_of(s.id) == st) for st in STATUSES]
        if sum(have):
            summary.append(
                {
                    "kind": GROUP_AR[kind].split(" (")[0],
                    "counts": [ar(n) for n in have],
                    "total": ar(sum(have)),
                }
            )
    hadith = [c for c in resolver.candidates.values() if c.kind == "hadith"]
    counts = Counter(c.reference_check for c in hadith)
    names = {"matched": "مطابق", "mismatch": "غير مطابق", "not_found": "غير موجود"}
    queue = [
        {
            "source": d.source,
            "question": d.question,
            "where": "؛ ".join(where.get(d.source, [])[:3]) or "المجلّدات",
        }
        for d in scholar_queue(resolver, pages)
    ]
    quran = resolver.quran
    return {
        "fonts": (REPO / "packages/pdf/src/qamra_pdf/fonts").as_uri(),
        "generated": ar(datetime.now(UTC).strftime("%Y/%m/%d")),
        "statuses": [{"ar": ST_AR[s]} for s in STATUSES],
        "summary": summary,
        "hadith_total": ar(len(reg.of_kind("hadith"))),
        "candidates_line": "، ".join(f"{names[k]} {ar(n)}" for k, n in sorted(counts.items()))
        or "لم تُجلب بعدُ",
        "quran_line": f"موجود: {quran.name}"
        if quran
        else "غير موجود بعدُ: تُطبع الآيات كمربّعات مميَّزة حتى يُضاف",
        "queue": [type("D", (), q) for q in queue],
        "groups": groups,
        "text_kinds": sorted(TEXT_KINDS),
    }


def run_pdf(args: argparse.Namespace) -> int:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    from qamra_pdf import html_to_pdf

    resolver = Resolver.load()
    env = Environment(
        loader=FileSystemLoader(REPO / "scripts/templates"), autoescape=select_autoescape(["html", "j2"])
    )
    html = env.get_template("islamic-scholar.html.j2").render(**build_pdf_context(resolver))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    footer = (
        '<div style="width:100%;font:8px sans-serif;color:#585C72;text-align:center">'
        'Qamra · مصادر للمراجعة العلمية · <span class="pageNumber"></span> / <span '
        'class="totalPages"></span></div>'
    )
    asyncio.run(html_to_pdf(html, args.out, footer=footer))
    print(f"wrote {args.out.relative_to(REPO)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="hadith candidates from the open dataset")
    fetch.add_argument("--only", nargs="+", metavar="ID", help="fetch only these ids")
    fetch.add_argument(
        "--search", metavar="ID", help="look around a mismatching hadith's number for the same hadith"
    )
    fetch.add_argument(
        "--window", type=int, default=30, help="with --search: numbers to look at on each side"
    )
    fetch.add_argument("--offline", action="store_true", help="do not touch the network")
    pdf = sub.add_parser("scholar-pdf", help="the readable PDF for the scholar")
    pdf.add_argument("--out", type=Path, default=REPO / "out/islamic/sources-for-scholar.pdf")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "fetch":
            return run_search(args) if args.search else run_fetch(args)
        return run_pdf(args)
    except SourceError as err:
        print(f"✗ {err}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
