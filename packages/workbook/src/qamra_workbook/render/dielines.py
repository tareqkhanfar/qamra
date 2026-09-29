"""Die lines for the insert sheets (Addendum 7 §6, §10): every cut line sits on its own layer.

A sheet's page templates mark each cut or kiss-cut outline with the class `cut` (an SVG shape, or an HTML box
whose border is the cut). The sheet is printed twice from the same HTML: once as the art (cut lines hidden)
and once as the die (only the cut lines), so the two align exactly. The die is then merged into the art PDF
as an optional-content layer «CutContour», which the printer switches off for the print plates and uses for
the cutter; `<name>-die.pdf` keeps the die on its own as well, for printers that want a separate file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    TextStringObject,
)

LAYER = "CutContour"
CUT = "#EC008C"  # the die line's color on screen (the printer's cut-contour convention)

# The art: every cut line hidden (the guide the child cuts along stays, as class `guide`).
ART_CSS = "<style>.cut { visibility: hidden !important; } .die-only { display: none !important; }</style>"
# The die: nothing but the cut lines, on a transparent page.
DIE_CSS = (
    "<style>html, body, .page { background: transparent !important; }"
    " .page, .page * { visibility: hidden !important; box-shadow: none !important; }"
    " .page .cut, .page .cut * { visibility: visible !important; }"
    " .art-only { display: none !important; }</style>"
)


def with_css(html: str, css: str) -> str:
    """The book's HTML with `css` added after its own stylesheet."""
    return html.replace("</head>", css + "</head>", 1)


def merge_layer(art_pdf: Path, die_pdf: Path, out: Path, name: str = LAYER) -> Path:
    """`art_pdf` with each page of `die_pdf` drawn on top as a form XObject in the optional-content group
    `name` (on by default, so a viewer shows the cut lines and the printer can switch them off)."""
    art, die = PdfReader(art_pdf), PdfReader(die_pdf)
    if len(art.pages) != len(die.pages):
        raise ValueError(f"{art_pdf.name} has {len(art.pages)} pages, its die {len(die.pages)}")
    writer = PdfWriter(clone_from=art)
    group = {NameObject("/Type"): NameObject("/OCG"), NameObject("/Name"): TextStringObject(name)}
    ocg = writer._add_object(DictionaryObject(group))
    for page, die_page in zip(writer.pages, die.pages, strict=True):
        form = DecodedStreamObject()
        form.set_data(_content_bytes(die_page))
        form.update(
            {
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Form"),
                NameObject("/BBox"): ArrayObject(die_page.mediabox),
                NameObject("/Resources"): die_page["/Resources"].clone(writer)
                if "/Resources" in die_page
                else DictionaryObject(),
                NameObject("/OC"): ocg,
            }
        )
        form_ref = writer._add_object(form)
        resources = page.setdefault(NameObject("/Resources"), DictionaryObject()).get_object()
        xobjects = resources.setdefault(NameObject("/XObject"), DictionaryObject()).get_object()
        xobjects[NameObject("/DieLine")] = form_ref
        # keep the art's own content untouched: wrap it in q … Q, then draw the die layer on top
        original = page.raw_get("/Contents")
        parts = original.get_object() if isinstance(original.get_object(), ArrayObject) else [original]
        page[NameObject("/Contents")] = ArrayObject(
            [_stream(writer, b"q\n"), *parts, _stream(writer, b"\nQ\nq /DieLine Do Q\n")]
        )
    writer._root_object[NameObject("/OCProperties")] = DictionaryObject(
        {
            NameObject("/OCGs"): ArrayObject([ocg]),
            NameObject("/D"): DictionaryObject(
                {
                    NameObject("/Name"): TextStringObject("Qamra"),
                    NameObject("/Order"): ArrayObject([ocg]),
                    NameObject("/ON"): ArrayObject([ocg]),
                }
            ),
        }
    )
    writer.compress_identical_objects()
    with out.open("wb") as fh:
        writer.write(fh)
    return out


def _content_bytes(page: Any) -> bytes:
    """A page's content, decoded (its /Contents may be one stream or an array of them)."""
    contents = page.get("/Contents")
    if contents is None:
        return b""
    contents = contents.get_object()
    streams = contents if isinstance(contents, ArrayObject) else [contents]
    return b"\n".join(x.get_object().get_data() for x in streams)


def _stream(writer: PdfWriter, data: bytes) -> Any:
    stream = DecodedStreamObject()
    stream.set_data(data)
    return writer._add_object(stream)


def layers(pdf: Path) -> list[str]:
    """The names of the optional-content layers of `pdf`."""
    root: Any = PdfReader(pdf).trailer["/Root"]
    props = root.get("/OCProperties")
    if props is None:
        return []
    return [str(g.get_object()["/Name"]) for g in props.get_object()["/OCGs"]]


def die_ink(pdf: Path, dpi: int = 50) -> list[float]:
    """How much of each page of a die PDF is inked (0–1): a die with nothing on it is a mistake."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf)
    out = []
    try:
        for page in doc:
            image = page.render(scale=dpi / 72, fill_color=(255, 255, 255, 255)).to_pil().convert("L")
            hist = image.histogram()
            out.append(1 - hist[255] / max(1, sum(hist)))
    finally:
        doc.close()
    return out
