#!/usr/bin/env python3
"""Content + organic-lead numbers for the deck's content slides -> weeks/<date>/content.json.

  python3 content_extract.py --metricool /workspace/content-performance/data/<Friday> \
      --pack /workspace/friday-pack-<dates> --out weeks/<date>/content.json [--zernio zernio_daily.json]

Inputs
  --metricool  folder from content-performance/run_daily.sh (Metricool raw JSON, rolling 30 days; run it Friday morning).
               Brands: 6400379 = Jake personal, 6396674 = Aletto. 6545263 (MXB) is a different brand and is skipped.
               The Facebook page 1187457517773840 is connected to both brands, so it is counted once, under Aletto.
  --pack       the Friday pack: summary.json (window), raw/ct/p*.json (GHL contacts), hyros_parsed.json, summary books roster.
  --zernio     optional: Zernio analytics_get_daily_metrics JSON for the 14 days (cross-check only).
Week = Fri–Thu Eastern, taken from summary.json. Views = impressions/views as each platform reports them
(Threads/Instagram/TikTok/YouTube/Facebook = views, LinkedIn/X = impressions). Engagements = likes + comments + shares/reposts + saves.
Output has no prospect emails/phones; prospects appear as first name + last initial.
"""
import argparse, collections as C, datetime as dt, glob, json, os, re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from utm_scheme import is_linkedin_paid, classify_lead, LI_ADS, META_ADS, LI_POSTTEXT

