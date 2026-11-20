#!/usr/bin/env python3
"""Unit + dry-run tests for dual-scheme UTM helpers. Writes nothing into pack or deck outputs."""
import copy, collections as C, json, glob, os, sys, datetime as dt, tempfile, subprocess
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from utm_scheme import (
    campaign_ad, is_linkedin_paid, is_generic_medium, campaign_from_ga4,
    is_paid_generic_medium,
)

fail = 0

def chk(name, got, want):
    global fail
    ok = got == want
    fail += (not ok)
    print(('ok  ' if ok else 'FAIL'), name, '=>', got if ok else f'got {got!r} want {want!r}')


# ---- unit: campaign_ad ----
old = {
    'utmSource': 'linkedin',
    'utmMedium': 'fr-winners-bg2-ss-sd-es',
    'utmCampaign': 'Aletto-fr/lt-winners',
    'utmContent': 'deadcold',
    'utmSessionSource': 'Paid Social',
    'pageUrl': 'https://go.aletto.ai/saasreport?li_fat_id=abc&utm_campaign=aletto-fr/lt-winners&utm_medium=fr-winners-bg2-ss-sd-es&h_ad_id=1534286044&lnk_id=732802984&h_ad_name=deadcold&utm_content=deadcold&utm_source=linkedin',
}
new = {
    'utmSource': 'linkedin',
    'utmMedium': 'paid_social',
    'utmCampaign': 'fr-winners-bg1-hc-rm-ml',
    'utmTerm': 'Aletto-fr/lt-winners',
    'utmContent': 'timmoran',
    'utmSessionSource': 'Paid Social',
    'pageUrl': 'https://go.aletto.ai/freetraining-1-7481?utm_source=linkedin&utm_medium=paid_social&utm_campaign=fr-winners-bg1-hc-rm-ml&utm_term=Aletto-fr/lt-winners&utm_content=timmoran&h_ad_id=1294085644&lnk_id=700616844&h_ad_name=timmoran',
}
# ids only, no utm fields on the object (parse URL)
ids_only = {
    'pageUrl': 'https://go.aletto.ai/saasreport?h_ad_id=1&lnk_id=700419024&h_ad_name=consortia&utm_source=linkedin&utm_medium=paid_social&utm_campaign=rt-vsl&utm_content=consortia',
}
organic = {
    'utmSource': 'linkedin', 'utmMedium': 'organic', 'utmCampaign': 'quill-post', 'utmContent': 'hook-a',
    'pageUrl': 'https://go.aletto.ai/saasreport?utm_source=linkedin&utm_medium=organic&utm_campaign=quill-post&utm_content=hook-a',
    'referrer': 'https://www.linkedin.com',
}
email = {'utmSource': 'ghl', 'utmMedium': 'email', 'utmCampaign': 'nurture-vsl', 'utmContent': 'week2'}
meta_old = {'utmSource': 'fb_ad', 'utmMedium': 'FR-WINNERS2', 'utmCampaign': 'Cbo-fr-hqc', 'utmContent': 'static-a'}

chk('old camp/ad', campaign_ad(old), ('fr-winners-bg2-ss-sd-es', 'deadcold'))
chk('new camp/ad', campaign_ad(new), ('fr-winners-bg1-hc-rm-ml', 'timmoran'))
chk('ids-only camp/ad', campaign_ad(ids_only), ('rt-vsl', 'consortia'))
chk('organic uses utm_campaign', campaign_ad(organic), ('quill-post', 'hook-a'))
chk('email uses utm_campaign', campaign_ad(email), ('nurture-vsl', 'week2'))
chk('meta old stays medium=adset', campaign_ad(meta_old), ('FR-WINNERS2', 'static-a'))
chk('ad fallback h_ad_name', campaign_ad({'pageUrl': 'https://x/?utm_medium=paid_social&utm_campaign=rt-vsl&h_ad_name=reel'}), ('rt-vsl', 'reel'))

