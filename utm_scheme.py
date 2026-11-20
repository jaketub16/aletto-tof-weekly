#!/usr/bin/env python3
"""Dual-scheme UTM helpers for GHL attributions and GA4 session rows.

Old LinkedIn paid (still live on bg2 EU 887084114, and all historical rows):
  utm_source=linkedin, utm_medium=<ad set name>, utm_campaign=<parent campaign>,
  utm_content=<ad name>, plus h_ad_id, lnk_id, h_ad_name, li_fat_id on the URL.

New LinkedIn paid (fr-winners-bg1 700616844 and fr-winners-bg2 US 732802984 as of 2026-11-13):
  utm_source=linkedin, utm_medium=paid_social, utm_campaign=<ad set name>,
  utm_term=<parent campaign>, utm_content=<ad name>, plus the same ids.

If utm_medium is a generic medium (paid_social, cpc, paid, social, email, sms, …),
the ad-set / campaign label lives in utm_campaign. Otherwise keep the old rule:
utm_medium holds that label. Ad name is utm_content, falling back to h_ad_name.

Treat as LinkedIn PAID (never organic): utm_source=linkedin + utm_medium=paid_social,
or any hit with h_ad_id / lnk_id / li_fat_id. Also the old scheme (linkedin + a
non-generic medium, i.e. an ad-set name).
"""
from urllib.parse import parse_qs, unquote, urlparse

GENERIC_MEDIUMS = frozenset({
    'paid_social', 'cpc', 'ppc', 'cpm', 'cpa', 'cpl', 'cpi',
    'paid', 'social', 'email', 'sms', 'organic', 'referral',
    'display', 'affiliate', 'banner', 'video', 'native',
    'paid_search',
})
# Generic mediums that mean paid traffic (not organic/email/sms/referral).
PAID_GENERIC_MEDIUMS = frozenset({
    'paid_social', 'cpc', 'ppc', 'cpm', 'cpa', 'cpl', 'cpi',
    'paid', 'display', 'paid_search',
})


def _norm_med(med):
    return (med or '').strip().lower().replace('-', '_').replace(' ', '_')


def is_generic_medium(med):
    m = _norm_med(med)
    return m in GENERIC_MEDIUMS or m.startswith('paid_')


def is_paid_generic_medium(med):
    m = _norm_med(med)
    return m in PAID_GENERIC_MEDIUMS or (m.startswith('paid_') and m not in ('paid_organic',))


def attr_qs(attr):
    """Parse UTM / Hyros / LinkedIn ids off pageUrl or url."""
    attr = attr or {}
    url = attr.get('pageUrl') or attr.get('url') or ''
    return {k: unquote(v[0]) for k, v in parse_qs(urlparse(url).query).items() if v}


def _get(attr, q, *keys):
    attr = attr or {}
    q = q or {}
    for k in keys:
        v = attr.get(k) or q.get(k)
        if v is not None and str(v).strip() and str(v).strip().lower() not in ('none', 'null'):
            return str(v).strip()
    return ''


def campaign_ad(attr):
    """Return (campaign_or_adset, ad_name) for either UTM scheme.

    Old: campaign/ad-set = utm_medium. New (generic medium): utm_campaign.
    Ad = utm_content, else h_ad_name.
    """
    q = attr_qs(attr)
    med = _get(attr, q, 'utmMedium', 'utm_medium')
    camp = _get(attr, q, 'utmCampaign', 'utm_campaign')
    ad = _get(attr, q, 'utmContent', 'utm_content', 'h_ad_name')
    if is_generic_medium(med):
        return camp, ad
    return med, ad


def campaign_from_ga4(row):
    """GA4 session row: campaign lives in sessionMedium (old) or sessionCampaignName (new)."""
    row = row or {}
    med = row.get('sessionMedium') or row.get('medium') or ''
    camp = row.get('sessionCampaignName') or row.get('sessionManualCampaignName') or row.get('campaign') or ''
    if is_generic_medium(med):
        return (camp or '').strip()
    return (med or '').strip()


