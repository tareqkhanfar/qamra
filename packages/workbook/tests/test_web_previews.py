"""The activity books' web previews (scripts/export_workbook_previews.py) and details (showcase/copy.json)
cover every part the store sells: each level × volume, stage, volume and set picks a part with its cover, its
pages and its details, and every exported file exists. Mirrors `partKeys` in apps/web/src/lib/workbook.ts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "apps/web"
MANIFEST = json.loads((WEB / "src/lib/workbook-previews.json").read_text())
COPY = json.loads((WEB / "src/components/workbook/showcase/copy.json").read_text())
CATALOG = yaml.safe_load((ROOT / "content/store/catalog.yaml").read_text())
ISLAMIC_SETS = {"L1": ["V1", "V2"], "L2": ["V3", "V4", "V5"], "set": ["V1", "V2", "V3", "V4", "V5"]}
ACTIVITY = {"workbook", "journey", "family", "islamic"}


def sold_options(product: dict) -> list[dict[str, str]]:
    """The options of every variant the catalog inserts as active (the matrix of «دوسية التأسيس» included)."""
    if "variant_matrix" in product:
        matrix = product["variant_matrix"]
        return [
            {"level": level, "volume": str(row["volume"]), **{k: row[k] for k in ("interior", "format")}}
            for level in matrix["levels"]
            for row in matrix["rows"]
            if str(row["volume"]) == "set" or str(row["volume"]) in matrix["rendered"][level]
        ]
    return [
        {k: str(v) for k, v in variant["options"].items()}
        for variant in product.get("variants") or []
        if variant.get("active", True)
    ]


def part_keys(line: str, default: str, picks: dict[str, str]) -> tuple[list[str], str | None]:
    """The parts a pick shows and the set it names (None for one book), as the product page computes them."""
    if line == "workbook":
        level, volume = picks["level"], picks["volume"]
        if volume == "set":
            return [f"{level}-{v}" for v in ("1", "2", "3")], f"{level}-set"
        return [f"{level}-{volume}"], None
    if line == "journey":
        return (["1", "2", "3"], "set") if picks["stage"] == "set" else ([picks["stage"]], None)
    if line == "islamic":
        volume = picks["volume"]
        return (ISLAMIC_SETS[volume], volume) if volume in ISLAMIC_SETS else ([volume], None)
    return [default], None


PRODUCTS = [p for p in CATALOG["products"] if p["line"] in ACTIVITY and p.get("active", True)]


@pytest.mark.parametrize("product", PRODUCTS, ids=lambda p: p["slug"])
def test_every_variant_shows_its_own_pages_and_details(product: dict) -> None:
    slug, line = product["slug"], product["line"]
    previews, copy = MANIFEST[slug], COPY[slug]
    assert previews["default"] in previews["scopes"]
    variants = sold_options(product)
    assert variants
    for picks in variants:
        keys, set_key = part_keys(line, previews["default"], picks)
        for key in keys:
            assert key in previews["scopes"], f"{slug} {picks}: no pages for part {key}"
            assert key in copy["parts"], f"{slug} {picks}: no details for part {key}"
        if set_key is not None:
            assert set_key in copy["sets"], f"{slug} {picks}: no details for set {set_key}"


@pytest.mark.parametrize("slug", list(MANIFEST))
def test_every_exported_page_exists_with_its_captions(slug: str) -> None:
    for key, scope in MANIFEST[slug]["scopes"].items():
        assert 6 <= len(scope["pages"]) <= 10, f"{slug}/{key}: {len(scope['pages'])} pages"
        for page in [scope["cover"], *scope["pages"]]:
            for src in (page["src"], page["sm"]):
                assert (WEB / "public" / src.split("?")[0].lstrip("/")).is_file(), src
            assert page["title_ar"].strip() and page["title_en"].strip()
            assert page["w"] == 720 and page["h"] > page["w"]


@pytest.mark.parametrize("slug", list(COPY))
def test_details_are_complete_in_both_languages(slug: str) -> None:
    def lines(value: object) -> list[dict]:
        if isinstance(value, dict) and set(value) == {"ar", "en"}:
            return [value]
        if isinstance(value, list):
            return [x for v in value for x in lines(v)]
        if isinstance(value, dict):
            return [x for v in value.values() for x in lines(v)]
        return []

    for key, part in COPY[slug]["parts"].items():
        assert part["pages"] > 0 and part["topics"] and part["skills"] and part["included"], f"{slug}/{key}"
    for line in lines(COPY[slug]):
        assert line["ar"].strip() and line["en"].strip()
    if slug == "islamic-series":  # the series prints no audio codes (decisions 2026-10-07)
        text = json.dumps(COPY[slug], ensure_ascii=False)
        assert "QR" not in text and "صوت" not in text