chk('old is paid', is_linkedin_paid(old), True)
chk('new is paid', is_linkedin_paid(new), True)
chk('ids-only is paid', is_linkedin_paid(ids_only), True)
chk('organic is not paid', is_linkedin_paid(organic), False)
chk('email is not LI paid', is_linkedin_paid(email), False)
chk('meta with h_ad_id is not LI paid', is_linkedin_paid({'utmSource':'fb_ad','utmMedium':'FR-WINNERS2','utmCampaign':'Cbo-fr-hqc','utmContent':'STATIC-a','pageUrl':'https://go.aletto.ai/saasreport?utm_source=fb_ad&utm_medium=FR-WINNERS2&h_ad_id=999&utm_content=STATIC-a'}), False)
chk('h_ad_id forces paid even without source', is_linkedin_paid({'pageUrl': 'https://x/?h_ad_id=9'}), True)
chk('lnk_id forces paid', is_linkedin_paid({'pageUrl': 'https://x/?lnk_id=700616844'}), True)

chk('ga4 old campaign from medium', campaign_from_ga4({'sessionSource': 'linkedin', 'sessionMedium': 'fr-winners-bg2-ss-sd-es'}), 'fr-winners-bg2-ss-sd-es')
chk('ga4 new campaign from campaign name', campaign_from_ga4({'sessionSource': 'linkedin', 'sessionMedium': 'paid_social', 'sessionCampaignName': 'fr-winners-bg1-hc-rm-ml'}), 'fr-winners-bg1-hc-rm-ml')
chk('generic paid_social', is_generic_medium('paid_social') and is_paid_generic_medium('paid_social'), True)
chk('ad-set name not generic', is_generic_medium('fr-winners-bg1-hc-rm-ml'), False)

# ---- dry-run leads.py against existing pack (old-scheme rows must match) ----
PACK = '/workspace/friday-pack-2026-11-06-12'
sys.path.insert(0, PACK)
# Recompute the same way leads.py does, without writing.
import importlib.util
# Don't import leads.py (it writes). Re-run the loop inline.
from common import lj
ET = ZoneInfo('America/New_York')
W1 = (dt.date(2026, 11, 6), dt.date(2026, 11, 12)); W0 = (dt.date(2026, 10, 30), dt.date(2026, 11, 5))
cs = {}
for f in sorted(glob.glob(PACK + '/raw/ct/p*.json')):
    d = lj(f); d = d.get('data', d)
    for c in d['contacts']:
        cs[c['id']] = c
rows = []
for c in cs.values():
    a = dt.datetime.fromisoformat(c['dateAdded'].replace('Z', '+00:00')).astimezone(ET).date()
    wk = 'this' if W1[0] <= a <= W1[1] else 'prior' if W0[0] <= a <= W0[1] else None
    if not wk: continue
    tags = set(c.get('tags', [])); src = (c.get('source') or ''); att = (c.get('attributions') or [])
    first = next((x for x in att if x.get('isFirst')), att[0] if att else {})
    url = (first.get('pageUrl') or first.get('url') or '')
    rep = ('saasreport' in tags) or ('saasreport' in url) or ('5 ways' in src.lower())
    if not rep or 'hiring' in tags: continue
    us = (first.get('utmSource') or '').lower()
    if 'li_fat_id' in url or us == 'linkedin' or src == 'linkedin' or is_linkedin_paid(first, src):
        ch = 'LinkedIn ads'
    elif 'fbclid' in url or 'fbc_id' in url or us in ('fb_ad', 'facebook') or src == 'fb_ad':
        ch = 'Meta ads'
    elif '5 ways' in src.lower():
        ch = 'Organic (5 Ways report)'
    else:
        ch = 'Other'
    camp, ad = campaign_ad(first)
    rows.append(dict(wk=wk, ch=ch, camp=camp or None, ut=ad or first.get('utmContent'), email=(c.get('email') or '').lower()))

