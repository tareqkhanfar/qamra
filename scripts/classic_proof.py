"""«قمرة كلاسيك» on the test server (Addendum 4 §9.3): templates from approved sample books; the cost proof.

It signs in like the ops client (password + TOTP from files in --creds: `ops-pw`, `ops-totp`) and only calls
admin endpoints. Every paid call happens on the server; this script never talks to an AI provider itself.

  python scripts/classic_proof.py --creds DIR status
  python scripts/classic_proof.py --creds DIR from-samples [BOOK_ID ...]   # approved sample books → templates
  python scripts/classic_proof.py --creds DIR generate --theme graduation  # or draw missing templates here
  python scripts/classic_proof.py --creds DIR texts [TEMPLATE_ID ...]      # vowelize the Arabic words once
  python scripts/classic_proof.py --creds DIR wait                         # until no template job runs
  python scripts/classic_proof.py --creds DIR publish TEMPLATE_ID ...      # approve (locks pages) + live
  python scripts/classic_proof.py --creds DIR proof --theme graduation     # 5 invented children → 5 books

`--offline` runs everything with placeholder art at no AI cost (a dry run of the flow). The children are
invented: their faces come from the configured image model's text-to-image prompt, never from a real person.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import pyotp

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"
EMAIL = "ops-bot@qamra.app"
# Addendum 4 plan §2.15: five invented children, two girls in hijab, one child with glasses
CHILDREN: list[dict[str, Any]] = [
    {"name": "سلمى", "gender": "f", "age": 5, "hijab": True, "skin": "light olive", "seed": 11},
    {"name": "ليان", "gender": "f", "age": 6, "hijab": True, "skin": "warm tan", "top": "yellow", "seed": 12},
    {"name": "يوسف", "gender": "m", "age": 5, "glasses": True, "hair": "black", "seed": 13},
    {
        "name": "آدم",
        "gender": "m",
        "age": 6,
        "skin": "deep brown",
        "hair": "black curly",
        "top": "green",
        "seed": 14,
    },
    {
        "name": "ريم",
        "gender": "f",
        "age": 5,
        "skin": "fair",
        "hair": "light brown wavy",
        "top": "pink",
        "seed": 15,
    },
]


def client(base: str) -> httpx.Client:
    return httpx.Client(base_url=base, headers={"X-Qamra-Client": "ops"}, timeout=120)


def login(c: httpx.Client, creds: Path) -> None:
    pw = (creds / "ops-pw").read_text().strip()
    r = c.post("/api/auth/login", json={"email": EMAIL, "password": pw})
    r.raise_for_status()
    if r.json().get("mfa_required"):
        secret = (creds / "ops-totp").read_text().strip()
        r = c.post("/api/auth/mfa/verify", json={"code": pyotp.TOTP(secret).now()})
        if r.status_code == 401:  # this 30 s code was already used: wait for the next one
            time.sleep(31 - time.time() % 30)
            r = c.post("/api/auth/mfa/verify", json={"code": pyotp.TOTP(secret).now()})
        r.raise_for_status()


def check(r: httpx.Response) -> Any:
    if r.status_code >= 400:
        sys.exit(f"{r.request.method} {r.request.url.path} → {r.status_code}: {r.text[:400]}")
    return r.json()


def usd_ils(c: httpx.Client) -> float:
    r = c.get("/api/admin/settings")
    if r.status_code == 200:
        for group in r.json()["groups"]:
            for s in group["settings"]:
                if s["key"] == "usd_ils":
                    return float(s["value"])
    return 3.70


def templates(c: httpx.Client) -> list[dict[str, Any]]:
    return list(check(c.get("/api/admin/classic/templates")))


def show(t: dict[str, Any]) -> None:
    print(
        f"{t['id']}  {t['theme']:<14} {t['style']:<11} {t['variant']:<11} {t['status']:<10} job={t['job']:<8}"
        f" pages={t['pages_drawn']}/{t['pages_total']} ${t['cost_usd']:.3f} {t['flags']}"
        + (" texts=ok" if (t.get("texts") or {}).get("vowelized") else " texts=missing")
        + (f" error={t['error']}" if t.get("error") else "")
    )


def wait_templates(c: httpx.Client) -> None:
    while True:
        busy = [t for t in templates(c) if t["job"] in ("queued", "running")]
        if not busy:
            break
        print(time.strftime("%H:%M:%S"), "working:", ", ".join(f"{t['theme']}/{t['variant']}" for t in busy))
        time.sleep(15)
    for t in templates(c):
        show(t)


def from_samples(c: httpx.Client, ids: list[str]) -> None:
    """Approved sample books (invented children, no drawn companion) → Classic templates in review."""
    if not ids:
        books = check(c.get("/api/admin/books", params={"view": "approved", "limit": 200}))
        ids = [b["id"] for b in books if b["is_sample"]]
    for book_id in ids:
        r = c.post(
            "/api/admin/classic/templates/from-book", json={"book_id": book_id, "synthetic_child": True}
        )
        if r.status_code == 409:
            print(book_id, "skipped:", r.json()["error"]["code"])
            continue
        t = check(r)
        print(book_id, "→ template", t["id"], t["theme"], t["variant"])
    wait_templates(c)


def generate(c: httpx.Client, theme: str, variants: list[str], offline: bool) -> None:
    """Draw the missing templates with the premium pipeline (about $2 each; skipped when one exists)."""
    have = {(t["theme"], t["style"], t["variant"]) for t in templates(c)}
    for variant in variants:
        if (theme, "watercolor", variant) in have:
            print(theme, variant, "exists")
            continue
        body = {"theme": theme, "style": "watercolor", "variant": variant, "offline": offline}
        t = check(c.post("/api/admin/classic/templates", json=body))
        print("drawing", t["id"], theme, variant)
    wait_templates(c)


def vowelize(c: httpx.Client, ids: list[str], refresh: bool) -> None:
    """Vowelize the Arabic texts of these templates (all of them when no ids): one Sonnet call per theme and
    gender, cached; templates made before this step existed need it once before they can be approved."""
    for t in templates(c):
        if ids and t["id"] not in ids:
            continue
        if t["texts"]["vowelized"] and not refresh:
            print(t["id"], t["theme"], t["variant"], "texts already vowelized")
            continue
        check(c.post(f"/api/admin/classic/templates/{t['id']}/texts", json={"refresh": refresh}))
        print(t["id"], t["theme"], t["variant"], "vowelizing")
    wait_templates(c)


def publish(c: httpx.Client, ids: list[str]) -> None:
    for tid in ids:
        t = check(c.get(f"/api/admin/classic/templates/{tid}"))
        if t["status"] == "draft":
            t = check(c.post(f"/api/admin/classic/templates/{tid}/status", json={"to": "in_review"}))
        if t["status"] == "in_review":
            t = check(c.post(f"/api/admin/classic/templates/{tid}/status", json={"to": "approved"}))
        if t["status"] == "approved":
            t = check(c.post(f"/api/admin/classic/templates/{tid}/status", json={"to": "live"}))
        show(t)


def face(c: httpx.Client, kid: dict[str, Any], offline: bool) -> bytes:
    if offline:
        return FIXTURE.read_bytes()  # a dry run spends nothing: the public-domain test face
    spec = {
        k: kid[k] for k in ("gender", "age", "hijab", "glasses", "skin", "hair", "top", "seed") if k in kid
    }
    face_id = check(c.post("/api/admin/classic/synthetic-faces", json=spec))["id"]
    for _ in range(60):
        r = c.get(f"/api/admin/classic/synthetic-faces/{face_id}")
        if r.status_code == 200:
            return r.content
        time.sleep(5)
    sys.exit(f"the invented face {face_id} was not drawn in 5 minutes (is the worker running?)")


def wait_book(c: httpx.Client, book_id: str) -> dict[str, Any]:
    while True:
        r = c.get(f"/api/admin/books/{book_id}")
        if r.status_code != 200:  # the API restarting (deploys): try again shortly
            time.sleep(15)
            continue
        d: dict[str, Any] = r.json()
        prog = d["generation"].get("progress") or {}
        print(time.strftime("%H:%M:%S"), d["status"], prog, f"${d['cost_usd']:.3f}", d["flags"], flush=True)
        if d["status"] != "generating":
            return d
        time.sleep(15)


def proof(c: httpx.Client, theme: str, out: Path, offline: bool, lang: str) -> None:
    """Five invented children, one Classic book each (final), their AI cost in ₪ and their PDFs."""
    rate = usd_ils(c)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for kid in CHILDREN:
        photo = face(c, kid, offline)
        (out / f"face-{kid['seed']}.png").write_bytes(photo)
        form = {
            "theme": theme, "name": kid["name"], "gender": kid["gender"], "age": str(kid["age"]),
            "hijab": str(kid.get("hijab", False)).lower(), "glasses": str(kid.get("glasses", False)).lower(),
            "consent": "true", "lang": lang, "mode": "final", "offline": str(offline).lower(),
        }  # fmt: skip
        files = [("photos", (f"face-{kid['seed']}.png", photo, "image/png"))]
        book_id = check(c.post("/api/admin/classic/samples", data=form, files=files))["book_id"]
        print(kid["name"], "→ book", book_id)
        d = wait_book(c, book_id)
        for name in ("interior.pdf", "cover.pdf", "proof.pdf"):
            r = c.get(f"/api/admin/books/{book_id}/files/{name}")
            if r.status_code == 200:
                (out / f"{kid['seed']}-{name}").write_bytes(r.content)
        ils = d["cost_usd"] * rate
        rows.append((kid["name"], d["status"], d["cost_usd"], ils, d["costs"], d["flags"]))
    print(f"\nAI cost per Classic book (usd_ils = {rate}):")
    for name, status, usd, ils, costs, flags in rows:
        verdict = "OK ≤ 2₪" if ils <= 2.0 else "OVER 2₪"
        print(f"  {name:<6} {status:<10} ${usd:.4f} = {ils:.2f}₪  {verdict}  {json.dumps(costs)}  {flags}")
    print(f"\nPDFs and faces in {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://62.84.179.155:3300")
    ap.add_argument("--creds", type=Path, required=True, help="folder with ops-pw and ops-totp")
    ap.add_argument("--offline", action="store_true", help="placeholder art, no AI cost")
    ap.add_argument("--theme", default="graduation")
    ap.add_argument("--lang", default="ar", choices=("ar", "en"))
    ap.add_argument("--variants", nargs="+", default=["girl", "girl_hijab", "boy"])
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "classic-proof")
    ap.add_argument("--refresh", action="store_true", help="texts: take the theme's current words first")
    ap.add_argument(
        "command", choices=("status", "from-samples", "generate", "texts", "wait", "publish", "proof")
    )
    ap.add_argument("ids", nargs="*", help="book ids (from-samples) or template ids (publish)")
    args = ap.parse_args()
    with client(args.base) as c:
        login(c, args.creds)
        if args.command == "status":
            for t in templates(c):
                show(t)
        elif args.command == "from-samples":
            from_samples(c, args.ids)
        elif args.command == "generate":
            generate(c, args.theme, args.variants, args.offline)
        elif args.command == "texts":
            vowelize(c, args.ids, args.refresh)
        elif args.command == "wait":
            wait_templates(c)
        elif args.command == "publish":
            publish(c, args.ids)
        else:
            proof(c, args.theme, args.out, args.offline, args.lang)


if __name__ == "__main__":
    main()
