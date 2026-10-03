---
name: dpr-trace
description: Turn a folder of Daily Progress Reports plus the subcontract into a traceable issue register (issue-trace.md). Use when the user says trace the DPRs, build the issue register, find the notice clocks, or run the trace on run/.
---

# DPR trace

You are reading a project's daily progress reports and its contract, for one of the parties to it (see
**Acting for** below). You produce one file,
`issue-trace.md`, that a script will check line by line. Every claim you make must point at the exact
report, date, section and words it came from. A citation that lands on the wrong words fails the whole row.

## Inputs

`run/` is the folder the user points you at. Read everything in it and nothing outside it. It holds the
contract or subcontract, the programme or scope document, the daily reports, and whatever else the user
keeps there: minutes of meeting, letters, emails, transmittals, delivery notes. File names are the user's,
not a fixed list. Daily reports are the files whose names carry a date. Cite every document by its own
file name, exactly as it is written, because that is what the page links back to.

**Step 0, before reading anything:** run `sh tools/extract_text.sh run text` (pdftotext, no model). It writes
`text/` with one .txt per PDF, plus `text/bundle-01.txt` onward holding ten daily reports each in date order,
every report headed `===== FILE: <the file's own name>.txt =====`. Read the text files, not the PDFs.

Read the contract and the programme first, in full. The programme dates define when a permit, an access or a
free-issue delivery was due. Then read every bundle in order, then every remaining .txt in `text/` that no
bundle covers, which is where minutes, letters and emails land. Keep a running list of open issues as you go.
Do not skip a bundle and do not skip a loose file.

**The as-of date.** If `run/AS-OF.txt` exists, its first line is today's date and you judge every deadline
against it. If it does not exist, use today's real date. State the date you used in one line at the top of
`issue-trace.md`, as `As of: dd Mon yyyy`.

**Acting for.** If `run/ACTING-FOR.txt` exists, its first line names the party you act for. If it does not
exist, read the parties' names from the contract and ask the user which one they act for, in one question
that lists the names. Do not work it out from letterheads or from who wrote the reports. Write the answer to
`run/ACTING-FOR.txt`. If there is no one to ask, stop and say that `run/ACTING-FOR.txt` is needed. State it on
the second line of `issue-trace.md`, as `Acting for: <name as the contract gives it>`. `AS-OF.txt` and
`ACTING-FOR.txt` are settings, not documents: never cite them.

## What counts as an issue

An issue is an event or circumstance that the contract makes the other party responsible for, or that
the contract requires the party you act for to notify. Typical: a permit not delivered,
access not given, free-issue material late, ground different from the geotechnical report, a third party
obstructing the works.

Plant trouble with an outside cause is an issue. Where the same part fails or is replaced again and again,
or output falls far below plan, and anything in `run/` describes the ground or conditions it was working in
(the reports, a rate schedule, a geotechnical report, a letter), list it under that condition. Quote the plant
entries and whatever describes the ground. If nothing in `run/` records the ground as different from what the
contract assumed, list it anyway and say so in Status as `ground not recorded`; the user decides, not you.

Not an issue, never list it: the own resourcing of the party you act for (leave, its own late supplies, a
one-off breakdown with no outside cause);
weather that does not meet the contract's weather clause in full; routine correspondence (meetings,
inductions, payment applications, hold points); anything you cannot quote from a report.

## Rules that decide the dates

1. **First seen = the day a report first mentions the issue.** Not the day it first costs money, not the day
   the crew starts waiting, not the day the contractual due date passed. If a report mentions it, then goes
   silent, then mentions it again, first seen is the first mention.
2. **Deadline = first seen + the notice period in the contract**, stated with the clause. If a different
   clause with a shorter period applies (for example ground conditions), use that one and say so.
3. **A DPR entry is not a notice.** Read the notices clause. If no written notice under that clause appears
   in the correspondence sections, the deadline stands unserved.
3a. **Unserved is not the same as missed, and the as-of date is what separates them.** An unserved deadline
   that falls on or after the as-of date is still `open`, and you say how many days are left. An unserved
   deadline that fell before the as-of date is `missed dd Mon yyyy`. Judge this against the as-of date, never
   against the date of the last report you happened to read: a window can close on a day nobody wrote a report.
