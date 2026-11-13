#!/usr/bin/env python3
"""Pull every number the deck shows out of a Friday pack folder into weeks/<date>/data.json.

Usage:
  python3 extract.py --pack /workspace/friday-pack-2026-11-06-12 \
      --last5k /workspace/li-trim-2026-11-12 --out weeks/2026-11-13/data.json

Inputs (same layout every Friday):
  <pack>/summary.json            analysis output (LinkedIn, leads, Hyros books, funnel)
  <pack>/raw/budgets_now/*.json  live LinkedIn campaign budgets (one campaign per file)
  <pack>/raw/zernio_li_extract.json  company-page posts
  <last5k>/last5k.json + last5k_output.txt   last-$5k per campaign (strict + any-Strat)
"""
import argparse, glob, json, os, re

ap = argparse.ArgumentParser()
ap.add_argument('--pack', required=True)
ap.add_argument('--last5k', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()

S = json.load(open(os.path.join(a.pack, 'summary.json')))
D = {'window': S['window']}

# ---- spend
D['spend'] = {
    'total': S['total_spend'], 'li': {w: S['li_total'][w]['spend'] for w in ('this', 'prior')},
    'li_rt': S['li_rt_this'], 'li_prosp': S['li_prospecting_this'], 'meta_est': S['meta_est'],
}
D['li_total'] = S['li_total']
D['li_camp'] = {w: sorted(S['li_camp'][w].values(), key=lambda c: -c['spend']) for w in ('this', 'prior')}
D['li_daily'] = S['li_daily']
D['li_camp_daily'] = S['li_camp_daily_this']
D['li_cr'] = {w: sorted([c for c in S['li_cr'][w].values() if c['spend'] >= 5], key=lambda c: -c['spend']) for w in ('this', 'prior')}

# ---- live budgets (files carry a one-line prefix before the JSON)
bud = []
for f in sorted(glob.glob(os.path.join(a.pack, 'raw/budgets_now/*.json'))):
    t = open(f).read()
    n = re.search(r'"name":"([^"]+)","account"', t)
    b = re.search(r'"dailyBudget":\{"currencyCode":"USD","amount":"([\d.]+)"', t)
    st = re.search(r'"status":"([A-Z]+)"', t)
    if n and b:
        bud.append({'name': n.group(1), 'daily': float(b.group(1)), 'status': st.group(1) if st else None})
D['budgets_now'] = bud

# ---- leads, books, funnel
D['leads'] = {w: {k: S['leads'][w][k] for k in ('total', 'by_ch', 'qlead', 'li_utm', 'meta_utm', 'by_day') if k in S['leads'][w]} for w in ('this', 'prior')}
D['books'] = {w: {k: S['books'][w].get(k) for k in ('strategy', 'people', 'q', 'unk', 'by_ch', 'by_cr', 'scopes', 'scopes_by_ch', 'scope_list')} for w in ('this', 'prior')}
D['funnel'] = S['funnel']

# ---- content (Zernio)
z = json.load(open(os.path.join(a.pack, 'raw/zernio_li_extract.json')))
P = z['posts']
D['content'] = {'posts': len(P), 'imp': sum(p['imp'] for p in P), 'likes': sum(p['likes'] for p in P),
                'shares': sum(p['shares'] for p in P), 'clicks': sum(p['clicks'] for p in P),
                'list': sorted(P, key=lambda p: p['date'])}

# ---- last $5k
L = json.load(open(os.path.join(a.last5k, 'last5k.json')))
txt = open(os.path.join(a.last5k, 'last5k_output.txt')).read()
alt = {}
for blk in re.split(r'\n## ', txt.split('======== ALT')[1])[1:]:
    head = blk.split('\n')[0]
    m = re.match(r'(.+?) (\d{9}) spend \$(\d+) Strats (\d+) asked (\d+) scopes (\d+)', head)
    if not m: continue
    ads = []
    for line in blk.split('\n')[1:]:
        mm = re.match(r'\s+(\S+)\s+S\s*(\d+) A\s*(\d+) Sc\s*(\d+)\s*(.*)', line)
        if mm:
            ads.append({'ad': mm.group(1), 'strats': int(mm.group(2)), 'asked': int(mm.group(3)), 'scopes': int(mm.group(4)),
                        'who': [re.sub(r' \(Strat.*', '', x).strip() + '.' for x in mm.group(5).split(';') if x.strip()]})
    alt[m.group(2)] = {'strats': int(m.group(4)), 'asked': int(m.group(5)), 'scopes': int(m.group(6)), 'ads': ads}
l5 = []
for k, v in L.items():
    cid = re.search(r'(\d{9})', k).group(1)
    label = k.split(' (')[0]
    ads = [{'ad': x['name'], 'spend': round(x['spend'], 2), 'strats': x['lt'][0], 'asked': x['lt'][1], 'scopes': x['lt'][2],
            'ft_scopes': x['ft'][2]} for x in v['ads'].values()]
    ads.sort(key=lambda x: -x['spend'])
    l5.append({'camp': label, 'id': cid, 'start': v['start'], 'spend': round(v['spend'], 2),
               'strict': {'strats': v['tot']['lt'][0], 'asked': v['tot']['lt'][1], 'scopes': v['tot']['lt'][2]},
               'ft_scopes': v['tot']['ft'][2], 'any': alt.get(cid), 'ads': ads})
D['last5k'] = l5

os.makedirs(os.path.dirname(a.out), exist_ok=True)
json.dump(D, open(a.out, 'w'), indent=1)
print('wrote', a.out, 'budgets', [(b['name'], b['daily']) for b in bud])
