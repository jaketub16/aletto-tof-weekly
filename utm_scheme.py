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
    sess = _get(attr, q, 'utmSessionSource', 'sessionSource', 'session_source')
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
    if us == 'linkedin' and sess.lower().startswith('paid'):
        return True
    if src == 'linkedin' and (q.get('lnk_id') or 'li_fat_id' in url or is_paid_generic_medium(med) or (med and not is_generic_medium(med))):
        return True
    return False