4. **Standby**: count the full days a rig or crew is recorded idle for a cause the contract puts on the other
   party. The reports never count this themselves; you do, from the equipment and delays sections, and you
   show which reports the count comes from.
5. **Contested**: if the main contractor's comments dispute a fact within the period in the contemporary
   records clause, mark the row contested and cite the comment.
6. **Cleared**: if a later report records the issue resolved, give that report and the date.
7. **A notice the contract itself turns into the entitlement is the whole requirement.** Where the contract
   says a notice of some event (different ground, for example) makes it a variation, no separate notice of
   claim is owed for it. Do not record one as missing, and do not say time or money was lost.
8. **A report that contradicts itself is flagged, not settled.** When one report says two things that cannot
   both be true (the notes blame high wind, the weather box on the same report records no wind hours), do
   not drop the event on either side. List it, quote both, and add `conflict in report: <the two things>` to
   Status. The user decides which one holds.

## Output: `issue-trace.md`, four pipe tables, exactly these columns

Table 1, `## ISSUES`, one row per issue, in first-seen order:

| ID | Issue | Responsible party | Contract hook | First seen | Deadline | Status | Short title |
|---|---|---|---|---|---|---|---|

- ID: I-01, I-02, ...
- Issue: one line, plain site words.
- Contract hook: clause and Division of Responsibility row, e.g. `PC 4.1, R-2`.
- First seen: `DPR-nnn, dd Mon yyyy`.
- Deadline: `dd Mon yyyy, PC 9.1` (or the clause that applies). `n/a` if no notice is required, say why in Status.
- Status: `open`, `cleared DPR-nnn dd Mon yyyy`, `contested MG-... dd Mon yyyy`, or `notified VX-RFI-... dd Mon yyyy`.
  Add standby as `standby n days, DPR-aaa to DPR-bbb` where it applies.
- Short title: three to five words, title case, the name the page shows. Lead with the place as the reports
  name it (a crossing, chainage, sector or drill), then what went wrong: `HDD-03 Permit Not Delivered`,
  `CH-512 Daily Permit Not Issued`. If the reports name no place, just what went wrong:
  `Cable Drums Not Delivered`. No clause numbers, no dates.

Table 2, `## EVIDENCE`, one row per citation, several per issue, first mention first:

| ID | Report | Date | Section | Quoted text |
|---|---|---|---|---|

- Report and Date: from the `===== FILE:` header and the document's own header line. Use the file name
  as written. Letters, emails and delivery notes are cited the same way, with Section `1`.
- Section: the number 1 to 8 as printed in the report.
- Quoted text: copy the words exactly as they appear in that section of that report. A table row is quoted as
  its cells in order. Do not paraphrase, do not merge two lines, do not add words.

Cite the first mention for every issue, the report that clears it, the comment that contests it, and enough
in between to show the run of idle days you counted. Fewer, exact citations beat many loose ones.

Table 3, `## CONTEXT`, **one row per SENTENCE**, issues in the order of Table 1 and sentences within an
issue in DATE ORDER, earliest first:

| ID | Sentence | Source |
|---|---|---|

- Sentence: one sentence of the context prose, written as below.
- Source: the EVIDENCE citations that sentence rests on, as `<report> <section>`, several separated by
  `;`, e.g. `DPR-007 7; DPR-008 5`. Every citation here must be a row you wrote in Table 2, spelled the
  same way. Write `judgement` instead where the sentence is your reasoning, or says that no document
  exists ("nothing else went out"). A sentence that is neither is not allowed: cite it or cut it.
  The page shows the quoted words under a sentence when the reader hovers it, and greys a `judgement`
  sentence, so a wrong citation here is visible on screen.