ap = argparse.ArgumentParser()
ap.add_argument('--metricool', required=True); ap.add_argument('--pack', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--zernio')
a = ap.parse_args()
ET = ZoneInfo('America/New_York')


def lj(p):
    t = open(p).read()
    i = min(x for x in (t.find('{'), t.find('[')) if x >= 0); j = max(t.rfind('}'), t.rfind(']'))
    return json.loads(t[i:j + 1])


S = json.load(open(os.path.join(a.pack, 'summary.json')))
start = dt.date.fromisoformat(re.search(r'(\d{4}-\d{2}-\d{2})', S['window']['this']).group(1))
W = {'this': (start, start + dt.timedelta(6)), 'prior': (start - dt.timedelta(7), start - dt.timedelta(1))}
wk_of = lambda d: next((k for k, (s, e) in W.items() if s <= d <= e), None)
OUT = {'window': {k: [str(s), str(e)] for k, (s, e) in W.items()}, 'sources': {'metricool': a.metricool, 'pack': a.pack}}

# ---------------------------------------------------------------- 1. posts (Metricool)
def ld(f):
    p = os.path.join(a.metricool, f)
    if not os.path.exists(p): return None
    d = json.load(open(p)); d = d.get('data', d) if isinstance(d, dict) else d
    return d if isinstance(d, list) else []


def when(x):
    if isinstance(x, dict):
        t = dt.datetime.fromisoformat(x['dateTime']).replace(tzinfo=ZoneInfo(x.get('timezone') or 'Europe/Madrid'))
    else:
        t = dt.datetime.fromisoformat(re.sub(r'([+-]\d\d)(\d\d)$', r'\1:\2', x))
    return t.astimezone(ET)


n = lambda v: float(v or 0)
P, MISSING = [], []


def add(brand, plat, fmt, t, text, url, views, reach, likes, comments, shares, saves, clicks, extra=None):
    wk = wk_of(t.date())
    if not wk: return
    eng = likes + comments + shares + saves
    text = (text or '').strip()
    hook = re.split(r'(?<=[.!?])\s|\n', text)[0][:140] if text else ''
    P.append(dict(wk=wk, brand=brand, platform=plat, format=fmt, et=t.strftime('%Y-%m-%d %H:%M'), hook=hook, text=text.replace('\n', ' ')[:300], url=url,
                  views=int(views), reach=int(reach) if reach is not None else None, likes=int(likes), comments=int(comments), shares=int(shares),
                  saves=int(saves), eng=int(eng), clicks=int(clicks) if clicks is not None else None,
                  er=round(100 * eng / views, 2) if views else None, **(extra or {})))


for b, bn in (('6400379', 'Jake'), ('6396674', 'Aletto')):
    files = {k: ld(f'{b}_v2_analytics_{k}.json') for k in ('posts_linkedin', 'posts_instagram', 'reels_instagram', 'posts_youtube', 'posts_tiktok',
                                                           'posts_twitter', 'posts_threads', 'posts_facebook', 'reels_facebook')}
    for x in files['posts_linkedin'] or []:
        add(bn, 'LinkedIn' if bn == 'Jake' else 'LinkedIn page', (x.get('type') or '').lower(), when(x['created']), x.get('comment'), x.get('url'),
            n(x.get('impressions')), x.get('uniqueImpressions'), max(n(x.get('likes')), n(x.get('like'))), n(x.get('comments')), n(x.get('shares')), 0,
            x.get('clicks'))
    for x in files['posts_instagram'] or []:
        add(bn, 'Instagram', (x.get('type') or '').lower().replace('feed_', ''), when(x['publishedAt']), x.get('content'), x.get('url'),
            n(x.get('views') or x.get('impressionsTotal')), n(x.get('reach')), n(x.get('likes')), n(x.get('comments')), n(x.get('shares')), n(x.get('saved')), None)
    for x in files['reels_instagram'] or []:
        add(bn, 'Instagram', 'reel', when(x['publishedAt']), x.get('content'), x.get('url'), n(x.get('views')), n(x.get('reach')),
            n(x.get('likes')), n(x.get('comments')), n(x.get('shares')), n(x.get('saved')), None,
            {'avg_watch_s': round(n(x.get('averageWatchTime')), 1), 'skip_rate': x.get('reelsSkipRate')})
    for x in files['posts_youtube'] or []:
        add(bn, 'YouTube', (x.get('videoType') or '').lower(), when(x['publishedAt']), x.get('title'), x.get('watchUrl'), n(x.get('views')), None,
            n(x.get('likes')), n(x.get('comments')), n(x.get('shares')), 0, None,
            {'watch_min': round(n(x.get('watchMinutes')), 1), 'avg_view_s': round(n(x.get('averageViewDuration')), 1)})
    for x in files['posts_tiktok'] or []:
        add(bn, 'TikTok', 'video', when(x['createTime']), x.get('videoDescription') or x.get('title'), x.get('shareUrl'), n(x.get('viewCount')), None,
            n(x.get('likeCount')), n(x.get('commentCount')), n(x.get('shareCount')), 0, None)
    for x in files['posts_twitter'] or []:
        add(bn, 'X', 'post', when(x['created']), x.get('text'), x.get('url'), n(x.get('totalImpressions')), None, n(x.get('totalLikes')),
            n(x.get('totalReplies')), n(x.get('totalRetweets')) + n(x.get('totalQuotes')), n(x.get('totalBookmarks')),
            n(x.get('totalProfileClicks')) + n(x.get('totalLinkClicks')), {'profile_clicks': int(n(x.get('totalProfileClicks')))})
    for x in files['posts_threads'] or []:
        add(bn, 'Threads', (x.get('mediaType') or '').lower().replace('_post', ''), when(x['publishedDate']), x.get('text'), x.get('permalink'),
            n(x.get('views')), None, n(x.get('likes')), n(x.get('replies')), n(x.get('reposts')) + n(x.get('quotes')) + n(x.get('shares')), 0, None)
    if bn == 'Aletto':  # shared FB page counted once
        for x in files['posts_facebook'] or []:
            add(bn, 'Facebook', (x.get('type') or '').lower(), when(x['created']), x.get('text'), x.get('link'), n(x.get('impressions')),
                n(x.get('impressionsUnique')), n(x.get('reactions')), n(x.get('comments')), n(x.get('shares')), 0, x.get('clicks'))
        for x in files['reels_facebook'] or []:
            add(bn, 'Facebook', 'reel', when(x['created']), x.get('description'), x.get('reelUrl'), n(x.get('blueReelsPlayCount')),
                n(x.get('postImpressionsUnique')), n(x.get('postVideoReactions')), 0, 0, 0, None)
seen, Q = set(), []
for p in P:
    k = (p['platform'], p['url'] or p['et'] + p['hook'])
    if k not in seen: seen.add(k); Q.append(p)
P = Q


def tot(ps):
    v = sum(p['views'] for p in ps); e = sum(p['eng'] for p in ps); ck = [p['clicks'] for p in ps if p['clicks']]
    rc = [p['reach'] for p in ps if p['reach'] is not None]
    return dict(posts=len(ps), views=v, reach=sum(rc) if rc else None, likes=sum(p['likes'] for p in ps), comments=sum(p['comments'] for p in ps),
                shares=sum(p['shares'] for p in ps), saves=sum(p['saves'] for p in ps), eng=e, er=round(100 * e / v, 2) if v else None,
                clicks=sum(ck) if ck else None, per_post=round(v / len(ps)) if ps else 0,
                median_views=sorted(p['views'] for p in ps)[len(ps) // 2] if ps else 0)


ORDER = ['Jake · LinkedIn', 'Jake · Instagram', 'Jake · Threads', 'Jake · X', 'Jake · TikTok', 'Jake · YouTube',
         'Aletto · LinkedIn page', 'Aletto · Instagram', 'Aletto · Facebook', 'Aletto · YouTube']
OUT['platforms'] = []
for key in ORDER + sorted({f"{p['brand']} · {p['platform']}" for p in P} - set(ORDER)):
    t = tot([p for p in P if p['wk'] == 'this' and f"{p['brand']} · {p['platform']}" == key])
    pr = tot([p for p in P if p['wk'] == 'prior' and f"{p['brand']} · {p['platform']}" == key])
    if t['posts'] or pr['posts']: OUT['platforms'].append({'key': key, 'this': t, 'prior': pr})
OUT['totals'] = {w: tot([p for p in P if p['wk'] == w]) for w in W}
strip = lambda p: {k: p[k] for k in ('brand', 'platform', 'format', 'et', 'hook', 'url', 'views', 'reach', 'likes', 'comments', 'shares', 'saves', 'eng', 'er', 'clicks')}
R = [p for p in P if p['wk'] == 'this']
OUT['top'] = {'by_views': [strip(p) for p in sorted(R, key=lambda p: -p['views'])[:10]],
              'by_eng': [strip(p) for p in sorted(R, key=lambda p: (-p['eng'], -p['views']))[:10]],
              'by_er_min100': [strip(p) for p in sorted([p for p in R if p['views'] >= 100], key=lambda p: -(p['er'] or 0))[:10]],
              'per_platform': {k['key']: [strip(p) for p in sorted([p for p in R if f"{p['brand']} · {p['platform']}" == k['key']], key=lambda p: (-p['eng'], -p['views']))[:5]]
                               for k in OUT['platforms']}}
# same hook reposted across platforms (cross-platform winners)
hk = C.defaultdict(list)
for p in R:
    if p['hook']: hk[p['hook'].lower()[:60]].append(p)
OUT['cross_platform'] = sorted([{'hook': v[0]['hook'], 'posts': len(v), 'platforms': sorted({x['platform'] for x in v}), 'views': sum(x['views'] for x in v),
                                 'eng': sum(x['eng'] for x in v)} for v in hk.values() if len({x['platform'] for x in v}) >= 2], key=lambda x: -x['eng'])[:8]
OUT['posts_this'] = [strip(p) for p in sorted(R, key=lambda p: p['et'])]
mc = os.path.join(a.metricool, 'summary.json')
if os.path.exists(mc):
    OUT['metricool_calls'] = [{k: c.get(k) for k in ('brand', 'network', 'endpoint', 'status', 'rows', 'error')} for c in json.load(open(mc))['calls']]

# ---------------------------------------------------------------- 2. GHL leads by organic source (first + last touch)
def net(x):
    if not x: return 'No attribution'
    ref = (x.get('referrer') or '').lower(); ua = x.get('userAgent') or ''; us = (x.get('utmSource') or '').lower(); u = (x.get('pageUrl') or x.get('url') or '').lower()
    host = urlparse(ref).netloc or ref
    if is_linkedin_paid(x) or 'li_fat_id' in u: return 'Paid LinkedIn'
    if us in ('fb_ad',) or ('fbclid' in u and ('utm_' in u or us == 'facebook')): return 'Paid Meta'
    # 2026-11-19: no UTMs + LinkedIn referrer/app + report page = the untagged lnkd.in link in the /saasreport ads' post text
    if not us and ('linkedin' in ref or 'lnkd' in ref or 'LinkedInApp' in ua) and urlparse(u).path.rstrip('/') == '/saasreport':
        return 'Paid LinkedIn (post-text link, untracked)'
    if 'linkedin' in ref or 'lnkd' in ref or 'LinkedInApp' in ua or 'linkedin' in us: return 'LinkedIn organic'
    if 'instagram' in ref or 'Instagram' in ua or us in ('ig', 'instagram'): return 'Instagram'
    if 'youtube' in ref or 'youtu.be' in ref or us in ('yt', 'youtube'): return 'YouTube'
    if host in ('t.co', 'x.com', 'twitter.com') or us in ('x', 'twitter'): return 'X'
    if 'threads' in ref: return 'Threads'
    if 'tiktok' in ref: return 'TikTok'
    if 'facebook' in ref or 'FBAN' in ua or 'FB_IAB' in ua or 'fbclid' in u: return 'Facebook organic'
    if 'skool' in ref: return 'Skool'
    if 'google' in ref or 'bing' in ref or 'duckduckgo' in ref: return 'Search'
    if 'chatgpt' in ref or 'chatgpt' in us or 'perplexity' in ref: return 'AI search'
    if not ref: return 'Direct / no referrer'
    return 'Other referrer'


cs = {}
for f in sorted(glob.glob(os.path.join(a.pack, 'raw/ct/p*.json'))):
    d = lj(f); d = d.get('data', d)
    for c in d['contacts']: cs[c['id']] = c
G = []
for c in cs.values():
    wk = wk_of(dt.datetime.fromisoformat(c['dateAdded'].replace('Z', '+00:00')).astimezone(ET).date())
    if not wk: continue
    att = c.get('attributions') or []
    fi = next((x for x in att if x.get('isFirst')), att[0] if att else {}); la = next((x for x in att if x.get('isLast')), att[-1] if att else {})
    tags = set(c.get('tags', [])); page = urlparse(fi.get('pageUrl') or fi.get('url') or '').path
    rep = 'saasreport' in tags or 'saasreport' in page or '5 ways' in (c.get('source') or '').lower()
    if 'hiring' in tags or 'test' in tags: continue  # 2026-11-20: skip test contacts, same as leads.py
    nf = net(fi)
    if not nf.startswith('Paid'):  # a later paid click beats an earlier organic/referral visit
        nf = next((n for n in (net(x) for x in att if x is not fi) if n in ('Paid LinkedIn', 'Paid Meta')), nf)
    # 2026-11-20: paid/not-paid follows the shared lead rule (utm_scheme.classify_lead), so this table ties to the pack's lead channels
    cl = classify_lead(c)
    if cl['ch'] == META_ADS: nf = 'Paid Meta'
    elif cl['ch'] in (LI_ADS, LI_POSTTEXT): nf = 'Paid LinkedIn (post-text link, untracked)' if cl['reason'].startswith('li_referrer') else 'Paid LinkedIn'
    elif nf.startswith('Paid'): nf = 'Direct / no referrer'
    G.append(dict(wk=wk, first=nf, last=net(la), rep=rep, q='qualified lead' in tags, page=page or '(none)'))
OUT['ghl'] = {}
for w in W:
    g = [x for x in G if x['wk'] == w]
    rep = [x for x in g if x['rep']]
    OUT['ghl'][w] = {'contacts': len(g), 'report_leads': len(rep),
                     'report_first': dict(C.Counter(x['first'] for x in rep).most_common()),
                     'report_last': dict(C.Counter(x['last'] for x in rep).most_common()),
                     'report_first_q': dict(C.Counter(x['first'] for x in rep if x['q']).most_common()),
                     'all_first': dict(C.Counter(x['first'] for x in g).most_common()),
                     'nonpaid_pages': dict(C.Counter(x['page'] for x in g if not x['first'].startswith('Paid')).most_common(8))}

# ---------------------------------------------------------------- 3. Hyros books by organic source (first + last touch)
H = json.load(open(os.path.join(a.pack, 'hyros_parsed.json')))
NAME = {'li': 'LinkedIn organic', 'linkedin': 'LinkedIn organic', 'ig': 'Instagram', 'instagram': 'Instagram', 'fb': 'Facebook organic', 'yt': 'YouTube',
        'youtube': 'YouTube', 'x': 'X', 'tw': 'X', 'twitter': 'X', 'threads': 'Threads', 'tiktok': 'TikTok', 'google-organic': 'Google organic',
        'youtube-organic': 'YouTube', 'facebook-organic': 'Facebook organic', 'linkedin-organic': 'LinkedIn organic', 'instagram-organic': 'Instagram', 'email': 'Email', 'freereport': 'Free report (nurture)', 'skool': 'Skool'}


def lab(s):
    if s['ts'] == 'none': return 'No source'
    if s['org']: return NAME.get(str(s['name']).lower(), 'Organic ' + str(s['name']))
    return {'linkedin': 'Paid LinkedIn', 'facebook': 'Paid Meta'}.get(s['ts'], 'Paid ' + str(s['ts']))


OUT['hyros'] = {}
for w in W:
    q = {(r['name'], r['day'], r['state']): r['q'] for r in S['books'][w]['roster']}
    R2 = [h for h in H if h['wk'] == w and h['kind'] in ('strategy', 'scope')]
    for touch, key in (('last', 'lt'), ('first', 'ft')):
        t = C.defaultdict(lambda: {'strat': 0, 'q': 0, 'scope': 0, 'scope_who': []})
        for h in R2:
            k = lab(h[key]); nm = f"{h['first']} {h['last'][:1]}." if h['last'] else h['first']
            if h['kind'] == 'strategy':
                t[k]['strat'] += 1; t[k]['q'] += bool(q.get((nm, h['day'], h['state'])))
            else:
                t[k]['scope'] += 1; t[k]['scope_who'].append(nm.strip())
        OUT['hyros'][f'{w}_{touch}'] = dict(sorted(t.items(), key=lambda kv: -(kv[1]['strat'] + kv[1]['scope'])))
    OUT['hyros'][f'{w}_check'] = {'strat': sum(1 for h in R2 if h['kind'] == 'strategy'), 'q_roster': sum(bool(r['q']) for r in S['books'][w]['roster']),
                                  'scope': sum(1 for h in R2 if h['kind'] == 'scope')}

# ---------------------------------------------------------------- 4. Zernio cross-check (optional)
if a.zernio and os.path.exists(a.zernio):
    z = lj(a.zernio); z = json.loads(z['result']) if isinstance(z, dict) and isinstance(z.get('result'), str) else z
    t = {w: C.defaultdict(C.Counter) for w in W}
    for day in z['dailyData']:
        w = wk_of(dt.date.fromisoformat(day['date'][:10]))
        if w:
            for p, m in day['platformMetrics'].items(): t[w][p].update(m)
    OUT['zernio'] = {w: {p: dict(m) for p, m in v.items()} for w, v in t.items()}

os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
json.dump(OUT, open(a.out, 'w'), indent=1)
print('wrote', a.out, '| posts this/prior', OUT['totals']['this']['posts'], OUT['totals']['prior']['posts'],
      '| views', OUT['totals']['this']['views'], OUT['totals']['prior']['views'])
for p in OUT['platforms']: print(f"  {p['key']:24s} {p['this']['posts']:4d} posts {p['this']['views']:>8,} views  eng {p['this']['eng']:4d}  | prior {p['prior']['posts']:4d} / {p['prior']['views']:>8,}")
print('  GHL report leads first touch:', OUT['ghl']['this']['report_first'], '| prior', OUT['ghl']['prior']['report_first'])
print('  Hyros first touch:', {k: (v['strat'], v['q'], v['scope']) for k, v in OUT['hyros']['this_first'].items()})
