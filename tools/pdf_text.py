#!/usr/bin/env python3
"""Text out of a PDF, with OCR when the PDF has no usable text layer.

Two kinds of PDF defeat pdftotext. A scan or an image export has no text at all. A PDF built with
custom-encoded fonts (seen on the first real folder: Type 3 fonts from Nitro PDF) has text that
comes out as symbols. Both read fine to a person, so both are read from the page images instead:
pdftoppm renders each page at 300 dpi and tesseract reads it.

Readable is measured, not guessed. The share of tokens that look like words or numbers was 0.90
or more on every good file in the first real folder and in the dummy project, and 0.11 or less on
every broken one (22 Sep 2026). The cut is 0.5, halfway across that gap.

  pdf_text.py run text     write text/<name>.txt for every PDF in run/, OCR where needed
Used by extract_text.sh (step 0) and check_links.py, so a quote taken from OCR text is checked
against the same OCR text.
"""
import re, shutil, subprocess, sys, tempfile
from pathlib import Path

CUT = 0.5
WORDLIKE = re.compile(r"[(\[\"'“]?[A-Za-z0-9][A-Za-z0-9'’&/.,:;%°\-]*[)\]\"'”.,;:!?]?")
OCR_NOTE = "[OCR: this file had no readable text layer; read from page images, spelling may be off]\n"


def readable(text):
    toks = text.split()
    return bool(toks) and sum(1 for t in toks if WORDLIKE.fullmatch(t)) / len(toks) >= CUT


def ocr(pdf):
    if not shutil.which("tesseract") or not shutil.which("pdftoppm"):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "300", "-png", str(pdf), f"{tmp}/p"], check=True, capture_output=True)
        pages = sorted(Path(tmp).glob("p*.png"))
        out = [read_page(p) for p in pages]
    return "\n\f".join(out)


def tess(png):
    return subprocess.run(["tesseract", str(png), "-", "--psm", "6"], capture_output=True, text=True).stdout


def score(text):
    toks = text.split()
    return sum(1 for t in toks if WORDLIKE.fullmatch(t)) / len(toks) if toks else 0.0


def real_words(text):
    """How many tokens are dictionary words of 3+ letters. OCR noise off a sideways page is short
    letter runs ("Oe", "ee", "Sisy") that pass as word-like, so turns are compared on real words."""
    global _DICT
    if _DICT is None:
        d = Path("/usr/share/dict/words")
        _DICT = {w.strip().lower() for w in d.read_text().split()} if d.exists() else set()
    return sum(1 for t in re.findall(r"[A-Za-z]{3,}", text) if t.lower() in _DICT)


_DICT = None


def read_page(png):
    """OCR one page, the right way up. A page printed sideways (a landscape programme on a portrait
    sheet, seen on the first real folder) reads as noise, so all four turns are read and the one
    with the most real words is kept. Needs Pillow for the turns; without it, upright only."""
    best = tess(png)
    try:
        from PIL import Image
    except ImportError:
        return best
    for turn in (90, 180, 270):
        rot = png.with_name(f"{png.stem}-r{turn}.png")
        Image.open(png).rotate(turn, expand=True).save(rot)
        t = tess(rot)
        if real_words(t) > real_words(best):
            best = t
    return best


def renderings(pdf):
    """Every way this PDF reads as text. The page and the link check accept a quote found in any."""
    layer = [subprocess.run(["pdftotext", "-q"] + f + [str(pdf), "-"], capture_output=True, text=True).stdout
             for f in (["-layout"], [])]
    if readable(layer[0]):
        return layer, False
    o = ocr(pdf)
    return ([o] if o else layer), bool(o)


def main(run, out):
    out.mkdir(parents=True, exist_ok=True)
    done, failed = [], []
    for pdf in sorted(run.glob("*.pdf")):
        texts, used_ocr = renderings(pdf)
        body = texts[0]
        if used_ocr:
            body = OCR_NOTE + body
            done.append(pdf.name)
        elif not readable(body):
            failed.append(pdf.name)
        (out / (pdf.stem + ".txt")).write_text(body)
    for n in done:
        print(f"OCR     {n}")
    for n in failed:
        print(f"UNREAD  {n}  (no text layer and OCR unavailable: install tesseract and poppler)")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
