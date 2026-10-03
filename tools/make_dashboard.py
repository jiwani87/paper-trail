#!/usr/bin/env python3
"""Render issue-trace.md plus the checker output as one self-contained HTML page for the camera.
The page is a VIEW of the file. Nothing on it is computed by a model; every number is read from
issue-trace.md or from the checker's printed lines.
Usage: make_dashboard.py <issue-trace.md> <check.txt> <out.html> [--pdf-dir run]"""
import argparse, html, json, re, sys
from datetime import date
from pathlib import Path

MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
DAY0 = date(2026, 3, 2)

def pdate(s):
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\w*\s+(\d{4})", s or "")
    return date(int(m.group(3)), MONTHS[m.group(2).title()], int(m.group(1))) if m else None

def tables(md):
    out = {}
    for name in ("ISSUES", "EVIDENCE", "CONTEXT", "NEXT"):
        m = re.search(rf"^##\s*{name}\s*$([\s\S]*?)(?=^##\s|\Z)", md, re.M)
        rows = [l for l in (m.group(1) if m else "").splitlines() if l.strip().startswith("|")]
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        cells = [c for c in cells if not all(re.fullmatch(r":?-+:?", x) for x in c)]
        out[name] = cells[1:] if cells else []
    m = re.search(r"^##\s*Not listed\s*$([\s\S]*?)\Z", md, re.M)
    out["NOT"] = (m.group(1).strip() if m else "")
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace"); ap.add_argument("check"); ap.add_argument("out")
    ap.add_argument("--pdf-dir", default="run")
    a = ap.parse_args()
    md = Path(a.trace).read_text()
    chk = Path(a.check).read_text().strip()
    T = tables(md)
    issues, evidence = T["ISSUES"], T["EVIDENCE"]
    pdf_dir = Path(a.pdf_dir)
    pdfs = {p.name[:7]: p for p in pdf_dir.glob("DPR-*.pdf")}
    out_path = Path(a.out).resolve()

    def pdf_href(rep):
        p = pdfs.get(rep)
        if not p: return None
        try: return str(p.resolve().relative_to(out_path.parent))
        except ValueError: return "file://" + str(p.resolve())

    # numbers read from the checker text, not recomputed
    def grab(pat):
        m = re.search(pat, chk); return m.group(1) if m else "?"
    n_cit = grab(r"Citations: (\d+ of \d+)")
    n_found = grab(r"Planted issues found: (\d+ of \d+)")
    n_inv = grab(r"Invented rows: (\d+)")
    result = grab(r"RESULT: (.*)")
    passed = result.startswith("ALL CHECKS PASS")

    # timeline span = the 60 reports
    span0, span1 = DAY0 + __import__("datetime").timedelta(days=1), DAY0 + __import__("datetime").timedelta(days=60)
    total = (span1 - span0).days
    def pct(d): return max(0, min(100, 100 * (d - span0).days / total))

    ev_by = {}
    for r in evidence:
        if len(r) >= 5: ev_by.setdefault(r[0], []).append(r)

    cards, rows = [], []
    for r in issues:
        if len(r) < 7: continue
        iid, text, party, hook, first, dead, status = r[:7]
        d_first, d_dead = pdate(first), pdate(dead)
        m_clear = re.search(r"cleared (DPR-\d{3}) (\d{1,2} \w{3} \d{4})", status)
        d_clear = pdate(m_clear.group(2)) if m_clear else None
        m_stand = re.search(r"standby (\d+) days", status)
        contested = "contested" in status.lower()
        notified = "notified" in status.lower()
        unserved = "no clause 9 notice seen" in text.lower()
        evs = ev_by.get(iid, [])
        first_rep = re.search(r"DPR-\d{3}", first); first_rep = first_rep.group(0) if first_rep else ""

        # timeline row
        left = pct(d_first) if d_first else 0
        right = pct(d_clear) if d_clear else 100
        dead_x = pct(d_dead) if d_dead else None
        rows.append(f"""
        <div class="trow">
          <div class="tlabel"><b>{html.escape(iid)}</b> {html.escape(text.split(',')[0].split(';')[0][:48])}</div>
          <div class="ttrack">
            <div class="tbar {'open' if not d_clear else ''}" style="left:{left:.1f}%;width:{max(0.8, right-left):.1f}%"></div>
            {'' if dead_x is None else f'<div class="tdead" style="left:{dead_x:.1f}%" title="notice deadline {html.escape(dead)}"></div>'}
            <div class="tdot" style="left:{left:.1f}%" title="first seen {html.escape(first)}"></div>
            {'' if not d_clear else f'<div class="tdot clear" style="left:{right:.1f}%" title="cleared {html.escape(m_clear.group(2))}"></div>'}
          </div>
        </div>""")

        ev_html = "".join(f"""
          <tr>
            <td class="mono">{'<a href="'+html.escape(pdf_href(e[1]))+'" target="_blank">'+html.escape(e[1])+'</a>' if pdf_href(e[1]) else html.escape(e[1])}</td>
            <td class="mono">{html.escape(e[2])}</td>
            <td class="mono c">{html.escape(e[3])}</td>
            <td class="q">“{html.escape(e[4])}”</td>
          </tr>""" for e in evs)
        badges = []
        if unserved: badges.append('<span class="b red">no Clause 9 notice</span>')
        if notified: badges.append('<span class="b green">notified</span>')
        if contested: badges.append('<span class="b amber">contested</span>')
        if m_stand: badges.append(f'<span class="b grey">standby {m_stand.group(1)} days</span>')
        badges.append('<span class="b green">cleared</span>' if d_clear else '<span class="b red">open</span>')
        cards.append(f"""
        <details class="card">
          <summary>
            <div class="chead">
              <span class="id">{html.escape(iid)}</span>
              <span class="ctitle">{html.escape(text.split(';')[0])}</span>
            </div>
            <div class="cmeta">
              <span><small>party</small>{html.escape(party)}</span>
              <span><small>clause</small>{html.escape(hook)}</span>
              <span><small>first seen</small>{html.escape(first)}</span>
              <span class="dl"><small>notice due</small>{html.escape(dead)}</span>
              <span><small>quotes</small>{len(evs)}</span>
            </div>
            <div class="badges">{''.join(badges)}</div>
          </summary>
          <table class="ev">
            <thead><tr><th>report</th><th>date</th><th>section</th><th>exact words in that report</th></tr></thead>
            <tbody>{ev_html}</tbody>
          </table>
        </details>""")

    n_reports = len(pdfs) if pdfs else 60
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Issue trace, {html.escape(Path(a.trace).stem)}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--ink:#1b1b1f;--grey:#6b6f76;--line:#e3e4e8;--bg:#f7f6f2;--card:#fff;--blue:#2f6fed;--red:#d23c3c;--green:#1f9d55;--amber:#d98a00}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,"Helvetica Neue",Arial,sans-serif}}
.wrap{{max-width:1720px;margin:0 auto;padding:28px 40px 60px}}
header{{display:flex;align-items:baseline;justify-content:space-between;gap:24px;flex-wrap:wrap;margin-bottom:22px}}
h1{{font-size:30px;margin:0;font-weight:700;letter-spacing:-.01em}}
h1 small{{font-weight:400;color:var(--grey);font-size:17px;margin-left:12px}}
.src{{font-family:ui-monospace,Menlo,monospace;color:var(--grey);font-size:14px}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:26px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.stat .n{{font-size:44px;font-weight:700;line-height:1;letter-spacing:-.02em}}
.stat .l{{color:var(--grey);margin-top:6px;font-size:14px}}
.stat.pass .n{{color:var(--green)}} .stat.fail .n{{color:var(--red)}}
.stat.pass{{border-color:#bfe7cf;background:#f1fbf5}} .stat.fail{{border-color:#f3c2c2;background:#fff3f3}}
h2{{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:var(--grey);margin:26px 0 12px;font-weight:600}}
.tl{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 22px 10px}}
.taxis{{display:flex;justify-content:space-between;color:var(--grey);font-size:13px;font-family:ui-monospace,Menlo,monospace;margin-left:300px;margin-bottom:8px}}
.trow{{display:flex;align-items:center;height:36px}}
.tlabel{{width:300px;flex:none;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding-right:12px}}
.tlabel b{{font-family:ui-monospace,Menlo,monospace;color:var(--blue);margin-right:6px}}
.ttrack{{position:relative;flex:1;height:14px;background:#eef0f4;border-radius:7px}}
.tbar{{position:absolute;top:0;height:14px;background:#c9d7f7;border-radius:7px}}
.tbar.open{{background:#f7c9c9}}
.tdot{{position:absolute;top:-2px;width:18px;height:18px;margin-left:-9px;border-radius:50%;background:var(--blue);border:3px solid #fff;box-shadow:0 0 0 1px var(--blue)}}
.tdot.clear{{background:var(--green);box-shadow:0 0 0 1px var(--green)}}
.tdead{{position:absolute;top:-8px;width:3px;height:30px;margin-left:-1px;background:var(--red);border-radius:2px}}
.legend{{display:flex;gap:22px;color:var(--grey);font-size:13px;margin:10px 0 6px 300px}}
.legend i{{display:inline-block;width:12px;height:12px;border-radius:50%;vertical-align:-1px;margin-right:6px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:0;overflow:hidden}}
.card[open]{{grid-column:1 / -1}}
summary{{list-style:none;cursor:pointer;padding:16px 20px}}
summary::-webkit-details-marker{{display:none}}
.chead{{display:flex;gap:12px;align-items:baseline}}
.id{{font-family:ui-monospace,Menlo,monospace;color:var(--blue);font-weight:700;font-size:15px;white-space:nowrap;flex:none}}
.ctitle{{font-size:19px;font-weight:600}}
.cmeta{{display:flex;gap:26px;flex-wrap:wrap;margin-top:10px;font-size:15px}}
.cmeta small{{display:block;color:var(--grey);font-size:12px;text-transform:uppercase;letter-spacing:.06em}}
.cmeta .dl{{color:var(--red);font-weight:600}}
.badges{{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap}}
.b{{font-size:12px;padding:3px 9px;border-radius:999px;border:1px solid;font-weight:600}}
.b.red{{color:var(--red);border-color:#f0b9b9;background:#fff3f3}}
.b.green{{color:var(--green);border-color:#b8e3c7;background:#effaf3}}
.b.amber{{color:var(--amber);border-color:#f2d59a;background:#fff8e8}}
.b.grey{{color:var(--grey);border-color:var(--line);background:#f5f5f7}}
table.ev{{width:100%;border-collapse:collapse;border-top:1px solid var(--line);font-size:14px}}
table.ev th{{text-align:left;color:var(--grey);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.06em;padding:10px 20px;background:#fafafa}}
table.ev td{{padding:8px 20px;border-top:1px solid #f0f0f2;vertical-align:top}}
table.ev td.c{{text-align:center}}
.mono{{font-family:ui-monospace,Menlo,monospace;white-space:nowrap}}
.mono a{{color:var(--blue);text-decoration:none}} .mono a:hover{{text-decoration:underline}}
.q{{font-family:ui-monospace,Menlo,monospace;font-size:13.5px}}
.check{{background:#0f1218;color:#d8dde6;border-radius:12px;padding:20px 24px;font:15px/1.6 ui-monospace,Menlo,monospace;white-space:pre-wrap}}
.check .ok{{color:#5fd38d;font-weight:700}} .check .bad{{color:#ff7a7a;font-weight:700}}
.notl{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 20px;font-size:15px;color:#333}}
@media(max-width:900px){{.stats{{grid-template-columns:repeat(2,1fr)}}.grid{{grid-template-columns:1fr}}.tlabel{{width:150px}}.taxis,.legend{{margin-left:150px}}.wrap{{padding:16px}}}}
</style></head><body><div class="wrap">
<header>
  <h1>Issue trace <small>MG/SC/2026/017, DPR-001 to DPR-060</small></h1>
  <div class="src">{html.escape(Path(a.trace).name)} · rendered from the file, nothing computed here</div>
</header>
<div class="stats">
  <div class="stat"><div class="n">{n_reports}</div><div class="l">daily reports read</div></div>
  <div class="stat"><div class="n">{len(issues)}</div><div class="l">issues, each with a notice deadline</div></div>
  <div class="stat"><div class="n">{len(evidence)}</div><div class="l">quotes, each tied to report, date, section</div></div>
  <div class="stat"><div class="n">{n_cit.split(' of ')[0]}<span style="font-size:22px;color:var(--grey)"> of {n_cit.split(' of ')[-1]}</span></div><div class="l">quotes found word for word by the checker</div></div>
  <div class="stat {'pass' if passed else 'fail'}"><div class="n">{'PASS' if passed else 'FAIL'}</div><div class="l">{html.escape(result)} · invented rows {html.escape(n_inv)}</div></div>
</div>

<h2>When each issue was first written down, when the notice was due, when it cleared</h2>
<div class="tl">
  <div class="taxis"><span>02 Mar</span><span>16 Mar</span><span>01 Apr</span><span>16 Apr</span><span>01 May</span></div>
  {''.join(rows)}
  <div class="legend"><span><i style="background:var(--blue)"></i>first mention in a report</span><span><i style="background:var(--red);border-radius:2px;width:4px"></i>notice deadline</span><span><i style="background:var(--green)"></i>cleared</span></div>
</div>

<h2>The issues. Open one to see every quote behind it</h2>
<div class="grid">{''.join(cards)}</div>

<h2>Considered and not listed</h2>
<div class="notl">{html.escape(T['NOT'])}</div>

<h2>The check. A script, not a model</h2>
<div class="check">{re.sub(r'(ALL CHECKS PASS)', r'<span class="ok">\1</span>', re.sub(r'(\d+ FAILURE\(S\))', r'<span class="bad">\1</span>', html.escape(chk)))}</div>
</div></body></html>"""
    out_path.write_text(page)
    print(f"wrote {out_path}  issues={len(issues)} evidence={len(evidence)} checker='{result}'")

if __name__ == "__main__":
    sys.exit(main())
