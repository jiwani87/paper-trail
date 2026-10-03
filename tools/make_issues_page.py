#!/usr/bin/env python3
"""The on-camera page. Design finalised with MJ on 12 Sep 2026, rules in DESIGN.md beside this folder's
SCOPE.md. Read DESIGN.md before changing anything visual. Drafted on the Claude Design canvas in design/.

Screen 1, "Issues": one card per issue. Title, SERVED / NOT SERVED, a bar from first seen to cleared
with the notice window in red when it was missed, the three dates, standby days when the trace records
them, party and clause. Three numbers top right: issues, notices not served, standby days.
Screen 2: the model's own sentence under the title, the contract strip (first seen, due, served or
not, reply or cleared, responsible), the calendar behind the count, then one row of three words,
CONTEXT · EVIDENCE · CORRESPONDENCE, and one panel under it. Context is on when the issue opens:
the model's own prose from the trace's CONTEXT table (skill Table 3), four to six sentences, one per
line, no references. Evidence, on request, is every report line in date order, each opening its DPR
PDF. Correspondence, on request, is every letter, email and delivery note the trace cites for the
issue (section 7 lines), in date order; an item opens letters/<REF>.pdf when that file exists.
Keys: C, E, R, Esc.

Everything is read from issue-trace.md. No checker on the page, and nothing checks the CONTEXT prose.
Usage: make_issues_page.py <issue-trace.md> <out.html> [--pdf-dir run] [--letters-dir letters]

SHORT is the only place the on-screen issue names are set. Change a value, re-run, done.
A missing id falls back to the Short title column of issue-trace.md, then to the text before the
first ";".
check_links.py imports load(): keep its keys id, lines, and each line's rep, q, pdf."""
import argparse, datetime as dt, html, json, re
from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_dashboard import tables, pdate

# On-screen issue names.
# Empty in the handover package: the approved names belong to the video's dummy project, and on
# anyone else's job they would sit over the wrong issues (found 22 Sep 2026 on the first real folder).
# Each issue takes its own words from issue-trace.md. The named list lives in demo/ and tools/.
SHORT = {}

def short_date(s):
    return re.sub(r" \d{4}$", "", s or "")

_MON = {m.lower(): i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}

END_WORDS = "cleared|complete|completed|resolved|instruction|delivered"

def end_clause(status):
    """How the issue ended, as the model wrote it: "cleared <report> <date>". The report name is
    whatever that project calls its reports, one word or five, so match to the date, not past it."""
    for clause in status.split(";"):
        m = re.search(rf"\b({END_WORDS})\b\s+(.*?\s+)?(\d{{1,2}} \w{{3}} \d{{4}})", clause.strip())
        if m: return m
    return None


def stem_head(stem):
    """The part of a file name before the date in it: DPR-007-2026-03-09 -> DPR-007."""
    t = stem.replace("_", " ")
    for pat in (r"(20\d{2})[-./ ](\d{1,2})[-./ ](\d{1,2})", r"(\d{1,2})[-./ ](\d{1,2})[-./ ](20\d{2})",
                r"(\d{1,2})[-. ]([A-Za-z]{3})[a-z]*[-. ](20\d{2})"):
        m = re.search(pat, t)
        if m: return stem[:m.start()].strip(" -_.")
    return ""


def stem_date(stem):
    """The day a document belongs to, read from its file name. 2026-03-09, 09-03-2026,
    09.03.2026 and 9 Mar 2026 all read as the same day. None when the name carries no date."""
    t = stem.replace("_", " ")
    m = re.search(r"(20\d{2})[-./ ](\d{1,2})[-./ ](\d{1,2})", t)
    if m: return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})[-./ ](\d{1,2})[-./ ](20\d{2})", t)
    if m: return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(r"(\d{1,2})[-. ]([A-Za-z]{3})[a-z]*[-. ](20\d{2})", t)
    if m: return dt.date(int(m.group(3)), _MON[m.group(2).lower()], int(m.group(1)))
    return None


def standby_range(status):
    """Read "standby 11 days, <first report> to <last report> (what stood idle)" out of the Status
    column. The report names are whatever the model cited, not a fixed pattern."""
    for clause in status.split(";"):
        m = re.search(r"standby (\d+) days,\s*(.+)$", clause.strip())
        if not m: continue
        rng, what = m.group(2).strip(), None
        mp = re.search(r"\((.*)\)\s*$", rng)
        if mp: what, rng = mp.group(1), rng[:mp.start()].strip()
        parts = [x.strip() for x in rng.split(" to ")]
        if len(parts) < 2: return None
        return dict(days=int(m.group(1)), **{"from": parts[0], "to": parts[-1]}, what=what)
    return None