def is_linkedin_paid(attr, source=''):
    """True when this attribution (or GHL source) is LinkedIn paid, never organic."""
    attr = attr or {}
    q = attr_qs(attr)
    url = attr.get('pageUrl') or attr.get('url') or ''
    us = _get(attr, q, 'utmSource', 'utm_source').lower()
    med = _get(attr, q, 'utmMedium', 'utm_medium')
    src = (source or '').strip().lower()
    # Meta ads also carry Hyros h_ad_id, so h_ad_id alone is not a LinkedIn signal.
    if us in ('fb_ad', 'facebook', 'fb', 'ig') or 'fbclid=' in url or 'fbclid' in url:
        return False
    # lnk_id and li_fat_id are LinkedIn-specific. h_ad_id counts only with a LinkedIn source
    # (or no conflicting source), so paid LinkedIn is never filed as organic.
    if q.get('lnk_id') or 'lnk_id=' in url or 'li_fat_id=' in url or 'li_fat_id' in url:
        return True
    if (q.get('h_ad_id') or 'h_ad_id=' in url) and us in ('linkedin', 'li', ''):
        return True
    if us == 'linkedin' and is_paid_generic_medium(med):
        return True
    if us == 'linkedin' and med and not is_generic_medium(med):
        return True
    # 2026-11-19: never use GHL's utmSessionSource label ('Paid Social', 'Social media', 'Direct traffic') as a signal.
    if src == 'linkedin' and (q.get('lnk_id') or 'li_fat_id' in url or is_paid_generic_medium(med) or (med and not is_generic_medium(med))):
        return True
    return False


# ---------------------------------------------------------------------------
# Lead channel for GHL contacts (2026-11-19, Jake approved reporting-only fix)
# ---------------------------------------------------------------------------
# Why: every /saasreport LinkedIn ad has a link in the POST TEXT (lnkd.in/eUvfBJqe -> goadstra.com/saasreport
# -> go.aletto.ai/saasreport, and lnkd.in/e83PihWj on 2013selling_v2_inmails). LinkedIn only adds the URL
# tracking parameters to the ad's destination link, so those clicks arrive with no UTMs and only a linkedin.com
# referrer. They are ad leads (dark ad posts, same US mix and qualified rate), not organic.
# Rules, in order:
#   1. Paid signals win, from ANY attribution (first touch first): LinkedIn paid (utm_source=linkedin with a paid
#      or ad-set medium, lnk_id, li_fat_id, h_ad_id with a LinkedIn source) or Meta (fb_ad/fbclid). A later paid
#      click beats an earlier organic/referral visit (Shy, 19 Nov). Then the new tracking custom fields.
#   2. No paid signal + referrer linkedin.com / lnkd.in / com.linkedin.android (first touch or the new referrer
#      field) + landing on /saasreport  =>  LI_POSTTEXT, counted inside LinkedIn ad leads, ad set/ad 'unattributed'.
#   3. '5 Ways' form source => organic. Else Other.
# GHL's utmSessionSource label is never used.
LI_ADS = 'LinkedIn ads'
META_ADS = 'Meta ads'
LI_POSTTEXT = 'LinkedIn Ads (post-text link, untracked)'
ORGANIC_5WAYS = 'Organic (5 Ways report)'
OTHER = 'Other'
UNATTRIBUTED = 'unattributed'
LI_AD_CHANNELS = (LI_ADS, LI_POSTTEXT)
LI_REFERRER_HOSTS = ('linkedin.com', 'lnkd.in', 'com.linkedin.android')
# New GHL contact custom fields (live 2026-11-18 ~21:45 Madrid)
CF_IDS = {'SS1rGyiAZhUMz7uPRWwU': 'utm_source', 'ndQ7bJ2nzt2srCXkQ4lq': 'utm_medium', 'MtiXmkHrCZTR8gV4lWNc': 'utm_campaign',
          'FOGZ6aL6Mw4WYu6poMD4': 'utm_content', 'qyiekIFiCE0fq4pbr0k6': 'utm_term', '0hgmf9iaQtLODcLfkMEu': 'referrer',
          'IgvD53McTKcGrYfxrrjY': 'landing_page', 'EVzuBhDTNIJ50xxFOgXz': 'lead_source_channel'}


def contact_fields(contact):
    """New tracking custom fields as {name: value}."""
    out = {}
    for f in (contact or {}).get('customFields') or []:
        k = CF_IDS.get(f.get('id'))
        if k and f.get('value') not in (None, ''):
            out[k] = str(f.get('value'))
    return out


def ordered_attributions(contact):
    """First touch first, then middle ones, last touch last."""
    att = [a for a in ((contact or {}).get('attributions') or []) if isinstance(a, dict)]
    first = [a for a in att if a.get('isFirst')]
    last = [a for a in att if a.get('isLast') and not a.get('isFirst')]
    mid = [a for a in att if a not in first and a not in last]
    return first + mid + last


