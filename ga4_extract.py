#!/usr/bin/env python3
"""GA4 (Ryze google_analytics, property 540656492, timezone America/New_York) -> weeks/<date>/ga4.json.

VSL throughput for the Friday deck: opt-in page -> VSL -> booked Strat call, by source, this week vs prior, plus 30 days.
Raw inputs live in <raw>/ (saved from Ryze `google_analytics__runRawReport`, request passed as a JSON *string*;
queries are in ga4_queries.json, fill {THIS_START} etc.):
  pages_funnel.json  pagePath x 3 date ranges (this, prior, d30), host go.aletto.ai
  src_funnel.json    pagePath x sessionSource x sessionMedium x 3 ranges (funnel pages)
  device.json        pagePath x deviceCategory x 3 ranges
  daily.json         pagePath x date (prior start .. this end)
  hyros_d30_extra.json  optional: Hyros hyros_list_calls from d30 start to prior start (30-day books)
Books for this/prior come from data.json (Hyros strategy calls, last touch), the same numbers the deck uses.
Usage: python3 ga4_extract.py --raw ga4_raw/2026-11-13 --data weeks/2026-11-13/data.json --out weeks/2026-11-13/ga4.json
"""
import argparse, json, os, datetime as dt, collections as C
from zoneinfo import ZoneInfo

VSL, OPTIN, BOOKPG, CONF = '/freetraining-1-7481', '/saasreport', '/freetraining-booking-6842', '/confirmed'
W = ('this', 'prior', 'd30')
# GA4 sessionSource -> deck bucket (LinkedIn/Meta ads carry utm_source=linkedin / fb_ad; campaign sits in utm_medium)
BUCKETS = [('li_ads', 'LinkedIn ads'), ('meta_ads', 'Meta ads'), ('li_org', 'LinkedIn organic'), ('other', 'Direct, email, IG, YouTube & other'), ('untracked', 'No source in GA4 ((not set))')]
# Hyros last-touch channel -> bucket. Hyros 'Organic other' + 'No source' have no clean GA4 twin, so they share 'other+untracked'.
HY = {'LinkedIn ads': 'li_ads', 'Meta ads': 'meta_ads', 'Organic (probable LinkedIn)': 'li_org', 'Organic other': 'rest', 'No source': 'rest'}


def bucket(src):
    s = (src or '').lower()
    if s == 'linkedin': return 'li_ads'
    if s == 'fb_ad': return 'meta_ads'
    if s in ('linkedin.com', 'lnkd.in', 'li', 'com.linkedin.android', 'www.linkedin.com'): return 'li_org'
    if s in ('(not set)', '(data not available)', ''): return 'untracked'
    return 'other'


def rows(path):
    d = json.load(open(path))
    dh = [h['name'] for h in d['dimensionHeaders']]; mh = [h['name'] for h in d['metricHeaders']]
    return [dict(zip(dh, [v['value'] for v in r['dimensionValues']]), **{k: float(v['value']) for k, v in zip(mh, r['metricValues'])}) for r in d.get('rows', [])]


def r1(x, n=1): return None if x is None else round(x, n)
def rate(a, b): return r1(a / b * 100) if b else None