- Context: four to six sentences in plain English, the way a site manager tells it out loud, one beat per
  sentence. The beats below are the ones to cover, but the ROW ORDER IS THE ORDER THE EVENTS HAPPENED:
  where the paper position (beat 5) falls due before the issue clears, its sentence sits at its own date,
  not at the end.
  1. The event, dated and placed. On <date>, at <the crossing, sector or chainage>, what was found or what
     did not arrive, against what should have happened (the programme date, the borehole log, the contract's
     promise), and whose job it was.
  2. What the site did, dated. What was written or asked, what the crew did instead, and what stood idle
     from which day.
  3. What came back, dated. The reply, the instruction or the dispute, or "nothing from <the other party> by <date>".
  4. How it ended, dated. Delivered, cleared, instructed or complete on <date>. Where Table 1 counts standby
     days, give the number of days and what stood idle.
  5. The paper position, dated. What went out on which date and whether it was a notice for time and cost.
     If it was not, say so and give the date the notice window closed. Never say nothing was served when
     Table 1 records a notice. Where the notice served is the whole requirement (rule 7), say that it was
     served in time and that nothing more was owed; do not call a second window missed.
  Every sentence is anchored in time: a date written as 9 March, or "the same day", "the next day", "by then"
  when the sentence before already gives the date. Never both ("the same day, 16 March" is a tic). Join each
  sentence to the one before by its consequence (so, by then, while), never five separate statements, and
  keep each sentence to one thing that happened; two beats in one sentence read as a claim submission, not
  as a site manager talking. No report numbers,
  no letter references, no clause numbers, no section numbers. Every date, figure and fact must appear in
  your EVIDENCE rows or your Table 1 row for that issue; a script checks each one.

Table 4, `## NEXT`, one row per issue, same order as Table 1:

| ID | Next by | Clause | Next |
|---|---|---|---|

- Next by: the date the contract sets for the next step if it is still to come, `missed dd Mon yyyy` if
  that date fell before the as-of date, or `none` if nothing is required. Passed means passed as of the
  as-of date above, not as of the last report.
- Clause: the clause the step comes from, e.g. `PC 9.3`.
- Next: **the action, and nothing else. One sentence, an instruction, starting with the verb**: "Serve a
  notice under PC 9.1 by 16 Mar 2026, enclosing the permit record." No retelling of what happened, no
  summary of the issue, no reasoning: the reader has just read the context. The sentence names the clause
  it comes from ("under PC 12.2").
  **Where there is no action, say so and why, in one sentence beginning "No action":** "No action: the
  PC 9.1 window closed on 16 Mar 2026 with no notice served, so the 11 standby days cannot be claimed."
  The reason is the fact that removes the action (the window closed, the notice was served and answered,
  nothing stood idle), never a story.
  It must agree with your own Table 1 row: where that row records a notice served, do not ask for it
  again. Where the contract itself turns a notice into the entitlement (rule 7), that notice is the whole
  requirement: do not report a separate notice of claim as missed, and do not say time or money was lost.
  Never invent a loss. No report numbers and no letter references. At most two sentences, and a second
  one only where a second action genuinely follows the first.
  **Only what the contract gives.** Where the contract gives nothing, the row is `No action:` and the
  reason. Never propose a commercial settlement, a goodwill request, an ex-gratia payment or "putting it
  to them anyway" once a window has closed, and never soften a closed window with what the records would
  have shown. The register states the contract position; what to do beyond it is the reader's decision,
  not yours.

After the tables, one short paragraph headed `## Not listed` naming anything you considered and rejected,
with the reason in a few words each.

## Step 2: build the page

`issue-trace.md` is the model's output. It is not what the reader looks at. After you have written it,
render it, from the folder that holds `run/`:

```
python3 tools/make_issues_page.py issue-trace.md issues.html --pdf-dir run --letters-dir letters
```

That writes `issues.html`, a fixed 1920x1080 frame that scales to any window: the issue list on the left,
and for the selected issue its context, its evidence rows, the correspondence, and what is next. A report
line opens the PDF it came from. A correspondence item opens `letters/<REF>.pdf` when that file exists;
the rest are listed and not clickable.

You do not write the HTML and you do not restyle it. The colours, spacing and the three re-theming traps
are in `DESIGN.md`; read that file before changing any of them, and change them only if asked.

Correspondence inside `run/` IS an input. Read every letter, email, RFI, delivery note and variation
order in there and cite it like any other document. A letter is what decides whether a notice was served:
a letter that says it is a notice under the notices clause is one, and a reminder or a request is not.
Where a letter promises a further step, that step is a deadline like any other.

Then run the check and report what it prints:

```
python3 tools/check_links.py issue-trace.md
```

Done means both files exist, `issue-trace.md` and `issues.html`, and the check says ALL LINKS RESOLVE.