prev_rows = json.load(open(PACK + '/leads.json'))
prev = {(r['email'], r['wk']): r for r in prev_rows}
# compare channel + campaign + ad for every previously saved row
mismatch = []
for r in rows:
    p = prev.get((r['email'], r['wk']))
    if not p:
        mismatch.append(('extra', r['email'], r['wk'], r['ch'], r['camp']))
        continue
    # old camp stored None vs missing: leads.py used first.get('utmMedium') which can be None
    old_camp = p.get('camp')
    new_camp = r['camp']
    # JSON may have had null
    if old_camp in (None, 'null', ''):
        old_camp = None
    if new_camp in (None, 'null', ''):
        new_camp = None
    ut_old, ut_new = (p.get('ut') or None), (r['ut'] or None)
    ut_ok = ut_old == ut_new or (ut_old is None and ut_new)  # allowed: fill ad from h_ad_name when utm_content was empty
    if p['ch'] != r['ch'] or old_camp != new_camp or not ut_ok:
        mismatch.append(('diff', r['email'], r['wk'], (p['ch'], old_camp, p.get('ut')), (r['ch'], new_camp, r['ut'])))

# rows that disappeared
new_keys = {(r['email'], r['wk']) for r in rows}
for k, p in prev.items():
    if k not in new_keys:
        mismatch.append(('missing',) + k)

chk('leads row count', len(rows), len(prev_rows))
chk('leads old-scheme rows unchanged', len(mismatch), 0)
if mismatch[:5]:
    print('  sample mismatches:', mismatch[:5])

S_prev = json.load(open(PACK + '/leads_summary.json'))
for w in ('this', 'prior'):
    R = [r for r in rows if r['wk'] == w]
    by = dict(C.Counter(r['ch'] for r in R))
    li_camp = dict(C.Counter(r['camp'] for r in R if r['ch'] == 'LinkedIn ads'))
    # Counter will use None; previous JSON used "null" string? check
    prev_camp = S_prev[w]['li_camp']
    # normalize null key
    li_camp_n = {('null' if k is None else k): v for k, v in li_camp.items()}
    chk(f'leads_summary {w} by_ch', by, S_prev[w]['by_ch'])
    chk(f'leads_summary {w} li_camp', li_camp_n, prev_camp)

# synthetic new-scheme contact mixed into the same loop
syn_first = new
syn_ch = 'LinkedIn ads' if is_linkedin_paid(syn_first) else 'WRONG'
syn_camp, syn_ad = campaign_ad(syn_first)
chk('synthetic new-scheme channel', syn_ch, 'LinkedIn ads')
chk('synthetic new-scheme camp is ad set, not paid_social', syn_camp, 'fr-winners-bg1-hc-rm-ml')
chk('synthetic new-scheme ad', syn_ad, 'timmoran')
# and would not be lumped under organic
chk('synthetic not organic', syn_ch != 'Organic (5 Ways report)' and syn_camp != 'paid_social', True)

# ---- ga4_extract dry run (old raw has no sessionCampaignName; buckets must match) ----
raw = '/workspace/aletto-tof-weekly/ga4_raw/2026-11-13'
data = '/workspace/aletto-tof-weekly/weeks/2026-11-13/data.json'
prev_g = json.load(open('/workspace/aletto-tof-weekly/weeks/2026-11-13/ga4.json'))
out = tempfile.mkdtemp(prefix='ga4_dry_') + '/ga4.json'
subprocess.check_call(['python3', '/workspace/aletto-tof-weekly/ga4_extract.py', '--raw', raw, '--data', data, '--out', out],
                      cwd='/workspace/aletto-tof-weekly')
got_g = json.load(open(out))
# compare steps and by_source user/book numbers; allow extra tracking keys and 'campaign' on detail rows
for w in ('this', 'prior', 'd30'):
    chk(f'ga4 steps {w} vsl_users', got_g['steps'][w]['vsl_users'], prev_g['steps'][w]['vsl_users'])
    chk(f'ga4 steps {w} books', got_g['steps'][w].get('books'), prev_g['steps'][w].get('books'))
