#!/usr/bin/env python3
"""Hyros 'Organic (probable LinkedIn)' strategy books -> re-split with GHL (source of truth), 2026-11-19.

Hyros files people who came through the untagged lnkd.in link in the /saasreport ads' post text as organic 'li'.
For each such book, find the GHL contact by email and run utm_scheme.classify_lead: LinkedIn ads (tagged or
post-text link) => move the book to li_ads. No GHL match or GHL organic => stays li_org.
Writes <raw>/books_resplit.json: {window: {"li_org_to_li_ads": n, "posttext": n, "tagged": n, "kept_org": n, "no_match": n}}
which ga4_extract.py uses to move books between li_org and li_ads (totals unchanged).
Usage: python3 books_resplit.py --hyros <hyros_list_calls json(s)> --contacts '<glob of GHL contact pages>' \
          --this 2026-11-13 2026-11-19 --prior 2026-11-06 2026-11-12 --d30 2026-10-21 --out ga4_raw/<date>/books_resplit.json
"""
import argparse, glob, json, datetime as dt, collections as C
from zoneinfo import ZoneInfo
from utm_scheme import classify_lead, LI_AD_CHANNELS, LI_POSTTEXT
ET = ZoneInfo('America/New_York')


def lj(f):
    t = open(f).read(); return json.loads(t[t.find('{'):t.rfind('}') + 1])


def channel(s):
    if not s: return 'No source'
    ts = (s.get('trafficSource') or {}).get('name')
    if s.get('organic'): return 'Organic (probable LinkedIn)' if s.get('name') in ('li', 'linkedin') else 'Organic other'
    return {'linkedin': 'LinkedIn ads', 'facebook': 'Meta ads'}.get(ts, 'Other paid:' + str(ts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hyros', nargs='+', required=True); ap.add_argument('--contacts', nargs='+', required=True)
    ap.add_argument('--this', nargs=2, required=True); ap.add_argument('--prior', nargs=2, required=True); ap.add_argument('--d30', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(); d = dt.date.fromisoformat
    W = {'this': (d(a.this[0]), d(a.this[1])), 'prior': (d(a.prior[0]), d(a.prior[1])), 'd30': (d(a.d30), d(a.this[1]))}
    cs = {}
    for g in a.contacts:
        for f in glob.glob(g):
            x = lj(f); x = x.get('data', x)
            for c in x.get('contacts', []) + ([x['contact']] if isinstance(x.get('contact'), dict) else []): cs[c['id']] = c
    em = {}
    for c in sorted(cs.values(), key=lambda c: c.get('dateAdded') or ''):
        em.setdefault((c.get('email') or '').lower(), c)
        # 2026-11-27: also match additionalEmails (Hyros sometimes keeps a different booking email than the GHL primary email)
        for e2 in (c.get('additionalEmails') or []):
            e2 = e2.get('email') if isinstance(e2, dict) else e2
            if e2: em.setdefault(e2.lower(), c)
    calls = {}
    for f in a.hyros:
        for x in lj(f)['result']: calls[x.get('id') or (x['creationDate'], x['lead'].get('email'))] = x
    out = {w: C.Counter() for w in W}; people = []
    for x in calls.values():
        if 'Strategy' not in x['name'] or channel(x.get('lastSource')) != 'Organic (probable LinkedIn)': continue
        day = dt.datetime.strptime(x['creationDate'], '%a %b %d %H:%M:%S UTC %Y').replace(tzinfo=dt.timezone.utc).astimezone(ET).date()
        c = em.get((x['lead'].get('email') or '').lower())
        k = 'no_match' if c is None else ('posttext' if classify_lead(c)['ch'] == LI_POSTTEXT else 'tagged' if classify_lead(c)['ch'] in LI_AD_CHANNELS else 'kept_org')
        people.append([str(day), (x['lead'].get('firstName') or '').strip().title(), k])
        for w, (s, e) in W.items():
            if s <= day <= e: out[w][k] += 1
    res = {w: dict(v, li_org_to_li_ads=v['posttext'] + v['tagged']) for w, v in out.items()}
    res['_people'] = sorted(people)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({w: res[w] for w in W}))


if __name__ == '__main__':
    main()
