# Paper Trail

Daily reports in. Notice deadlines out.

Site teams write everything down in their daily progress reports. Most contracts say a report
entry is not a notice. So the event is on record, and the notice window still closes.

Paper Trail is a Claude Code skill that reads a folder of daily reports against the contract and
the programme. For each issue the contract puts on the other party, it says when the issue first
appeared in a report, when the notice was due, and whether one went out. Every line it writes
points at the exact report, date, section and words it came from, and a script checks that the
quoted words are really there.

This repository ships a worked example: an invented HDD and cable project with 60 dummy daily
reports, a dummy subcontract and a dummy programme. Every party, figure and date in it is made up.

## Before you start

1. **Homebrew**, the Mac package installer. If `brew --version` fails in Terminal, install it from [brew.sh](https://brew.sh).
2. **git**. If `git --version` fails, run `xcode-select --install`.
3. **Claude Code**, with a Claude Pro, Max, Team, Enterprise or Console account. The free claude.ai
   plan does not include Claude Code. Install it with:

   ```
   curl -fsSL https://claude.ai/install.sh | bash
   ```

   Open a new Terminal window, run `claude`, and log in when the browser opens.
   Full instructions: [Claude Code setup](https://code.claude.com/docs/en/setup).
4. **Python 3**, already on most Macs. Check with `python3 --version`.
5. **poppler**, for reading PDFs:

   ```
   brew install poppler
   brew install tesseract pillow   # optional, scanned PDFs only
   ```

Tested on macOS.

## Run it

```
git clone https://github.com/jiwani87/paper-trail.git
cd paper-trail
claude
```

Then say:

```
trace the DPRs in run/
```

Claude asks your permission before it runs each command (text extraction, the page build, the check).
Approve them. The skill reads `run/` and writes its outputs into this folder.

It first asks which party you act for, using the names in the contract, and saves your answer to
`run/ACTING-FOR.txt`. Then it reads the contract, the programme and every report, and writes:

| File | What it is |
|---|---|
| `issue-trace.md` | the register, four tables: ISSUES, EVIDENCE, CONTEXT, NEXT. Every row cited |
| `issues.html` | the page a person reads. Open it in a browser. Click a report line to open that PDF |

## Check it

Nothing here asks you to take the model's word for it:

```
python3 tools/check_links.py issue-trace.md
```

It takes every quoted line in `issue-trace.md`, opens the PDF that row points at, and looks for
the line inside it. `ALL LINKS RESOLVE` means every quote is really in the report it cites.
Anything else names the rows that failed.

## What is in here

| Path | What it is |
|---|---|
| `run/` | the input: 60 daily reports, the subcontract extract, the scope and programme, all PDF |
| `run/AS-OF.txt` | the date deadlines are judged against. Delete it to use today's date |
| `run/ACTING-FOR.txt` | written on first run: the party you act for. Delete it to be asked again |
| `letters/` | the correspondence the reports refer to. Not an input: the page links them so a reader can open one |
| `.claude/skills/dpr-trace/SKILL.md` | the whole method: what counts as an issue, the date rules, the four tables |
| `DESIGN.md` | the page's colours and spacing. Read before restyling |
| `tools/extract_text.sh` | step 0: turns the PDFs into text, with OCR where a PDF has no text layer |
| `tools/make_issues_page.py` | builds `issues.html` from `issue-trace.md` |
| `tools/make_dashboard.py` | the register parser the page builder imports |
| `tools/check_links.py` | the check above |
| `tools/pdf_text.py` | PDF text and OCR helper used by step 0 and the check |

## Use it on your own reports

Replace the contents of `run/` with your own contract, programme and daily reports, under any
file names. Minutes, letters, emails and transmittals can go in too, and it reads them alongside
the reports. Set `run/AS-OF.txt` to the date you want deadlines judged against, or delete it.

Your documents are read by Claude through your own Claude Code account. Check your contract's
confidentiality terms before you put a live project in.

## What this cannot do

It reads what is in the folder and nothing else. It cannot see a conversation on site, a drawing
that was never issued, or a report nobody wrote.

It cites the contract by clause. Nothing checks that a clause it names exists in your contract, so
read the clause references before you rely on one.

The check proves the quotes and nothing more. It does not know whether a line was filed under the
right issue, whether the standby days were counted correctly, or whether the reasoning is sound.
Whether an issue is yours to claim is still your call.

## Licence

MIT. See `LICENSE`.