# by_source buckets (ignore possible new keys inside rows)
for a, b in zip(got_g['by_source'], prev_g['by_source']):
    chk(f"ga4 by_source {a['key']} this vsl", a['this']['vsl_users'], b['this']['vsl_users'])
# old-scheme campaigns still come from medium, so li_ads_campaigns should equal the old medium list (minus empty)
old_meds = [m for m in prev_g['tracking']['li_ads_campaign_in_medium'] if m]
chk('ga4 li_ads_campaign_in_medium unchanged', got_g['tracking']['li_ads_campaign_in_medium'], prev_g['tracking']['li_ads_campaign_in_medium'])
chk('ga4 li_ads_campaigns == old mediums (no campaign dim in this raw)', got_g['tracking']['li_ads_campaigns'], sorted(old_meds))
# synthetic GA4 new-scheme row
from ga4_extract import bucket
chk('ga4 bucket new medium still li_ads', bucket('linkedin', 'paid_social'), 'li_ads')
chk('ga4 bucket old source still li_ads', bucket('linkedin', 'fr-winners-bg2-ss-sd-es'), 'li_ads')
chk('ga4 bucket organic referrer still li_org', bucket('linkedin.com', 'referral'), 'li_org')
chk('ga4 campaign new scheme', campaign_from_ga4({'sessionSource': 'linkedin', 'sessionMedium': 'paid_social', 'sessionCampaignName': 'static-test-US'}), 'static-test-US')

# ---- content_extract net() dry-run: re-apply new net() to existing pack contacts vs saved content.json ----
# Inline the updated net() (content_extract.py is not import-safe).
def net(x):
    if not x: return 'No attribution'
    ref = (x.get('referrer') or '').lower(); ua = x.get('userAgent') or ''; us = (x.get('utmSource') or '').lower(); u = (x.get('pageUrl') or x.get('url') or '').lower()
    host = urlparse(ref).netloc or ref
    if is_linkedin_paid(x) or 'li_fat_id' in u: return 'Paid LinkedIn'
    if us in ('fb_ad',) or ('fbclid' in u and ('utm_' in u or us == 'facebook')): return 'Paid Meta'
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

# previous net() for comparison
def net_old(x):
    if not x: return 'No attribution'
    ref = (x.get('referrer') or '').lower(); ua = x.get('userAgent') or ''; us = (x.get('utmSource') or '').lower(); u = (x.get('pageUrl') or x.get('url') or '').lower()
    if 'li_fat_id' in u or (us == 'linkedin' and x.get('utmCampaign')): return 'Paid LinkedIn'
    if us in ('fb_ad',) or ('fbclid' in u and ('utm_' in u or us == 'facebook')): return 'Paid Meta'
    if 'linkedin' in ref or 'lnkd' in ref or 'LinkedInApp' in ua or 'linkedin' in us: return 'LinkedIn organic'
    return 'other-or-later'

# count report-lead first-touch buckets this week vs content.json, and vs old net
CJ = json.load(open('/workspace/aletto-tof-weekly/weeks/2026-11-13/content.json'))
start = dt.date(2026, 11, 6); end = dt.date(2026, 11, 12)
changed = C.Counter(); report_first = C.Counter()
for c in cs.values():
    a = dt.datetime.fromisoformat(c['dateAdded'].replace('Z', '+00:00')).astimezone(ET).date()
    if not (start <= a <= end): continue
    att = c.get('attributions') or []
    fi = next((x for x in att if x.get('isFirst')), att[0] if att else {})
    tags = set(c.get('tags', [])); from urllib.parse import urlparse as _up; page = _up(fi.get('pageUrl') or fi.get('url') or '').path
    if 'hiring' in tags: continue
    rep = 'saasreport' in tags or 'saasreport' in page or '5 ways' in (c.get('source') or '').lower()
    if not rep: continue
    n, o = net(fi), net_old(fi)
    if n != o and o in ('Paid LinkedIn', 'LinkedIn organic') or n in ('Paid LinkedIn', 'LinkedIn organic') and n != o:
        changed[(o, n)] += 1
    report_first[n] += 1