def is_meta_paid(attr, source=''):
    attr = attr or {}
    q = attr_qs(attr)
    url = attr.get('pageUrl') or attr.get('url') or ''
    us = _get(attr, q, 'utmSource', 'utm_source').lower()
    med = _get(attr, q, 'utmMedium', 'utm_medium')
    if us in ('fb_ad', 'facebook') or 'fbclid' in url or 'fbc_id' in url or attr.get('utmFbclid'):
        return True
    if us in ('facebook', 'fb', 'ig', 'instagram', 'meta') and (is_paid_generic_medium(med) or (med and not is_generic_medium(med))):
        return True
    return (source or '').strip().lower() == 'fb_ad' and attr.get('isFirst')


def _host(u):
    u = (u or '').strip()
    if u.startswith('android-app://'):
        return u[len('android-app://'):].split('/')[0].lower()
    try:
        return (urlparse(u).hostname or '').lower()
    except Exception:
        return ''


def _is_li_referrer(u):
    h = _host(u)
    return any(h == d or h.endswith('.' + d) for d in LI_REFERRER_HOSTS)


def _path(u):
    try:
        return urlparse(u or '').path.rstrip('/') or '/'
    except Exception:
        return ''


def _camp_ad(a):
    """Ad set / ad, preferring the exact values on the landing URL (GHL capitalises utmCampaign, e.g. 'Fr-winners-...')."""
    q = attr_qs({'pageUrl': (a or {}).get('pageUrl') or ''})
    if q.get('utm_campaign') or q.get('utm_medium') or q.get('utm_content') or q.get('h_ad_name'):
        return campaign_ad({'pageUrl': a.get('pageUrl')})
    return campaign_ad(a)


def classify_lead(contact):
    """Return dict(ch, adset, ad, reason, attr) for one GHL contact. See rules above."""
    contact = contact or {}
    src = (contact.get('source') or '').strip()
    att = ordered_attributions(contact)
    cf = contact_fields(contact)
    # 1. paid signals from any attribution (first touch wins among paid ones)
    for a in att:
        if is_meta_paid(a, src):
            camp, ad = _camp_ad(a)
            return dict(ch=META_ADS, adset=camp, ad=ad, reason='meta_paid' + ('' if a.get('isFirst') else '_later_touch'), attr=a)
        if is_linkedin_paid(a, src):
            camp, ad = _camp_ad(a)
            return dict(ch=LI_ADS, adset=camp, ad=ad, reason='li_paid' + ('' if a.get('isFirst') else '_later_touch'), attr=a)
    cfs, cfm = cf.get('utm_source', '').lower(), cf.get('utm_medium', '')
    cfch = cf.get('lead_source_channel', '')
    if cfs == 'fb_ad' or cfch == 'Paid Social - Meta':
        camp = cf.get('utm_campaign') if is_generic_medium(cfm) or not cfm else cfm
        return dict(ch=META_ADS, adset=camp or '', ad=cf.get('utm_content', ''), reason='meta_custom_fields', attr=None)
    if (cfs == 'linkedin' and (is_paid_generic_medium(cfm) or (cfm and not is_generic_medium(cfm)))) or cfch == 'Paid Social - LinkedIn':
        camp = cf.get('utm_campaign') if is_generic_medium(cfm) or not cfm else cfm
        return dict(ch=LI_ADS, adset=camp or '', ad=cf.get('utm_content', ''), reason='li_custom_fields', attr=None)
    if src.lower() == 'fb_ad':
        return dict(ch=META_ADS, adset='', ad='', reason='meta_ghl_source', attr=att[0] if att else None)
    if src.lower() == 'linkedin':  # GHL source set from utm_source=linkedin by a form
        return dict(ch=LI_ADS, adset='', ad='', reason='li_ghl_source', attr=att[0] if att else None)
    # 2. post-text link: LinkedIn referrer + /saasreport, no UTMs/click ids anywhere
    first = att[0] if att else {}
    refs = [first.get('referrer') or '', cf.get('referrer', '')]
    lands = [first.get('url') or first.get('pageUrl') or '', cf.get('landing_page', '')]
    # only the first touch / first-touch fields matter here: later email/SMS visits (utm_source=email|sms) don't make it organic
    has_utm = bool(_get(first, attr_qs(first), 'utmSource', 'utm_source')) or bool(cfs)
    if not has_utm and any(_is_li_referrer(r) for r in refs) and any(_path(l) == '/saasreport' for l in lands if l):
        return dict(ch=LI_POSTTEXT, adset=UNATTRIBUTED, ad=UNATTRIBUTED, reason='li_referrer_saasreport_no_utm', attr=first)
    # 3. organic / other
    if '5 ways' in src.lower():
        return dict(ch=ORGANIC_5WAYS, adset='', ad='', reason='5ways_form_no_paid_signal', attr=first)
    return dict(ch=OTHER, adset='', ad='', reason='no_paid_signal', attr=first)
