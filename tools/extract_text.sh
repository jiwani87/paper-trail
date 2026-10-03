#!/bin/sh
# Step 0: turn the PDFs in run/ into plain text the model reads in a few files instead of dozens.
# Uses pdftotext (poppler), and tesseract for OCR where a PDF has no readable text. Writes text/<name>.txt per PDF.
#
# A file whose NAME carries a date is a dated record (a daily report) and goes into a bundle,
# ten per bundle, in date order. Everything else (contract, programme, minutes, letters, emails)
# is left as its own .txt for the model to read whole. No file-naming convention is assumed:
# 2026-03-09, 09-03-2026, 09.03.2026 and 9 Mar 2026 all read as the same day.
set -e
RUN=${1:-run}; OUT=${2:-text}
rm -rf "$OUT"; mkdir -p "$OUT"
# pdftotext, or OCR for a PDF with no readable text layer (scans, custom-encoded fonts). See pdf_text.py.
python3 "$(dirname "$0")/pdf_text.py" "$RUN" "$OUT"
python3 - "$OUT" <<'PY'
import re, sys
from pathlib import Path
out = Path(sys.argv[1])
MON = {m.lower(): i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
def datekey(stem):
    s = stem.replace("_", " ")
    m = re.search(r"(20\d{2})[-./ ](\d{1,2})[-./ ](\d{1,2})", s)          # 2026-03-09
    if m: return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})[-./ ](\d{1,2})[-./ ](20\d{2})", s)          # 09-03-2026
    if m: return (int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(r"(\d{1,2})[-. ]([A-Za-z]{3})[a-z]*[-. ](20\d{2})", s)  # 9 Mar 2026
    if m: return (int(m.group(3)), MON[m.group(2).lower()], int(m.group(1)))
    return None
dated = sorted(((datekey(p.stem), p) for p in out.glob("*.txt") if datekey(p.stem)))
for i in range(0, len(dated), 10):
    b = out / f"bundle-{i//10+1:02d}.txt"
    b.write_text("".join(f"===== FILE: {p.name} =====\n{p.read_text()}\n" for _, p in dated[i:i+10]))
loose = [p for p in out.glob("*.txt") if not datekey(p.stem) and not p.name.startswith("bundle-")]
print(f"{len(dated)} dated reports in {(len(dated)+9)//10} bundles, {len(loose)} other documents read whole")
PY