chk('content report_first matches saved (or report delta below)', dict(report_first), CJ['ghl']['this']['report_first'])
print('content_extract first-touch deltas vs previous net() (this week report leads):', dict(changed) or 'none')
# synthetic
chk('content net() new-scheme is Paid LinkedIn', net(new), 'Paid LinkedIn')
chk('content net() organic stays organic', net(organic), 'LinkedIn organic')
chk('content net() old-scheme stays Paid LinkedIn', net(old), 'Paid LinkedIn')

# ---- daily-brief style label (10-23) ----
def brief_label(a):
    camp, cont = campaign_ad(a)
    u = (a.get('utmSource') or '').lower()
    if u in ('fb_ad', 'facebook', 'fb', 'ig'):
        return f"Meta {camp} · {cont}".strip(' ·')
    if u == 'linkedin' or is_linkedin_paid(a):
        return f"LinkedIn paid {camp} · {cont}".strip(' ·')
    return 'other'

# old-scheme label must still show the ad set (from medium), not parent campaign
chk('brief old-scheme label', brief_label(old), 'LinkedIn paid fr-winners-bg2-ss-sd-es · deadcold')
chk('brief new-scheme label', brief_label(new), 'LinkedIn paid fr-winners-bg1-hc-rm-ml · timmoran')
# previous 10-23 logic would have used medium from URL = paid_social for the new row
url_med = 'paid_social'
old_logic_new = f"LinkedIn paid {url_med} · timmoran"
chk('brief new-scheme is not paid_social', brief_label(new) != old_logic_new, True)


# ---- 2026-11-19 lead channel rules ----
from utm_scheme import classify_lead, LI_ADS, LI_POSTTEXT, ORGANIC_5WAYS, META_ADS, OTHER
posttext = {'source': '5 Ways SaaS New', 'attributions': [{'isFirst': True, 'url': 'https://go.aletto.ai/saasreport', 'pageUrl': 'https://go.aletto.ai/saasreport',
            'referrer': 'https://www.linkedin.com', 'utmSessionSource': 'Social media', 'medium': 'form'}]}
r = classify_lead(posttext)
chk('post-text link => LI post-text', r['ch'], LI_POSTTEXT)
chk('post-text ad set unattributed', (r['adset'], r['ad']), ('unattributed', 'unattributed'))
android = {'source': '5 Ways SaaS New', 'attributions': [{'isFirst': True, 'url': 'https://go.aletto.ai/saasreport', 'referrer': 'android-app://com.linkedin.android'}]}
chk('android LinkedIn app referrer', classify_lead(android)['ch'], LI_POSTTEXT)
cf_only = {'source': '5 Ways SaaS New', 'attributions': [{'isFirst': True, 'url': 'https://go.aletto.ai/saasreport?al_ch=Organic+Social'}],
           'customFields': [{'id': '0hgmf9iaQtLODcLfkMEu', 'value': 'https://www.linkedin.com/'}, {'id': 'EVzuBhDTNIJ50xxFOgXz', 'value': 'Organic Social'},
                            {'id': 'IgvD53McTKcGrYfxrrjY', 'value': 'https://go.aletto.ai/saasreport'}]}
