#!/usr/bin/env python3
"""Gate for the on-camera claim: press a report line and the real DPR opens on that line.

check_trace.py proves a quote exists in the markdown source of the cited report and section.
This proves the different thing the page claims: the PDF each row actually links to exists,
and contains that row's line.

A PDF table survives text extraction two ways and neither alone covers both cases:
  -layout   keeps a table row on one line, but interleaves the columns when a cell wraps
  reflowed  joins a wrapped cell back together, but splits a table row
Both are renderings of the same document, so a quote found in either is present in the PDF.

Usage: check_links.py <issue-trace.md> [--pdf-dir run]
"""
import argparse, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_issues_page import load
from pdf_text import renderings

norm = lambda s: re.sub(r"\s+", " ", s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--pdf-dir", default="run")
    a = ap.parse_args()

    issues = load(a.trace, a.pdf_dir)
    cache, total, ok, missing = {}, 0, 0, 0
    for i in issues:
        for e in i["lines"]:
            total += 1
            if not e["pdf"]:
                missing += 1
                print(f"NO PDF   {i['id']} {e['rep']}")
                continue
            p = e["pdf"].replace("file://", "")
            if p not in cache:
                # Same text the model read: the text layer, or OCR where the PDF has none.
                cache[p] = [norm(t) for t in renderings(p)[0]]
            if any(norm(e["q"]) in t for t in cache[p]):
                ok += 1
            else:
                print(f"NOT IN PDF  {i['id']} {e['rep']} | {e['q'][:70]}")

    print(f"\n{ok} of {total} report lines open a PDF that contains that line.")
    print(f"{len(cache)} distinct PDFs checked, {len(issues)} issues.")
    print("\nWhat this cannot see: whether the line was filed under the right issue, and "
          "whether the PDF opens in the viewer's browser. It reads the file, it does not click.")
    bad = (total - ok) + missing
    print("RESULT: ALL LINKS RESOLVE" if bad == 0 else f"RESULT: {bad} FAILURE(S)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
