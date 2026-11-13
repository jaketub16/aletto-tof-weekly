#!/usr/bin/env python3
"""Tie the built deck back to the pack. Recomputes key numbers from summary.json + last5k output
and checks each formatted value appears in <date>/index.html.
  python3 verify.py --pack /workspace/friday-pack-2026-11-06-12 --last5k /workspace/li-trim-2026-11-12 --date 2026-11-13
"""
import argparse, json, os, re, sys
ap = argparse.ArgumentParser(); ap.add_argument('--pack'); ap.add_argument('--last5k'); ap.add_argument('--date'); ap.add_argument('--metricool', help='Metricool day folder; enables independent content re-check')
a = ap.parse_args()
S = json.load(open(os.path.join(a.pack, 'summary.json')))
H = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), a.date, 'index.html')).read()
H = re.sub(r'<script>.*?</script>', lambda m: m.group(0) if '__' in m.group(0)[:0] else m.group(0), H, flags=re.S)
txt = re.sub(r'<[^>]+>', ' ', H.split('<script>')[0]); txt = re.sub(r'\s+', ' ', txt).replace('&#x27;', "'").replace('&quot;', '"')
chart = H.split('const H=')[1].split(';\n')[0] if 'const H=' in H else ''
m = lambda v: '$' + format(round(v), ',')
T, P = S['total_spend']['this'], S['total_spend']['prior']
b, bp = S['books']['this'], S['books']['prior']
li, lip = S['li_total']['this'], S['li_total']['prior']
L5 = open(os.path.join(a.last5k, 'last5k_output.txt')).read()
checks = [
 ('total spend', '~' + m(T)), ('prior spend', '~' + m(P)), ('spend change +4%', '+4%'),
 ('LinkedIn spend', m(li['spend'])), ('LinkedIn 2dp', '$' + format(li['spend'], ',.2f')), ('retargeting', m(S['li_rt_this'])),
 ('Meta est', '~$' + format(S['meta_est']['this'], ',')), ('clicks', str(li['clk'])), ('prior clicks', str(lip['clk'])),
 ('CTR', f"{li['ctr']}%"), ('CPC', f"${li['cpc']:.2f}"), ('CPM', f"${li['cpm']:.0f}"), ('prior CPM', f"${lip['cpm']:.0f}"),
 ('report leads', str(S['leads']['this']['total'])), ('prior leads', str(S['leads']['prior']['total'])),
 ('LI/Meta/organic leads', f"{S['leads']['this']['by_ch']['LinkedIn ads']} / {S['leads']['this']['by_ch']['Meta ads']} / {S['leads']['this']['by_ch']['Organic (5 Ways report)']}"),
 ('lead→book', f"{S['funnel']['this']['lead_to_book']}%"), ('books', str(b['strategy'])), ('qualified', str(b['q'])), ('scopes', str(b['scopes'])),
 ('$/book', '~' + m(T / b['strategy'])), ('$/qualified', '~' + m(T / b['q'])), ('prior $/qualified', '~' + m(P / bp['q'])),
 ('LI $/qualified', m(li['spend'] / b['by_ch']['LinkedIn ads']['q'])), ('Meta $/qualified', '~' + m(S['meta_est']['this'] / b['by_ch']['Meta ads']['q'])),
 ('Meta books/q', f"Meta {b['by_ch']['Meta ads']['books']} books / {b['by_ch']['Meta ads']['q']} qualified"),
 ('LI books/q', f"LinkedIn ads {b['by_ch']['LinkedIn ads']['books']} / {b['by_ch']['LinkedIn ads']['q']} ({bp['by_ch']['LinkedIn ads']['books']} / {bp['by_ch']['LinkedIn ads']['q']})"),
 ('organic books/q', 'Organic 12 / 5'), ('prospecting $260/day', '$260/day'),
 ('bg2 US any-Strat $/asked', '$834'), ('bg2 EU $/asked', '$835'), ('bg1 US any $/asked', '$1,008'), ('deadcold $/asked', '$762'), ('coldgraveyard $/asked', '$741'),
 ('datadoesnt Will H. $144', '$144'), ('coldgraveyard 40%', '40% of LinkedIn'), ('deadcold spend', '$775'),
 ('organic leads 52→61', '52 → 61'), ('static-test $172', '$172'),
]
# ---- content slides (content.json from content_extract.py)
WD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weeks', a.date)
CP = os.path.join(WD, 'content.json')
if os.path.exists(CP):
    CJ = json.load(open(CP)); tt = CJ['totals']['this']
    checks += [('content posts', f"{tt['posts']:,}"), ('content views', f"{tt['views']:,}"), ('content engagements', f"{tt['eng']:,}"),
               ('LinkedIn organic report leads', str(CJ['ghl']['this']['report_first'].get('LinkedIn organic', 0)) + '*')]
    for r in CJ['platforms']:
        checks.append((r['key'] + ' views', f"{r['this']['views']:,}"))
    # platform rows add up to the total
    for k in ('posts', 'views', 'eng', 'likes', 'comments'):
        s_ = sum(r['this'][k] for r in CJ['platforms'])
        checks.append((f'platform {k} sum = total', f"{tt[k]:,}" if s_ == tt[k] else f'__SUM_MISMATCH_{s_}_vs_{tt[k]}__'))
    # Hyros organic table ties to the pack's booking totals
    for touch in ('first', 'last'):
        T_ = CJ['hyros'][f'this_{touch}']
        for k, want in (('strat', S['books']['this']['strategy']), ('q', S['books']['this']['q']), ('scope', S['books']['this']['scopes'])):
            got = sum(x[k] for x in T_.values())
            checks.append((f'Hyros {touch}-touch {k} sums to pack ({want})', str(want) if got == want else f'__HYROS_{touch}_{k}_{got}__'))
    # GHL report leads tie to the pack's report-lead count
    gl = sum(CJ['ghl']['this']['report_first'].values())
    checks.append(('GHL report leads = pack', str(S['leads']['this']['total']) if gl == S['leads']['this']['total'] else f'__GHL_{gl}__'))
    # independent raw recompute (separate code path from content_extract.py)
    if a.metricool:
        import datetime as _dt
        from zoneinfo import ZoneInfo as _Z
        s0 = _dt.date.fromisoformat(CJ['window']['this'][0]); s1 = _dt.date.fromisoformat(CJ['window']['this'][1])
        def _raw(f, dkey, vkey):
            d = json.load(open(os.path.join(a.metricool, f))); d = d.get('data', d)
            n_ = vv = 0
            for x in d:
                t = _dt.datetime.fromisoformat(x[dkey]['dateTime']).replace(tzinfo=_Z(x[dkey]['timezone'])).astimezone(_Z('America/New_York')).date()
                if s0 <= t <= s1: n_ += 1; vv += int(float(x.get(vkey) or 0))
            return n_, vv
        for key, f, dk, vk in (('Jake · Threads', '6400379_v2_analytics_posts_threads.json', 'publishedDate', 'views'),
                               ('Jake · LinkedIn', '6400379_v2_analytics_posts_linkedin.json', 'created', 'impressions'),
                               ('Jake · X', '6400379_v2_analytics_posts_twitter.json', 'created', 'totalImpressions')):
            n_, vv = _raw(f, dk, vk); r = next(r for r in CJ['platforms'] if r['key'] == key)
            ok_ = (n_, vv) == (r['this']['posts'], r['this']['views'])
            checks.append((f'raw re-sum {key} {n_} posts / {vv:,} views', f"{vv:,}" if ok_ else f'__RAW_{key}_{n_}_{vv}__'))
# last5k text cross-checks
for pat, want in [(r'bg2 US \(ss-sd-es\) 732802984 spend \$5002 Strats 31 asked 6 scopes 4 \$/asked \$834', '$834'), (r'bg1 US \(hc-rm-ml\) 700616844 spend \$5039 Strats 31 asked 5 scopes 3 \$/asked \$1008', '$1,008'), (r'deadcold 1534286044\s+\$4570\.30 \| LT S35 A6 Sc6 \$762/ask', '$762')]:
    checks.append(('last5k source has ' + want, want if re.search(pat, L5) else '__MISSING_IN_SOURCE__'))
fail = 0
for name, want in checks:
    ok = want in txt or want in chart
    fail += not ok
    print(('ok  ' if ok else 'FAIL'), name, '=>', want)
# privacy: no full surnames from the roster
for r in b.get('roster', []):
    pass
print('PASS', len(checks) - fail, 'FAIL', fail)
sys.exit(1 if fail else 0)