def hyros_extra(path):
    """30-day books before the prior week, same rules as the pack's hy.py (strategy calls, last-touch channel)."""
    t = open(path).read(); R = json.loads(t[t.find('{'):t.rfind('}') + 1])['result']
    def channel(s):
        if not s: return 'No source'
        ts = (s.get('trafficSource') or {}).get('name')
        if s.get('organic'): return 'Organic (probable LinkedIn)' if s.get('name') in ('li', 'linkedin') else 'Organic other'
        return {'linkedin': 'LinkedIn ads', 'facebook': 'Meta ads'}.get(ts, 'Other paid:' + str(ts))
    out = C.Counter(); n = 0
    for x in R:
        if 'Strategy' not in x['name']: continue
        n += 1; out[channel(x.get('lastSource'))] += 1
    return n, dict(out), len(R)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--raw', required=True); ap.add_argument('--data', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args(); D = json.load(open(a.data)); J = lambda f: os.path.join(a.raw, f)
    G = {'source': 'GA4 via Ryze google_analytics, property 540656492 "Aletto — aletto", timezone America/New_York (ET)',
         'window': D['window'], 'pages': {}}
    # ---- pages
    for r in rows(J('pages_funnel.json')):
        p = G['pages'].setdefault(r['pagePath'], {})
        p[r['dateRange']] = {'users': int(r['totalUsers']), 'new': int(r['newUsers']), 'sessions': int(r['sessions']), 'views': int(r['screenPageViews']),
                             'eng_s': int(r['userEngagementDuration']), 'eng_per_user_s': r1(r['userEngagementDuration'] / r['totalUsers'], 0) if r['totalUsers'] else None,
                             'engaged_sessions': int(r['engagedSessions']), 'key_events': r['keyEvents']}
    pg = lambda path, w, k='users': G['pages'].get(path, {}).get(w, {}).get(k, 0)
    # ---- books (Hyros): this/prior from data.json, d30 = extra + prior + this
    bk = {w: {'total': D['books'][w]['strategy'], 'by': C.Counter()} for w in ('this', 'prior')}
    for w in ('this', 'prior'):
        for ch, v in D['books'][w]['by_ch'].items(): bk[w]['by'][HY.get(ch, 'rest')] += v['books']
    if os.path.exists(J('hyros_d30_extra.json')):
        n, by, nraw = hyros_extra(J('hyros_d30_extra.json'))
        b30 = C.Counter(); [b30.update({HY.get(k, 'rest'): v}) for k, v in by.items()]
        bk['d30'] = {'total': n + bk['this']['total'] + bk['prior']['total'], 'by': b30 + bk['this']['by'] + bk['prior']['by'], 'extra_calls_read': nraw}
    # ---- sources (per page, per window)
    src = C.defaultdict(lambda: C.defaultdict(lambda: C.Counter()))  # page -> window -> bucket -> users
    detail = C.defaultdict(list)
    for r in rows(J('src_funnel.json')):
        if r['totalUsers'] <= 0: continue
        b = bucket(r['sessionSource'])
        src[r['pagePath']][r['dateRange']][b] += int(r['totalUsers'])
        detail[(r['pagePath'], r['dateRange'])].append({'source': r['sessionSource'], 'medium': r['sessionMedium'], 'bucket': b, 'users': int(r['totalUsers']),
                                                       'new': int(r['newUsers']), 'sessions': int(r['sessions']), 'eng_s': int(r['userEngagementDuration'])})
    G['source_detail'] = {f'{p}|{w}': sorted(v, key=lambda x: -x['users']) for (p, w), v in detail.items() if p in (VSL, OPTIN, BOOKPG, CONF)}
    leads_by = {w: D['leads'][w]['by_ch'] for w in ('this', 'prior')}
    LB = {'li_ads': 'LinkedIn ads', 'meta_ads': 'Meta ads'}
    by_source = []
    for key, label in BUCKETS:
        row = {'key': key, 'label': label}
        for w in W:
            v, o = src[VSL][w][key], src[OPTIN][w][key]
            books = bk.get(w, {}).get('by', {}).get(key) if key in ('li_ads', 'meta_ads', 'li_org') else None
            row[w] = {'vsl_users': v, 'optin_users': o, 'optin_to_vsl': rate(v, o), 'books': books, 'vsl_to_book': rate(books, v) if books is not None else None,
                      'leads': leads_by.get(w, {}).get(LB.get(key, ''), None) if key in LB else None}
            if key in LB and w in leads_by: row[w]['optin_rate'] = rate(row[w]['leads'], o)
        by_source.append(row)
    # combined "everything else" row: GA4 other + untracked vs Hyros Organic other + No source
    rest = {'key': 'rest', 'label': 'Everything else (direct, email, IG, YouTube, no source)'}
    for w in W:
        v = src[VSL][w]['other'] + src[VSL][w]['untracked']; o = src[OPTIN][w]['other'] + src[OPTIN][w]['untracked']
        books = bk.get(w, {}).get('by', {}).get('rest')
        rest[w] = {'vsl_users': v, 'optin_users': o, 'optin_to_vsl': rate(v, o), 'books': books, 'vsl_to_book': rate(books, v) if books is not None else None}
    G['by_source'] = by_source; G['by_source_rest'] = rest
    # ---- steps
    G['steps'] = {}
    for w in W:
        s = {'optin_users': pg(OPTIN, w), 'vsl_users': pg(VSL, w), 'vsl_new_users': pg(VSL, w, 'new'), 'booking_page_users': pg(BOOKPG, w), 'confirmed_users': pg(CONF, w),
             'vsl_eng_per_user_s': G['pages'].get(VSL, {}).get(w, {}).get('eng_per_user_s'), 'books': bk.get(w, {}).get('total')}
        s['optin_to_vsl'] = rate(s['vsl_users'], s['optin_users'])
        s['vsl_to_book'] = rate(s['books'], s['vsl_users']) if s['books'] else None
        if w in ('this', 'prior'):
            s['leads'] = D['leads'][w]['total']; s['optin_rate'] = rate(s['leads'], s['optin_users'])
        s['vsl_untracked_users'] = src[VSL][w]['untracked']; s['vsl_untracked_pct'] = rate(s['vsl_untracked_users'], s['vsl_users'])
        G['steps'][w] = s
    # ---- device / daily
    G['device'] = C.defaultdict(dict)
    for r in rows(J('device.json')):
        if r['pagePath'] in (VSL, OPTIN): G['device'][r['pagePath'] + '|' + r['dateRange']][r['deviceCategory']] = int(r['totalUsers'])
    G['device'] = dict(G['device'])
    G['daily'] = C.defaultdict(dict)
    for r in rows(J('daily.json')):
        d = f"{r['date'][:4]}-{r['date'][4:6]}-{r['date'][6:]}"; G['daily'][r['pagePath']][d] = int(r['totalUsers'])
    G['daily'] = dict(G['daily'])
    # ---- tracking checks (computed, not typed)
    t = G['steps']['this']
    G['tracking'] = {
        'key_events_total': sum((p.get(w, {}).get('key_events') or 0) for p in G['pages'].values() for w in W),
        'confirmed_vs_books': [t['confirmed_users'], t['books']],
        'vsl_untracked_pct': t['vsl_untracked_pct'],
        'li_ads_campaign_in_medium': sorted({x['medium'] for x in detail[(VSL, 'this')] + detail[(OPTIN, 'this')] if x['bucket'] == 'li_ads'}),
        'meta_campaign_in_medium': sorted({x['medium'] for x in detail[(VSL, 'this')] + detail[(OPTIN, 'this')] if x['bucket'] == 'meta_ads'}),
        'booking_page_sources_this': [(x['source'], x['users']) for x in G['source_detail'].get(f'{BOOKPG}|this', [])],
        'meta_optin_eng_per_user_s': r1(sum(x['eng_s'] for x in detail[(OPTIN, 'this')] if x['bucket'] == 'meta_ads') / max(1, src[OPTIN]['this']['meta_ads']), 0),
        'li_optin_eng_per_user_s': r1(sum(x['eng_s'] for x in detail[(OPTIN, 'this')] if x['bucket'] == 'li_ads') / max(1, src[OPTIN]['this']['li_ads']), 0),
    }
    # ---- per ad (optional): VSL users by utm_content this week vs Hyros last-touch books by ad
    if os.path.exists(J('vsl_by_ad_this.json')):
        A_ = json.load(open(J('vsl_by_ad_this.json')))['rows']
        books_cr = {r['cr']: r for r in D['books']['this']['by_cr']}
        G['by_ad'] = []
        for s_, ad, u in A_:
            b_ = books_cr.get(ad, {}).get('books', 0)
            G['by_ad'].append({'source': s_, 'ad': ad, 'vsl_users': u, 'books': b_, 'vsl_to_book': rate(b_, u)})
        big = [x for x in G['by_ad'] if x['vsl_users'] >= 15]
        G['notes_extra'] = ['Per ad (VSL visitors → books, this week): ' + '; '.join(f"{x['ad'].replace(' -W', '')} {x['vsl_users']} → {x['books']} ({x['vsl_to_book']}%)" for x in big) + '.']
    json.dump(G, open(a.out, 'w'), indent=1)
    print('ga4.json', a.out, 'VSL users', {w: G['steps'][w]['vsl_users'] for w in W}, 'books', {w: G['steps'][w]['books'] for w in W},
          'VSL->book %', {w: G['steps'][w]['vsl_to_book'] for w in W})


if __name__ == '__main__':
    main()