chk('new referrer field counts', classify_lead(cf_only)['ch'], LI_POSTTEXT)
organic_vsl = {'source': '5 Ways SaaS New', 'attributions': [{'isFirst': True, 'url': 'https://go.aletto.ai/freetraining-booking-6842', 'referrer': 'https://www.linkedin.com'}]}
chk('LinkedIn referrer NOT on /saasreport stays organic', classify_lead(organic_vsl)['ch'], ORGANIC_5WAYS)
li_tagged_org = {'source': 'li', 'attributions': [{'isFirst': True, 'url': 'https://go.aletto.ai/saasreport', 'pageUrl': 'https://go.aletto.ai/saasreport?utm_source=li&utm_medium=jfr', 'utmSource': 'li', 'utmMedium': 'jfr', 'referrer': 'https://www.linkedin.com'}]}
chk('tagged personal link (li/jfr) not swallowed', classify_lead(li_tagged_org)['ch'], OTHER)
later = {'source': '5 Ways SaaS New', 'attributions': [
    {'isFirst': True, 'url': 'https://go.aletto.ai/saasreport', 'referrer': 'https://www.linkedin.com', 'utmSessionSource': 'Social media'},
    {'isLast': True, 'url': 'https://go.aletto.ai/saasreport', 'pageUrl': 'https://go.aletto.ai/saasreport?utm_source=linkedin&utm_medium=paid_social&utm_campaign=fr-winners-bg2-ss-sd-es&utm_content=coldgraveyard&li_fat_id=x&lnk_id=732802984',
     'utmSource': 'linkedin', 'utmMedium': 'paid_social', 'utmCampaign': 'fr-winners-bg2-ss-sd-es', 'utmContent': 'coldgraveyard', 'utmSessionSource': 'Direct traffic'}]}
r = classify_lead(later)
chk('later paid click beats earlier organic', (r['ch'], r['adset'], r['ad']), (LI_ADS, 'fr-winners-bg2-ss-sd-es', 'coldgraveyard'))
shy = {'source': 'linkedin', 'attributions': [{'isFirst': True, 'url': 'https://go.aletto.ai/saasreport', 'utmSessionSource': 'Direct traffic',
       'pageUrl': 'https://go.aletto.ai/saasreport?al_ch=Organic+Social&li_fat_id=x&utm_campaign=fr-winners-bg2-ss-sd-es&utm_medium=paid_social&lnk_id=732802984&utm_content=coldgraveyard&utm_source=linkedin'}],
       'customFields': [{'id': 'EVzuBhDTNIJ50xxFOgXz', 'value': 'Organic Social'}]}
chk('UTMs beat stale Organic Social field (Shy)', classify_lead(shy)['ch'], LI_ADS)
label_only = {'source': '5 Ways SaaS New', 'attributions': [{'isFirst': True, 'url': 'https://go.aletto.ai/', 'utmSessionSource': 'Paid Social'}]}
chk('GHL Paid Social label alone is ignored', classify_lead(label_only)['ch'], ORGANIC_5WAYS)
oldsch = {'source': 'linkedin', 'attributions': [{'isFirst': True, 'utmSource': 'linkedin', 'utmMedium': 'fr-winners-bg2-ss-sd-es-eu', 'utmCampaign': 'aletto-fr/lt-winners', 'utmContent': 'deadcold',
          'pageUrl': 'https://go.aletto.ai/saasreport?utm_source=linkedin&utm_medium=fr-winners-bg2-ss-sd-es-eu&lnk_id=1'}]}
chk('old scheme ad set from utm_medium fallback', classify_lead(oldsch)['adset'], 'fr-winners-bg2-ss-sd-es-eu')
meta = {'source': 'fb_ad', 'attributions': [{'isFirst': True, 'utmSource': 'fb_ad', 'utmMedium': 'paid_social', 'utmCampaign': 'ABO', 'utmContent': 'x', 'referrer': 'https://www.linkedin.com', 'url': 'https://go.aletto.ai/saasreport'}]}
chk('Meta stays Meta', classify_lead(meta)['ch'], META_ADS)
later_email = {'source': '5 Ways SaaS New', 'attributions': [{'isFirst': True, 'url': 'https://go.aletto.ai/saasreport', 'referrer': 'https://www.linkedin.com'},
               {'isLast': True, 'url': 'https://go.aletto.ai/preferences', 'pageUrl': 'https://go.aletto.ai/preferences?utm_source=email', 'utmSource': 'email'}]}
