# Aletto · Friday top-of-funnel deck

Live, branded HTML deck of the weekly top-of-funnel pack (Fri–Thu ET vs the week before).
Same Apple-glass design system as the 2026 YTD marketing deck and the 60-day sales scorecard.

- Latest week: `/` (root `index.html`)
- Each week: `/<YYYY-MM-DD>/` (the Friday it was built)
- Archive: `/archive/`

Arrow keys / space / swipe to move, **N** for speaker notes, `?static` turns animation off, `#5` jumps to slide 5.

## Weekly rebuild (every Friday)
```bash
# 0. content data: refresh Metricool (read-only) and save Zernio daily metrics (optional cross-check)
/workspace/content-performance/run_daily.sh 30          # -> /workspace/content-performance/data/<Friday>/
#    Zernio MCP analytics_get_daily_metrics(from_date=<prior Fri>, to_date=<Thu>) -> save JSON as /workspace/content-week-<date>/zernio_daily.json
# 0b. GA4 (read-only): run the 5 queries in ga4_queries.json through Ryze google_analytics__runRawReport
#     (propertyId "540656492", request as a JSON *string*) and save them + the 30-day Hyros extra into ga4_raw/<YYYY-MM-DD>/
# 1. numbers from the new Friday pack + latest last-$5k run (+ content.json when --metricool, + ga4.json when --ga4)
python3 extract.py --pack /workspace/friday-pack-<dates> --last5k /workspace/li-trim-<date> --out weeks/<YYYY-MM-DD>/data.json \
    --metricool /workspace/content-performance/data/<Friday> --zernio /workspace/content-week-<date>/zernio_daily.json \
    --ga4 ga4_raw/<YYYY-MM-DD>
# 2. copy last week's story.json into weeks/<YYYY-MM-DD>/ and rewrite the words (verdict, winners/losers, fatigue, recs, gaps,
#    and content2: score_h/sub, leads_h/sub, hot post + why, 5 hooks, 3 super hooks, tests) from content.json
# 3. build + verify
python3 build.py weeks/<YYYY-MM-DD>
python3 verify.py --pack /workspace/friday-pack-<dates> --last5k /workspace/li-trim-<date> --date <YYYY-MM-DD> \
    --metricool /workspace/content-performance/data/<Friday> --ga4 ga4_raw/<YYYY-MM-DD>
git add -A && git commit -m "TOF deck <YYYY-MM-DD>" && git push
```
`build.py --all` rebuilds every week. Root `index.html` always points at the newest week; old weeks stay at their dated path.

### VSL throughput (slides 4–5, GA4)
`ga4_extract.py` writes `weeks/<date>/ga4.json` from `ga4_raw/<date>/` (GA4 property 540656492 "Aletto — aletto", timezone America/New_York, so dates are already ET):
- Pages: report page `go.aletto.ai/saasreport` → VSL `/freetraining-1-7481` (the strategy-call calendar is embedded on the VSL page) → `/confirmed`; `/freetraining-booking-6842` is the email/DM booking page.
- Unique users, new users, sessions, views, engagement time per page, by session source/medium, device and day; this week, prior week and 30 days.
- Source buckets: LinkedIn ads = utm_source `linkedin` (also `paid_social` medium on a LinkedIn host); Meta ads = `fb_ad`; LinkedIn organic = `linkedin.com`/`lnkd.in`/`li`; everything else = direct, email, IG, YouTube and `(not set)`. Ad-set name is `sessionCampaignName` when medium is generic (`paid_social`, …); otherwise it still sits in `sessionMedium` (old LinkedIn UTMs). See `utm_scheme.py`.
- VSL visitor → book % = Hyros strategy calls (last touch, same week, same numbers as the Books slide) ÷ GA4 VSL unique users. Jake's bar: 2–5% is good. Not a per-person cohort until a GA4 booking event exists.
- Slide 4 funnel shows report-page and VSL visitors; slide 5 is "VSL throughput by source"; GA4 tracking gaps go on the Data gaps slide (story.json `gaps`).
- If `ga4.json` is missing, build.py falls back to the old "not tracked" funnel row and skips slide 5.

### Content slides (12–14)
`content_extract.py` writes `weeks/<date>/content.json`:
- **platforms**: per brand · platform (Jake: LinkedIn, Instagram, Threads, X, TikTok, YouTube; Aletto: LinkedIn page, Instagram, Facebook, YouTube) posts, views, reach, likes, comments, shares, saves, engagement rate, clicks, this vs last week. Source: Metricool raw JSON (lifetime-to-date per post on the pull day).
- **top / cross_platform / posts_this**: every post this week, top 10 by views, engagement and engagement rate, and hooks reused across platforms.
- **ghl**: free-report leads by first- and last-touch organic source (LinkedIn organic, Instagram, YouTube, X, Threads, TikTok, Facebook, search, direct), from GHL attribution referrer + in-app user agent.
- **hyros**: strategy calls / qualified / Scopes by organic source, first and last touch (Hyros source names li, ig, fb, google-organic, email, freereport).
Hot post rule: #1 by leads where post-level tracking exists; until then #1 by engagement on the platform that produced the most organic leads.
Hooks / super hooks: built from the winning posts + `/workspace/us-qualified-remakes-2026-11-09/scope_buyer_patterns.md` (Fathom Scope-buyer language).
If `content.json` or `story.content2` is missing, build.py falls back to the old single Content slide.

Files: `extract.py` (pack → data.json, + content.json, + ga4.json), `ga4_extract.py` (GA4 raw → ga4.json), `ga4_queries.json` (the GA4 requests), `content_extract.py` (Metricool + GHL + Hyros → content.json), `build.py` (data + story → HTML), `verify.py` (deck ↔ pack tie-out), `assets/` (CSS, Chart.js, logo, deck JS), `weeks/<date>/` (data.json + story.json).

Privacy: prospects are first name + last initial only; no emails, phones or companies of prospects.
Meta spend is an estimate (~$190/day) while the Aletto Meta ad account is locked, and is labelled that way on every slide.
