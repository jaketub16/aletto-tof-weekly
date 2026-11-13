# Aletto · Friday top-of-funnel deck

Live, branded HTML deck of the weekly top-of-funnel pack (Fri–Thu ET vs the week before).
Same Apple-glass design system as the 2026 YTD marketing deck and the 60-day sales scorecard.

- Latest week: `/` (root `index.html`)
- Each week: `/<YYYY-MM-DD>/` (the Friday it was built)
- Archive: `/archive/`

Arrow keys / space / swipe to move, **N** for speaker notes, `?static` turns animation off, `#5` jumps to slide 5.

## Weekly rebuild (every Friday)
```bash
# 1. numbers from the new Friday pack + latest last-$5k run
python3 extract.py --pack /workspace/friday-pack-<dates> --last5k /workspace/li-trim-<date> --out weeks/<YYYY-MM-DD>/data.json
# 2. copy last week's story.json into weeks/<YYYY-MM-DD>/ and rewrite the words (verdict, winners/losers, fatigue, recs, gaps)
# 3. build + verify
python3 build.py weeks/<YYYY-MM-DD>
python3 verify.py --pack /workspace/friday-pack-<dates> --last5k /workspace/li-trim-<date> --date <YYYY-MM-DD>
git add -A && git commit -m "TOF deck <YYYY-MM-DD>" && git push
```
`build.py --all` rebuilds every week. Root `index.html` always points at the newest week; old weeks stay at their dated path.

Files: `extract.py` (pack → data.json), `build.py` (data + story → HTML), `verify.py` (deck ↔ pack tie-out), `assets/` (CSS, Chart.js, logo, deck JS), `weeks/<date>/` (data.json + story.json).

Privacy: prospects are first name + last initial only; no emails, phones or companies of prospects.
Meta spend is an estimate (~$190/day) while the Aletto Meta ad account is locked, and is labelled that way on every slide.