def load(trace, pdf_dir, letters_dir="letters"):
    T = tables(Path(trace).read_text())
    # No file-naming convention assumed. Every PDF in the folder is addressable by its own name,
    # and a report's day is the date written in that name, in whatever order the project writes it.
    files = sorted(Path(pdf_dir).glob("*.pdf"))
    pdfs = {q.stem: "file://" + str(q.resolve()) for q in files}
    rep_dates = {q.stem: stem_date(q.stem) for q in files if stem_date(q.stem)}
    # A trace may cite a report by a shorter name than the file carries ("DPR-007" for
    # DPR-007-2026-03-09.pdf). Accept any such prefix, but only where it names one file and no other.
    alias = {}
    for q in files:
        d = stem_date(q.stem)
        head = stem_head(q.stem)
        if head and head != q.stem: alias.setdefault(head, []).append(q)
    for head, qs in alias.items():
        if len(qs) == 1 and head not in pdfs:
            pdfs[head] = "file://" + str(qs[0].resolve())
            if stem_date(qs[0].stem): rep_dates[head] = stem_date(qs[0].stem)
    rep_by_date = {d: r for r, d in rep_dates.items()}   # every day has a report; every calendar cell opens it
    # CONTEXT is one row per SENTENCE since 22 Sep: | ID | Sentence | Source |. Source names the
    # EVIDENCE citations that back it (`DPR-007 7; DPR-008 5`) or says `judgement` for a sentence that
    # is reasoning, or a statement that no document exists. An older two-column table still loads: the
    # whole context arrives as one row and is split into sentences with no sources.
    CTX = {}
    for r in T["CONTEXT"]:
        if len(r) >= 2: CTX.setdefault(r[0], []).append((r[1], r[2] if len(r) > 2 else None))
    # Skill Table 4: the next step the contract requires, in the model's words. Absent for an issue
    # until the trace carries a row for it (12 Sep: written for I-04 only, MJ's "build first for 1 event").
    NXT = {r[0]: dict(by=r[1], clause=r[2], text=r[3]) for r in T["NEXT"] if len(r) >= 4}
    ev = {}
    for r in T["EVIDENCE"]:
        if len(r) >= 5: ev.setdefault(r[0], []).append(dict(rep=r[1], date=r[2], sec=r[3], q=r[4], pdf=pdfs.get(r[1])))
    out = []
    for r in T["ISSUES"]:
        if len(r) < 7: continue
        iid, text, party, hook, first, dead, status = r[:7]
        short = r[7] if len(r) > 7 else ""      # Short title, the skill's 3-to-5-word name (added 22 Sep)
        party = party.split(" (")[0].strip()
        # The end of the issue, as the model wrote it: "cleared DPR-023 25 Mar 2026", "complete DPR-056 ...",
        # or "instruction MG-LTR-022 22 Mar 2026". The label on screen follows the word the model used.
        mc = end_clause(status)
        END = {"cleared": "Cleared", "complete": "Complete", "completed": "Complete", "resolved": "Resolved", "instruction": "Instructed", "delivered": "Delivered"}
        md = re.search(r"contested (\S+) (\d{1,2} \w{3} \d{4})", status)
        mn = re.search(r"notified (\S+) (\d{1,2} \w{3} \d{4})", status)
        ms = re.search(r"standby (\d+) days", status)
        # The model's findings: every clause of the status column that the strip and the calendar do not
        # already show. Cleared, contested, notified and standby are parsed into those; what is left is the
        # reasoning, "no Clause 9 notice served, VX-LTR-006 is a reminder", in the model's own words.
        parsed = [re.compile(p) for p in (
            r"\b(cleared|complete|completed|resolved|instruction|delivered)\b\s+(.*?\s+)?\d{1,2} \w{3} \d{4}",
            r"contested \S+ \d{1,2} \w{3} \d{4}", r"notified \S+ \d{1,2} \w{3} \d{4}", r"standby \d+ days")]
        findings = [s.strip() for s in status.split(";") if s.strip() and not any(p.search(s) for p in parsed)]
        findings = [f[0].upper() + f[1:] + ("" if f.endswith(".") else ".") for f in findings]
        no_standby = next((f for f in findings if re.match(r"^No (rig )?standby\b", f)), None)
        title = SHORT.get(iid) or short or text.split(";")[0].strip()
        first_date = first.split(",")[-1].strip()
        due = dead.split(",")[0].strip()
        due_clause = ",".join(dead.split(",")[1:]).strip().split(" (")[0]
        lines = sorted(ev.get(iid, []), key=lambda e: (pdate(e["date"]), int(re.search(r"\d", e["sec"]).group(0))))
        served_ref, served_date = (mn.group(1), mn.group(2)) if mn else (None, None)
        reply = None
        if served_ref:
            for e in lines:
                if e["sec"].strip() == "7" and f"Reply to {served_ref}" in e["q"]:
                    reply = dict(ref=e["q"].split()[0], date=e["date"]); break
        # The calendar behind the count. One cell per calendar day from first seen to cleared. Standby days
        # come from the trace's own "standby n days, DPR-aaa to DPR-bbb"; the count on screen is the number
        # of amber cells, so the arithmetic is visible. A day is clickable when a report line cites it.
        mr = standby_range(status)
        d0, d1, d2 = pdate(first_date), pdate(due), pdate(mc.group(3)) if mc else None
        d_end = d2 or max(rep_dates.values())
        sb_days = set()
        if mr:
            d_a, d_b = rep_dates.get(mr["from"]), rep_dates.get(mr["to"])
            if d_a and d_b:
                sb_days = {d for d in rep_dates.values() if d_a <= d <= d_b}
            if len(sb_days) != mr["days"]:
                print(f"WARNING {iid}: trace says standby {mr['days']} days but {mr['from']} to {mr['to']} spans {len(sb_days)} report days")
        by_day = {}
        for e in lines: by_day.setdefault(e["date"], e)
        cal, d = [], d0
        while d <= d_end:
            ds = d.strftime("%d %b %Y").lstrip("0")
            ds = d.strftime("%d %b %Y")
            cal.append(dict(d=d.strftime("%d %b"), dow=d.strftime("%a")[0], sb=d in sb_days, win=d1 is not None and d <= d1,
                            cite=by_day[ds]["rep"] if ds in by_day else None,
                            rep=rep_by_date.get(d), pdf=pdfs.get(rep_by_date.get(d)),
                            mark="first" if d == d0 else "cleared" if d == d2 else "served" if served_date and d == pdate(served_date) else "due" if d == d1 else None))
            d += dt.timedelta(1)
        # The correspondence on this issue: every section 7 line in date order, parsed as
        # "REF To|From PARTY subject Sent|Received". An item opens letters/<REF>.pdf when that file exists;
        # the others are listed and not clickable. Only a few letters are written (MJ, 12 Sep: "start with 2-3").
        corr = []
        for e in lines:
            if e["sec"].strip() != "7": continue
            m7 = re.match(r"^(\S+) (To|From) (\S+) (.+) (Sent|Received)(,.*)?$", e["q"])
            ref = m7.group(1) if m7 else e["q"].split()[0]
            # A reference looks like MG-LTR-021, VX-RFI-019, MG-EMAIL-14-03, MG-DN-0412. Anything else
            # is a section 7 line that is evidence but not a document, and listing it as one puts words
            # like "Nil." on screen under Correspondence.
            if not re.fullmatch(r"[A-Z]{2}-[A-Z]+-[0-9][\w-]*", ref):
                continue
            pdf = next((q for d in (Path(letters_dir), Path(pdf_dir))
                        if d.is_dir() for q in sorted(d.glob("*.pdf")) if ref in q.stem), None)
            corr.append(dict(ref=ref, date=e["date"], dir=(m7.group(2) + " " + m7.group(3)) if m7 else "",
                             subject=(m7.group(4) + (m7.group(6) or "")) if m7 else e["q"],
                             pdf=("file://" + str(pdf.resolve())) if pdf else None))
        corr.sort(key=lambda c: pdate(c["date"]))
        # The context: the model's own prose from the CONTEXT table (skill Table 3), one sentence per line.
        # No gate checks it against the reports; the EVIDENCE tab is the checked layer.
        rows_ctx = CTX.get(iid, [])
        if len(rows_ctx) == 1 and not rows_ctx[0][1]:
            rows_ctx = [(s.strip(), None) for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", rows_ctx[0][0]) if s.strip()]
        context = []
        for sent, src in rows_ctx:          # not `text`: that holds the issue's own line, used as the lede
            if not sent.strip(): continue
            says = [] if not src or src.strip().lower().startswith("judge") else src.split(";")
            srcs = []
            for cite in says:
                m = re.match(r"\s*(.+?)[\s,;:§·]+(\d+)\s*$", cite.strip())
                if not m: continue
                rep, sec = m.group(1).strip(), m.group(2)
                for e in ev.get(iid, []):
                    if e["rep"].strip() == rep and e["sec"].strip() == sec:
                        srcs.append(dict(d=e["date"], q=e["q"], pdf=e["pdf"]))
            context.append(dict(t=sent.strip(), think=bool(src) and not srcs, srcs=srcs))
        # The as-of clock, added 18 Sep with the date fix in SKILL.md.
        mdl = re.search(r"(\d+)\s+days?\s+left", status, re.I)
        mm = re.search(r"missed\s+(\d{1,2}\s+\w{3}\s+\d{4})", status, re.I)
        total = max((d2 - d0).days, 1) if d2 else None
        # A Deadline of n/a (no notice owed, or no notices clause in the folder) has no window to shade.
        red = 0 if served_ref or not total or d1 is None else min((min(d1, d2) - d0).days / total, 1)
        out.append(dict(id=iid, n=int(iid.split("-")[1]), title=title, party=party, hook=hook,
            clause=hook.split(",")[0].strip(), first=first, first_report=first.split(",")[0].strip(), first_date=first_date,
            due=due, due_clause=due_clause,
            # n/a deadline: no notice owed, or no notices clause in the folder. Neither is "not served".
            nodue=d1 is None,
            served=(served_ref + " " + served_date) if mn else None, served_ref=served_ref, served_date=served_date,
            served_in_time=bool(served_ref) and d1 is not None and pdate(served_date) <= d1,
            disputed=(md.group(1) + " " + md.group(2)) if md else None,
            cleared=mc.group(3) if mc else None, cleared_report=(mc.group(2) or "").strip() if mc else None, end_label=END[mc.group(1)] if mc else "Open",
            days_left=int(mdl.group(1)) if mdl else None, missed=mm.group(1) if mm else None,
            standby=int(ms.group(1)) if ms else 0, standby_range=(mr["from"] + " to " + mr["to"]) if mr else None,
            standby_what=mr["what"] if mr else None, no_standby=no_standby, desc=text.strip(), findings=findings, context=context, corr=corr,
            nxt=NXT.get(iid),
            span=(d_end - d0).days + 1, open=not d2, reply=reply, red=red, cal=cal, lines=lines))
    return out

CSS = """
:root{--bg:#faf8f3;--ink:#1c1917;--dim:#8a827a;--soft:#44403c;--line:#e7e2d9;--track:#ebe6dc;--red:#b91c1c;--green:#15803d;--amber:#a16207;--amber-fill:#e8cf9c;--link:#1d4ed8;--paper:#ffffff;--paperink:#1a1c20;--hi:#0b0a09;--quote:#332f2b}
html,body{margin:0;height:100%;overflow:hidden;background:var(--bg);color:var(--ink);font:18px/1.45 "IBM Plex Sans",-apple-system,"Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased}
.mono{font-family:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace}
/* The frame is always exactly 1920x1080 so a recording is pixel-for-pixel. --s shrinks it to fit
   a smaller window; at a 1920x1080 viewport --s is 1 and nothing is scaled.
   Centred by absolute positioning, not by grid: a grid track sizes itself to the 1920px item and
   then centres the item inside the track, not inside the window, which pushes it off to the right. */
.stage{position:absolute;left:50%;top:50%;width:1920px;height:1080px;
  transform:translate(-50%,-50%) scale(var(--s,1));transform-origin:center center}
.screen{position:absolute;inset:0;padding:40px 96px 48px;box-sizing:border-box;display:none;flex-direction:column;gap:18px}
.screen.on{display:flex}
.head{display:flex;justify-content:space-between;align-items:flex-end}
h1{font-size:48px;font-weight:600;margin:0;letter-spacing:-.01em;line-height:1.1}
.nums{display:flex;gap:40px;align-items:baseline}
.nums div{display:flex;flex-direction:column;align-items:flex-end;gap:2px}
.nums b{font-size:36px;font-weight:500}.nums small{font-size:14px;color:var(--dim)}
.nums .bad b{color:var(--red)}.nums .warn b{color:var(--amber)}.nums .dim b{color:var(--dim)}
/* Two ways to read the register: GRID, two columns of cards (the approved layout), and LIST, one issue
   per row with the same title, bar, dates and tag laid out across. Same content, one switch. */
.hr{display:flex;align-items:flex-end;gap:56px}
.views{display:flex;gap:4px;align-self:center;padding:3px;border:1px solid var(--line);border-radius:8px}
.vb{width:34px;height:30px;display:grid;place-items:center;border:0;border-radius:6px;background:none;cursor:pointer;padding:0}
.vb svg{width:18px;height:18px;fill:none;stroke:var(--dim);stroke-width:1.6;stroke-linecap:round}
.vb:hover svg{stroke:var(--hi)}
.vb.on{background:var(--track)}.vb.on svg{stroke:var(--ink)}
.grid.list{grid-template-columns:1fr;grid-auto-rows:1fr}
.grid.list .card{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr) minmax(0,1.25fr);column-gap:48px;row-gap:8px;align-items:center;align-content:center;padding:0}
.grid.list .card .top{gap:24px}
.grid.list .card .meta{grid-column:1}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-auto-rows:1fr;column-gap:72px;row-gap:0;flex:1;min-height:0}
.card{display:flex;flex-direction:column;gap:14px;padding:22px 0 22px;border-top:1px solid var(--line);cursor:pointer}
.card:hover .t{color:var(--hi)}
.card .top{display:flex;justify-content:space-between;align-items:center}
.card .t{font-size:23px;font-weight:500;letter-spacing:-.01em}
.tag{font-size:14px;letter-spacing:.06em}.tag.bad{color:var(--red)}.tag.ok{color:var(--green)}.tag.dim{color:var(--dim)}
.bar{display:flex;height:5px;border-radius:3px;overflow:hidden;background:var(--track)}
.bar i{display:block;background:var(--red)}
.dates{display:flex;justify-content:space-between;font-size:15px;color:var(--dim)}
.dates .bad{color:var(--red)}.dates .ok{color:var(--green)}
.meta{display:flex;gap:28px;font-size:16px;color:var(--soft)}
.back{color:var(--link);font-size:17px;cursor:pointer;align-self:flex-start}
.back:hover{color:var(--hi)}
.dh{display:flex;flex-direction:column;gap:12px}
.dh .row{display:flex;justify-content:space-between;align-items:center}
.dh .t{font-size:44px;font-weight:600;letter-spacing:-.015em;line-height:1.15}
.dh .lede{font-size:21px;line-height:1.4;color:var(--soft)}
/* Under the calendar, one row of three words: CONTEXT · EVIDENCE · n · THE NOTICE. One panel below it
   shows whichever is on. Context is on when the issue opens. Text only: ink when on, link blue when not. */
.tabs{display:flex;gap:48px;border-top:1px solid var(--line);padding-top:18px}
.tab{font-size:15px;letter-spacing:.08em;text-transform:uppercase;color:var(--link);cursor:pointer}
.tab:hover{color:var(--hi)}.tab.on{color:var(--ink);cursor:default}
/* On every tab the block from title to panel sits just above centre between the back link and the
   frame's bottom edge: two spacers share whatever height is free. When the panel is tall (the longest
   evidence list) there is no free height, the spacers are 0 and the block simply starts at the top.
   The panel's content fades in on each tab. */
.sp{flex:1 1 0;margin:-11px 0}
.sp:first-child{flex-grow:.85}
.panel{min-height:0;overflow:hidden}
.panel.in{animation:fade .3s ease}
@keyframes fade{from{opacity:0}to{opacity:1}}
.ctx{display:flex;flex-direction:column;gap:10px;font-size:19px;line-height:1.45;color:var(--ink);max-width:1400px}
.ctx>div{position:relative;padding-left:24px}
.ctx>div::before{content:"";position:absolute;left:0;top:.5em;width:8px;height:8px;border-radius:50%;border:1.5px solid var(--dim)}
.ctx .think{color:var(--dim)}
.ctx .line{cursor:default}
.ctx .line .proof{max-height:0;overflow:hidden;opacity:0;transition:max-height .15s,opacity .15s}
.ctx .line:hover .s{color:var(--hi)}
.ctx .line:hover .proof{max-height:240px;opacity:1;margin-top:9px}
.ctx .proof .p{display:flex;gap:18px;align-items:baseline;padding:3px 0 3px 22px;border-left:1px solid var(--line)}
.ctx .proof .d{font-size:14px;color:var(--dim);white-space:nowrap;min-width:64px}
.ctx .proof .q{font-size:18px;line-height:1.4;color:var(--quote);text-decoration:none}
a.q:hover{text-decoration:underline;text-decoration-color:var(--dim);text-underline-offset:4px}
.panel .lines.corr{column-count:1}
.l.off{cursor:default}.l.off small{color:var(--dim)}.l.off:hover .q{color:var(--quote)}
.strip{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.strip .warn b{color:var(--amber)}.strip .none b{color:var(--dim)}
.strip div{padding:13px 14px 13px 0;display:flex;flex-direction:column;gap:4px;min-width:0}
.strip small{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--dim)}
.strip b{font-size:18px;font-weight:500;white-space:nowrap;overflow:hidden}
.strip .bad b{color:var(--red)}.strip .ok b{color:var(--green)}
.panel .lines{display:block;column-count:2;column-gap:72px}
.panel .lines.three{column-count:3;column-gap:56px}
.cal{display:flex;flex-direction:column;gap:10px}
.cal .row{display:flex;justify-content:space-between;align-items:baseline}
.cal .sum{font-size:17px;color:var(--soft)}.cal .sum b{font-weight:500;color:var(--ink)}.cal .sum b.warn{color:var(--amber)}.cal .sum .none{color:var(--dim)}
.cal .key{display:flex;gap:22px;font-size:14px;color:var(--dim)}
.cal .key i{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:7px;vertical-align:-1px;background:var(--track)}
.cal .key i.sb{background:var(--amber-fill)}.cal .key i.win{background:var(--track);box-shadow:0 4px 0 var(--red)}
.strip2{display:flex;gap:3px}
.day{flex:1;display:flex;flex-direction:column;gap:6px;min-width:0}
.day i{display:block;height:26px;border-radius:2px;background:var(--track)}
.day.sb i{background:var(--amber-fill)}
.day.win i{box-shadow:0 4px 0 var(--red)}
/* Every cell opens its day's report (MJ 12 Sep: "every cell should link with a report"). The outline
   stays on the days the model cited, so the evidence days still read on the strip. */
.day.go{cursor:pointer}.day.cite i{outline:1px solid rgba(242,240,235,.25);outline-offset:-1px}.day.go:hover i{outline:1px solid var(--ink);outline-offset:-1px}
.day small{font-size:12px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:clip;text-align:center;height:14px}
.day small.m{color:var(--ink)}.day small.due{color:var(--red)}.day small.served{color:var(--green)}
.lines{padding:0}
.l{display:flex;flex-direction:column;gap:3px;padding:9px 0 11px;cursor:pointer;break-inside:avoid}
.l:hover .q{color:var(--hi)}
.l small{font-size:15px;color:var(--dim)}.l small.ok{color:var(--green)}
.l .q.ltr{color:var(--soft)}
.l .q{font-size:19px;line-height:1.4;color:var(--quote)}
"""

JS = r"""
const I = __DATA__;
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const sd = s => s ? s.replace(/ \d{4}$/, '') : '';
function show(id){ document.querySelectorAll('.screen').forEach(s => s.classList.toggle('on', s.id === id)); }
function fit(){ document.getElementById('stage').style.setProperty('--s',
  Math.min(window.innerWidth / 1920, window.innerHeight / 1080)); }
addEventListener('resize', fit); fit();
function view(v){ document.getElementById('cards').classList.toggle('list', v === 'list');
  document.querySelectorAll('.views .vb').forEach(t => t.classList.toggle('on', t.dataset.v === v));
  try { localStorage.setItem('issuesView', v); } catch (e) {} }
try { if (localStorage.getItem('issuesView') === 'list') setTimeout(() => view('list')); } catch (e) {}

const notServed = I.filter(i => !i.served && !i.nodue).length, noDue = I.filter(i => i.nodue).length, standby = I.reduce((a, i) => a + i.standby, 0);
document.getElementById('nums').innerHTML =
  `<div><b>${I.length}</b><small>Issues found</small></div>` +
  (noDue < I.length ? `<div class="bad"><b>${notServed}</b><small>Notice not served</small></div>` : '') +
  (noDue ? `<div class="dim"><b>${noDue}</b><small>No notice deadline</small></div>` : '') +
  (standby ? `<div class="warn"><b>${standby}</b><small>Standby days</small></div>` : '');

document.getElementById('cards').innerHTML = I.map((i, k) => {
  // Every dated event once, as label + date (MJ 12 Sep 13:33, "more clean"): the tag is the state with
  // its date when served, the middle slot is the due date only. "missed" and the letter ref came off;
  // the tag and the red bar already say missed, the ref lives on the correspondence tab.
  const tag = i.served ? `<span class="tag ok mono">SERVED ${sd(i.served_date)}</span>`
    : i.nodue ? `<span class="tag dim mono">NO DEADLINE</span>` : `<span class="tag bad mono">NOT SERVED</span>`;
  const mid = i.served || i.nodue ? `<span>Due ${sd(i.due)}</span>` : `<span class="bad">Due ${sd(i.due)}</span>`;
  // Party and clause came off the card (MJ 12 Sep 13:40: "unnecessary"); the strip on screen 2 names the
  // notice clause, the context prose names the party. Under the dates only the consequence, when there is one.
  const meta = i.standby ? `<div class="meta"><span>Standby ${i.standby} days</span></div>` : '';
  return `<div class="card" onclick="openIssue(${k})">
    <div class="top"><div class="t">${esc(i.title)}</div>${tag}</div>
    <div class="bar"><i style="width:${Math.round(i.red * 100)}%"></i></div>
    <div class="dates mono"><span>First seen ${sd(i.first_date)} · ${i.first_report}</span>${mid}<span class="${!i.cleared && i.missed ? 'bad' : ''}">${i.cleared ? i.end_label + ' ' + sd(i.cleared)
      : i.days_left != null ? 'Open · ' + i.days_left + ' days left'
      : i.missed ? 'Missed ' + sd(i.missed) : 'Open'}</span></div>
    ${meta}
  </div>`;
}).join('');

let cur = null;
const sentences = t => t.split(/(?<=[.!?])\s+(?=[A-Z])/).map(s => s.trim()).filter(Boolean);

function openIssue(k){ cur = k; const i = I[k];
  const strip = [
    `<div><small>Clock started</small><b class="mono">${i.first_date}</b></div>`,
    `<div><small>Notice due</small><b class="mono">${i.due}${i.due_clause ? ' · ' + esc(i.due_clause) : ''}</b></div>`,
    i.served ? `<div class="ok"><small>Served</small><b class="mono">${i.served_date} · ${i.served_in_time ? 'in time' : 'late'}</b></div>`
             : i.nodue ? `<div><small>Served</small><b class="mono">Unknown</b></div>`
             : `<div class="bad"><small>Served</small><b class="mono">Not served</b></div>`,
    i.reply ? `<div><small>Reply</small><b class="mono">${i.reply.date} · ${i.reply.ref}</b></div>`
            : i.disputed ? `<div><small>Contested</small><b class="mono">${i.disputed.split(' ').slice(1).join(' ')}</b></div>`
            : `<div><small>${i.cleared ? i.end_label : 'Status'}</small><b class="mono">${i.cleared || 'Open'}</b></div>`,
    // Impact = standby days from the trace, for now (MJ 12 Sep: "for now we write impact no. of days").
    `<div class="${i.standby ? 'warn' : 'none'}"><small>Impact</small><b class="mono">${i.standby} days</b></div>`
    // No NEXT cell (MJ 12 Sep 15:30: "dont show next in status line"); NEXT is a tab only.
  ].join('');   // no Responsible cell: the register card carries party and clause (MJ 12 Sep: "too detail")
  // No line above the strip (MJ 12 Sep: "status above gantt chart, extra info"). The days sit in the
  // strip's Impact cell; the amber cells and the key say the rest.
  const cal = `<div class="cal">
    <div class="row"><div></div><div class="key mono">${i.standby ? '<span><i class="sb"></i>standby day</span>' : ''}<span><i class="win"></i>notice window</span></div></div>
    <div class="strip2">${i.cal.map(c => `<div class="day${c.sb ? ' sb' : ''}${c.win ? ' win' : ''}${c.cite ? ' cite' : ''}${c.pdf ? ' go' : ''}"${c.pdf ? ` onclick="window.open('${c.pdf}','_blank')" title="${c.rep}"` : ''}><i></i><small class="mono${c.mark ? ' m ' + c.mark : ''}">${c.d}</small></div>`).join('')}</div>
  </div>`;
  // A context sentence carries the records it rests on. They stay closed until the reader hovers
  // the sentence, then open under it: the date, the words as the report writes them, and a click
  // through to that report. A sentence with no record behind it is reasoning and reads grey.
  const ctxRows = i.context.length ? i.context : [{t: i.desc, think: false, srcs: []}];
  const ctx = `<div class="ctx">` + ctxRows.map(c => c.think
      ? `<div class="think">${esc(c.t)}</div>`
      : !c.srcs.length ? `<div>${esc(c.t)}</div>`
      : `<div class="line"><div class="s">${esc(c.t)}</div><div class="proof">` + c.srcs.map(s =>
          `<div class="p"><span class="d mono">${esc(sd(s.d))}</span>` +
          (s.pdf ? `<a class="q" href="${esc(s.pdf)}" target="_blank">&ldquo;${esc(s.q)}&rdquo;</a>`
                 : `<span class="q">&ldquo;${esc(s.q)}&rdquo;</span>`) + `</div>`).join('') +
        `</div></div>`).join('') + `</div>`;
  // One entry per report since 22 Sep (MJ: "same DPR being repeated twice"): the report is named once
  // and every line quoted from it sits under that name. Lines stay open; Evidence is the proof tab.
  const byRep = [];
  i.lines.forEach(e => { let g = byRep.find(g => g.rep === e.rep);
    if (!g) { g = {rep: e.rep, date: e.date, pdf: e.pdf, qs: []}; byRep.push(g); }
    g.qs.push(e.q); });
  const ev = `<div class="lines${byRep.length > 6 ? ' three' : ''}">` + byRep.map(g =>
      `<div class="l" onclick="${g.pdf ? `window.open('${g.pdf}','_blank')` : ''}"><small class="mono">${g.rep} · ${g.date}</small>`
      + g.qs.map(q => `<div class="q${/^(VX|MG)-/.test(q) ? ' ltr' : ''}">${esc(q)}</div>`).join('') + `</div>`).join('') + `</div>`;
  const co = `<div class="lines corr">` + i.corr.map(c => `<div class="l${c.pdf ? '' : ' off'}"${c.pdf ? ` onclick="window.open('${c.pdf}','_blank')"` : ''}>`
    + `<small class="mono">${esc(c.ref)} · ${c.date} · ${esc(c.dir)}</small><div class="q">${esc(c.subject)}</div></div>`).join('') + `</div>`;
  const nx = i.nxt ? `<div class="ctx">` + sentences(i.nxt.text).map(s => `<div>${esc(s)}</div>`).join('') + `</div>` : '';
  PANELS = { context: ctx, evidence: ev, correspondence: i.corr.length ? co : '', next: nx };
  const tabs = `<div class="tabs"><span class="tab mono on" data-t="context" onclick="tab('context')">Context</span>`
    + `<span class="tab mono" data-t="evidence" onclick="tab('evidence')">Evidence</span>`
    + (i.corr.length ? `<span class="tab mono" data-t="correspondence" onclick="tab('correspondence')">Correspondence</span>` : '')
    + (i.nxt ? `<span class="tab mono" data-t="next" onclick="tab('next')">Next</span>` : '') + `</div>`;
  const body = document.getElementById('dbody');
  body.innerHTML = `<div class="sp"></div>
    <div class="dh"><div class="row"><div class="t">${esc(i.title)}</div>${i.served ? `<span class="tag ok mono">NOTICE SERVED · ${i.served_ref}</span>` : i.nodue ? `<span class="tag dim mono">NO NOTICE DEADLINE</span>` : `<span class="tag bad mono">NOTICE NOT SERVED</span>`}</div><div class="lede">${esc(i.desc)}</div></div>
    <div class="strip">${strip}</div>
    ${cal}${tabs}<div class="panel" id="panel">${ctx}</div><div class="sp"></div>`;
  show('detail'); }
let PANELS = {};
function tab(t){ if (!PANELS[t]) return;
  document.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x.dataset.t === t));
  const p = document.getElementById('panel'); p.innerHTML = PANELS[t];
  p.classList.remove('in'); void p.offsetWidth; p.classList.add('in'); }
addEventListener('keydown', e => { const on = document.querySelector('.screen.on').id;
  if (on === 'detail' && e.key === 'Escape') show('list');
  if (on === 'detail' && e.key === 'c') tab('context');
  if (on === 'detail' && e.key === 'e') tab('evidence');
  if (on === 'detail' && e.key === 'r') tab('correspondence');
  if (on === 'detail' && e.key === 'n') tab('next'); });
"""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("trace"); ap.add_argument("out")
    ap.add_argument("--pdf-dir", default="run"); ap.add_argument("--letters-dir", default="letters")
    a = ap.parse_args(); issues = load(a.trace, a.pdf_dir, a.letters_dir)
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Issues</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>__CSS__</style></head><body>
<div class="stage" id="stage">
<section class="screen on" id="list">
  <div class="head"><h1>Issues</h1><div class="hr"><div class="nums" id="nums"></div><div class="views"><button class="vb on" data-v="grid" onclick="view('grid')" aria-label="Grid view" title="Grid"><svg viewBox="0 0 20 20"><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="11" y="3" width="6" height="6" rx="1"/><rect x="3" y="11" width="6" height="6" rx="1"/><rect x="11" y="11" width="6" height="6" rx="1"/></svg></button><button class="vb" data-v="list" onclick="view('list')" aria-label="List view" title="List"><svg viewBox="0 0 20 20"><line x1="3" y1="5" x2="17" y2="5"/><line x1="3" y1="10" x2="17" y2="10"/><line x1="3" y1="15" x2="17" y2="15"/></svg></button></div></div></div>
  <div class="grid" id="cards"></div>
</section>
<section class="screen" id="detail">
  <a class="back mono" onclick="show('list')">← Issues</a>
  <div id="dbody" style="display:flex;flex-direction:column;gap:22px;min-height:0;flex:1"></div>
</section>
</div>
<script>__JS__</script></body></html>"""
    page = page.replace("__CSS__", CSS).replace("__JS__", JS.replace("__DATA__", json.dumps(issues)))
    Path(a.out).write_text(page)
    print("wrote", a.out, len(issues), "issues,", sum(1 for i in issues if i["context"]), "with context,",
          sum(1 for i in issues for c in i["corr"] if c["pdf"]), "of", sum(len(i["corr"]) for i in issues), "correspondence items open a PDF")

if __name__ == "__main__":
    main()
