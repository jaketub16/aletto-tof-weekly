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
# 0b. GA4 (read-only): run the 6 queries in ga4_queries.json through Ryze google_analytics__runRawReport
#     (propertyId "540656492", request as a JSON *string*) and save them + the 30-day Hyros extra into ga4_raw/<YYYY-MM-DD>/
#     src_funnel.json is ~600 rows and the Ryze result gets truncated (omittedItems/fullTextId): read the full text with
#     native__read_tool_output in 30,000-char chunks before saving. Then re-split Hyros organic-'li' books with GHL:
python3 books_resplit.py --hyros /workspace/friday-pack-<dates>/raw/hyros_*.json ga4_raw/<YYYY-MM-DD>/hyros_d30_extra.json \
    --contacts '/workspace/friday-pack-<dates>/raw/ct/*.json' '/workspace/friday-pack-<dates>/raw/lookups/*' --this <Fri> <Thu> --prior <Fri-7> <Thu-7> --d30 <Thu-29> \
    --out ga4_raw/<YYYY-MM-DD>/books_resplit.json      # GHL contact pages (+ email lookups for older bookers)
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

### Lead channels (2026-11-19, reporting-only fix)
One shared rule for GHL leads: `utm_scheme.classify_lead(contact)`. The pack's `leads.py`, the daily pulse `classify.py` and `content_extract.py` use it.
- Paid UTMs or click IDs from **any** touch win: LinkedIn (`utm_source=linkedin` with a paid or ad-set medium, `lnk_id`, `li_fat_id`) or Meta (`fb_ad`, `fbclid`). A later paid click beats an earlier organic or referral visit. After that come the new tracking custom fields.
- No UTMs on the first touch, plus a referrer of linkedin.com, lnkd.in or com.linkedin.android (first touch or the new `referrer` field), plus landing on `/saasreport` = **LinkedIn Ads (post-text link, untracked)**. These are counted inside "LinkedIn ads" with ad set and ad `unattributed` (`li_posttext` in leads_summary).
  - Why: every /saasreport ad has an untagged `lnkd.in/eUvfBJqe` link in its post text.
  - See /workspace/li-organic-misattribution-2026-11-19/README.md.
- GHL's `utmSessionSource` labels ("Social media", "Paid Social", "Direct traffic") are never used. The ad set comes from utm_campaign, or from utm_medium for old-scheme contacts, read off the landing URL.
- GA4 (`ga4_extract.bucket`): linkedin.com and lnkd.in referral sessions on `/saasreport` count as LinkedIn ads. `li` and LinkedIn referrals on other pages stay organic.
  - VSL/booking pages (fixed 2026-11-19): `src_landing.json` (pagePath × sessionSource × landingPage, LinkedIn referral hosts only, ~20 rows) shows where those sessions landed. GA4 users don't add up across landing pages, so ga4_extract moves the **share** that landed on `/saasreport`: `moved = round(li_org_referral × saasreport_landings / all_LinkedIn_landings)`. Landings on the VSL itself, `/`, other pages or `(not set)`, and tagged `li` links stay organic. Page totals don't change.
  - Books: Hyros last-touch calls post-text bookers organic `li`. `books_resplit.py` looks each one up in GHL by email and moves the ones `classify_lead` calls LinkedIn ads into li_ads (`books_resplit.json`; no GHL match stays organic). ga4_extract and verify.py use both files if present.
- Contacts tagged `test` are skipped. Run `python3 test_utm_scheme.py` after any change.
- Next Friday: copy `/workspace/friday-pack-2026-11-06-12/leads.py` into the new pack. It takes `python3 leads.py <this_start> <this_end>` (ET dates).

## 2026-11-20 changes
- `story.json` can carry a `"text"` dict that overrides any slide prose in build.py (keys: title_*, week_notes, spend_*, bud_lbl, bud_labels, funnel_*, vsl_*, books_*, cost_*, l5_*, l5ad_* incl. l5ad_cols / l5ad_trunc, cr_*, fat_*, sb_*, org_notes, hot_*, recs_*, gaps_notes). Rewrite them every week; defaults are the Nov 13 words.
- `budgets_now/` in the pack must hold ACTIVE campaigns only (paused ones inflate the prospecting sum).
- content_extract.py skips `test`-tagged contacts and uses `utm_scheme.classify_lead` for paid vs not paid, so the content lead table ties to the pack's lead channels.
- verify.py: week-specific literal checks live in `WEEK[date]` and `L5PAT[date]`; add this week's before running.
- `ga4_raw/*/hyros_d30_extra.json` holds prospect emails and is git-ignored (the repo is public). Never commit it.