chk('later email visit does not block post-text rule', classify_lead(later_email)['ch'], LI_POSTTEXT)

# ---- 2026-11-19: GA4 landing-page split + Hyros book re-split (ga4_extract.py). Uses a real GA4 pull as fixture if present.
import os, json as _json, shutil, subprocess, tempfile
FIX = os.environ.get('GA4_FIXTURE', '/workspace/ga4-landing-2026-11-19')
if os.path.isdir(os.path.join(FIX, 'raw')) and os.path.exists(os.path.join(FIX, 'raw', 'src_landing.json')):
    HERE = os.path.dirname(os.path.abspath(__file__))
    def _run(drop=(), landing=None, books=None):
        d = tempfile.mkdtemp(); r = os.path.join(d, 'raw'); shutil.copytree(os.path.join(FIX, 'raw'), r, ignore=shutil.ignore_patterns('ghl_lookups'))
        for f in drop:
            if os.path.exists(os.path.join(r, f)): os.remove(os.path.join(r, f))
        if landing is not None: _json.dump(landing, open(os.path.join(r, 'src_landing.json'), 'w'))
        if books is not None: _json.dump(books, open(os.path.join(r, 'books_resplit.json'), 'w'))
        subprocess.run([sys.executable, os.path.join(HERE, 'ga4_extract.py'), '--raw', r, '--data', os.path.join(FIX, 'data.json'), '--out', os.path.join(d, 'g.json')], check=True, capture_output=True)
        G = _json.load(open(os.path.join(d, 'g.json'))); shutil.rmtree(d)
        return {x['key']: x for x in G['by_source']}, G
    def _tot(B, w, m): return sum((B[k][w].get(m) or 0) for k in B)
    base, _ = _run(drop=('src_landing.json', 'books_resplit.json'))
    new, G = _run(drop=('books_resplit.json',))
    for w in ('this', 'prior', 'd30'):
        chk(f'landing split keeps VSL total ({w})', _tot(new, w, 'vsl_users'), _tot(base, w, 'vsl_users'))
        chk(f'landing split only moves li_org->li_ads ({w})', new['li_org'][w]['vsl_users'] - base['li_org'][w]['vsl_users'], -(new['li_ads'][w]['vsl_users'] - base['li_ads'][w]['vsl_users']))
        chk(f'landing split leaves Meta alone ({w})', new['meta_ads'][w]['vsl_users'], base['meta_ads'][w]['vsl_users'])
    chk('(not set)/VSL/home landings keep some organic (d30)', new['li_org']['d30']['vsl_users'] > 0, True)
    L = _json.load(open(os.path.join(FIX, 'raw', 'src_landing.json')))
    home = _json.loads(_json.dumps(L))
    for row in home['rows']:
        if row['dimensionValues'][2]['value'].split('?')[0].rstrip('/') == '/saasreport': row['dimensionValues'][2]['value'] = '/'
    h, _ = _run(drop=('books_resplit.json',), landing=home)
    chk('LinkedIn referrals landing on home page stay organic', (h['li_org']['d30']['vsl_users'], h['li_ads']['d30']['vsl_users']), (base['li_org']['d30']['vsl_users'], base['li_ads']['d30']['vsl_users']))
    b, _ = _run(books={'this': {'li_org_to_li_ads': 2}, 'prior': {'li_org_to_li_ads': 99}, 'd30': {'li_org_to_li_ads': 3}})
    chk('book re-split keeps book total (this)', _tot(b, 'this', 'books'), _tot(new, 'this', 'books'))
    chk('book re-split moves 2 (this)', b['li_ads']['this']['books'] - new['li_ads']['this']['books'], 2)
    chk('book re-split capped at organic books (prior)', b['li_org']['prior']['books'], 0)
else:
    print('skip GA4 landing tests (no fixture at', FIX, ')')

print('PASS', 'all' if fail == 0 else f'{fail} failed')
sys.exit(1 if fail else 0)
