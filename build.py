#!/usr/bin/env python3
"""Build the Aletto Friday top-of-funnel deck.

  python3 build.py weeks/2026-11-13          # builds /2026-11-13/index.html, root index.html (latest) and /archive/
  python3 build.py --all                     # rebuild every week in weeks/

Each week folder holds data.json (from extract.py, numbers only) and story.json (the words: verdict,
winners/losers, fatigue, recommendations, gaps). Style = the Aletto Apple-glass deck system
(assets/base.css from the 2026 YTD deck + assets/presenter.css from the sales scorecard + assets/deck.css).
"""
import base64, glob, html, json, os, sys

R = os.path.dirname(os.path.abspath(__file__))
A = lambda p: open(os.path.join(R, 'assets', p)).read()
E = html.escape


def money(v, dec=0, est=False):
    if v is None: return '—'
    s = ('$' + format(round(v, dec) if dec else round(v), ',.%df' % dec))
    return ('~' + s) if est else s


def pct(a, b):
    if not b: return 'new'
    p = round((a - b) / b * 100)
    return ('+' if p > 0 else '') + str(p) + '%'


def delta(a, b, good='up', fmt=str, label='last week'):
    if b is None: return ''
    if a == b: cls, arr = 'fl0', '→'
    else:
        upish = a > b
        cls = ('up' if (upish == (good == 'up')) else 'dn') if good != 'none' else 'fl0'
        arr = '▲' if upish else '▼'
    return f'<div class="deltas"><span class="{cls}">{arr} {pct(a, b) if b else ""}</span><span>{label} {fmt(b)}</span></div>'


def ch_short(c):
    return {'Organic (probable LinkedIn)': 'Organic (LinkedIn)', 'Organic (5 Ways report)': 'Organic "5 Ways"'}.get(c, c)


def build(wdir):
    D = json.load(open(os.path.join(wdir, 'data.json')))
    S = json.load(open(os.path.join(wdir, 'story.json')))
    GP = os.path.join(wdir, 'ga4.json')
    GA = json.load(open(GP)) if os.path.exists(GP) else None   # GA4 VSL throughput (ga4_extract.py)
    date = S['date']
    T, P = 'this', 'prior'
    sp = D['spend']
    meta = sp['meta_est']
    tot_t, tot_p = sp['total'][T], sp['total'][P]
    li_t, li_p = sp['li'][T], sp['li'][P]
    lt, lp = D['li_total'][T], D['li_total'][P]
    bk_t, bk_p = D['books'][T], D['books'][P]
    ld_t, ld_p = D['leads'][T], D['leads'][P]
    fn_t, fn_p = D['funnel'][T], D['funnel'][P]
    org = lambda b, k: b['by_ch'].get('Organic (probable LinkedIn)', {}).get(k, 0) + b['by_ch'].get('Organic other', {}).get(k, 0)
    chb = lambda b, c, k: b['by_ch'].get(c, {}).get(k, 0)
    sc = lambda b, c: (b['scopes_by_ch'] or {}).get(c, 0)
    per = lambda s, n: (s / n) if n else None

    # source economics table rows: label, spend this, prior, est?, books t/p, q t/p, scopes t/p
    src_rows = [
        ('All sources', tot_t, tot_p, True, bk_t['strategy'], bk_p['strategy'], bk_t['q'], bk_p['q'], bk_t['scopes'], bk_p['scopes']),
        ('LinkedIn ads', li_t, li_p, False, chb(bk_t, 'LinkedIn ads', 'books'), chb(bk_p, 'LinkedIn ads', 'books'), chb(bk_t, 'LinkedIn ads', 'q'), chb(bk_p, 'LinkedIn ads', 'q'), sc(bk_t, 'LinkedIn ads'), sc(bk_p, 'LinkedIn ads')),
        ('Meta ads', meta[T], meta[P], True, chb(bk_t, 'Meta ads', 'books'), chb(bk_p, 'Meta ads', 'books'), chb(bk_t, 'Meta ads', 'q'), chb(bk_p, 'Meta ads', 'q'), sc(bk_t, 'Meta ads'), sc(bk_p, 'Meta ads')),
        ('Organic (all)', None, None, False, org(bk_t, 'books'), org(bk_p, 'books'), org(bk_t, 'q'), org(bk_p, 'q'), sc(bk_t, 'Organic (probable LinkedIn)') + sc(bk_t, 'Organic other'), sc(bk_p, 'Organic (probable LinkedIn)') + sc(bk_p, 'Organic other')),
        ('No source', None, None, False, chb(bk_t, 'No source', 'books'), chb(bk_p, 'No source', 'books'), chb(bk_t, 'No source', 'q'), chb(bk_p, 'No source', 'q'), sc(bk_t, 'No source'), sc(bk_p, 'No source')),
    ]
    logo = 'data:image/png;base64,' + base64.b64encode(open(os.path.join(R, 'assets/aletto_white.png'), 'rb').read()).decode()
    N = [0]

    def top(k):
        N[0] += 1
        return f'<div class="top"><span class="kicker">{N[0]:02d} · {k}</span><img src="{logo}" alt="Aletto"></div>'

    def notes(*li):
        return '<aside class="sn"><ul>' + ''.join(f'<li>{x}</li>' for x in li) + '</ul></aside>'

    def kpi(label, val, d='', tag='', color=''):
        return f'<div class="glass card kpi"><div class="lbl">{label}{tag}</div><div class="v" style="{color}">{val}</div>{d}</div>'

    EST = '<span class="tag est">estimate</span>'
    slides = []

    # 1 title
    slides.append(f'''<section class="slide" data-title="Title">{top('Top of funnel · ' + S['title_date'])}
<div class="title-wrap"><div class="kicker" style="color:var(--blu)">Friday marketing pack</div>
<h1>Top of funnel<span class="dot">.</span><br>{E(S['week_label'])}</h1>
<p class="sub" style="max-width:900px">Spend, leads, booked calls and Scopes by source, compared with {E(S['prior_label'])}. LinkedIn numbers are actuals. Meta spend is an estimate while the account is locked.</p>
<div><span class="chip">← → or swipe to move</span><span class="chip">N for speaker notes</span><span class="chip"><a href="../archive/" style="color:inherit">Past weeks →</a></span></div></div>
<div class="src">Sources: LinkedIn Ads (account 513100372), Hyros booked calls (last touch), GHL contacts and tags, Metricool + Zernio (content). Read-only pull, Fri Nov 13. Prospects shown as first name + last initial.</div>
{notes('Same week window as every Friday pack: Friday to Thursday, Eastern time.', 'Every number ties to the pack files; Meta spend is the standing ~$190/day estimate.')}</section>''')

    # 2 week in one slide
    k = ''.join([
        kpi('Total spend', money(tot_t, est=True), delta(tot_t, tot_p, 'none', lambda v: money(v, est=True)), EST),
        kpi('LinkedIn clicks', f'{lt["clk"]:,}', delta(lt['clk'], lp['clk'], 'up', lambda v: f'{v:,}')),
        kpi('Free-report leads', f'{ld_t["total"]}', delta(ld_t['total'], ld_p['total'])),
        kpi('Strategy calls booked', f'{bk_t["strategy"]}', delta(bk_t['strategy'], bk_p['strategy'])),
        kpi('Qualified calls', f'{bk_t["q"]}', delta(bk_t['q'], bk_p['q']), color='color:var(--grn)'),
        kpi('Scopes booked', f'{bk_t["scopes"]}', delta(bk_t['scopes'], bk_p['scopes']), color='color:var(--amb)'),
        kpi('Cost per book', money(tot_t / bk_t['strategy'], est=True), delta(tot_t / bk_t['strategy'], tot_p / bk_p['strategy'], 'down', lambda v: money(v, est=True))),
        kpi('Cost per qualified', money(tot_t / bk_t['q'], est=True), delta(tot_t / bk_t['q'], tot_p / bk_p['q'], 'down', lambda v: money(v, est=True))),
    ])
    fl = ''.join(f'<div class="glass card flag {c}"><b>{t}</b><p>{p}</p></div>' for c, t, p in S['verdict_flags'])
    slides.append(f'''<section class="slide" data-title="The week">{top('The week in one slide')}
<h2>{S['verdict_h']}</h2><p class="sub">{S['verdict_sub']}</p>
<div class="col fill" style="justify-content:center;gap:18px"><div class="grid g4 big4">{k}</div><div class="grid g3">{fl}</div></div>
<div class="src">Cost per book / qualified use total spend including the Meta estimate. Last week's calls have had a week longer to cancel, so cancels aren't compared.</div>
{notes('Lead with the verdict: qualified and Scopes up, spend +4%.', 'LinkedIn paid is the problem channel this week; Meta + organic carried it.')}</section>''')

    # 3 spend & budgets
    bud = {b['name']: b['daily'] for b in D['budgets_now']}
    prosp = sum(v for n, v in bud.items() if n != 'rt-vsl')
    slides.append(f'''<section class="slide" data-title="Spend & budgets">{top('Spend & budgets')}
<h2>{money(tot_t, est=True)} spent, up {pct(tot_t, tot_p).lstrip('+')}. Prospecting now runs at ${prosp:.0f}/day.</h2>
<p class="sub">LinkedIn actual {money(li_t)} ({pct(li_t, li_p)}), including {money(sp['li_rt'])} of new retargeting from Nov 11. Meta is an <b style="color:var(--amb)">estimate</b> of {money(meta[T], est=True)} (${meta['per_day']}/day) because the account is locked.</p>
<div class="grid g2 fill" style="grid-template-columns:1.05fr 1fr">
 <div class="glass card col"><div class="lbl">Spend by channel, this week vs last <span class="legend-est" style="margin-left:10px"></span><span class="hint">hatched = estimate</span></div><div class="chart"><canvas id="cSpend"></canvas></div></div>
 <div class="glass card col"><div class="lbl">LinkedIn daily budgets since Nov 12</div><div class="chart"><canvas id="cBud"></canvas></div>
 <p class="hint" style="margin-top:8px;font-size:13px;line-height:1.45">{S['budget_note']}</p></div>
</div>
<div class="src">LinkedIn: campaign report, account 513100372; budgets re-read live Fri Nov 13 (read-only). Prospecting averaged ${sp['li_prosp'] / 7:.0f}/day this week against $275/day of set budgets (LinkedIn over-delivers).</div>
{notes('Prospecting $260 = bg2 US 100 + bg2 EU 100 + bg1 US 40 + static-test-US 20 (ends Sun Nov 15).', 'rt-vsl retargeting $20/day on top, uncapped.')}</section>''')

    # 4 funnel
    def fb(label, v, vmax, col, conv=''):
        w = max(16, (v / vmax) ** 0.5 * 100)
        return f'<div class="frow"><div class="bx" style="width:{w * 0.62:.0f}%;background:{col}"><span>{label}</span>{v:,}</div><div class="cv">{conv}</div></div>'
    q_rate_t = bk_t['q'] / bk_t['strategy'] * 100
    q_rate_p = bk_p['q'] / bk_p['strategy'] * 100
    fun = (fb('LinkedIn clicks', fn_t['li_clicks'], fn_t['li_clicks'], 'rgba(96,165,250,.35)', f'<b>{fn_t["click_to_lead"]}%</b>click → LinkedIn report lead (last week {fn_p["click_to_lead"]}%)')
           + (fb('Report-page visitors', GA['steps'][T]['optin_users'], fn_t['li_clicks'], 'rgba(96,165,250,.22)', f'<b>{GA["steps"][T]["optin_rate"]}%</b>visitor → report lead, all sources (last week {GA["steps"][P]["optin_rate"]}%)') if GA else '')
           + fb('Report leads', fn_t['report_leads'], fn_t['li_clicks'], 'rgba(167,139,250,.35)', f'<b>{ld_t["by_ch"].get("LinkedIn ads", 0)} / {ld_t["by_ch"].get("Meta ads", 0)} / {ld_t["by_ch"].get("Organic (5 Ways report)", 0)}</b>LinkedIn / Meta / organic')
           + (fb('VSL visitors', GA['steps'][T]['vsl_users'], fn_t['li_clicks'], 'rgba(251,191,36,.30)', f'<b>{GA["steps"][T]["vsl_to_book"]}%</b>VSL visitor → booked call (last week {GA["steps"][P]["vsl_to_book"]}%) · bar 2–5%') if GA else
              '<div class="frow"><div class="bx gapbox" style="width:38%"><span>VSL visitors</span>not tracked</div><div class="cv"><b>2–5% bar can\'t be checked</b>no page analytics connected</div></div>')
           + fb('Calls booked', fn_t['books'], fn_t['li_clicks'], 'rgba(52,211,153,.32)', f'<b>{fn_t["lead_to_book"]}%</b>report lead → booked call (last week {fn_p["lead_to_book"]}%)')
           + fb('Qualified', fn_t['q'], fn_t['li_clicks'], 'rgba(52,211,153,.55)', f'<b>{q_rate_t:.0f}%</b>of books qualified (last week {q_rate_p:.0f}%)'))
    slides.append(f'''<section class="slide" data-title="Funnel">{top('Funnel')}
<h2>Fewer clicks and leads, but more of them qualified</h2>
<p class="sub">Clicks {lt['clk']} ({lp['clk']}), report leads {ld_t['total']} ({ld_p['total']}), calls {bk_t['strategy']} ({bk_p['strategy']}), qualified {bk_t['q']} ({bk_p['q']}). LinkedIn CTR {lt['ctr']}% ({lp['ctr']}%), CPC {money(lt['cpc'], 2)} ({money(lp['cpc'], 2)}), CPM ${lt['cpm']:.0f} (${lp['cpm']:.0f}).</p>
<div class="grid g2 fill" style="grid-template-columns:1.25fr 1fr">
 <div class="glass card col" style="justify-content:center">{fun}</div>
 <div class="glass card col"><div class="lbl">Free-report leads by source</div><div class="chart"><canvas id="cLeads"></canvas></div></div>
</div>
<div class="src">Report leads: GHL contacts created in the week with the free-report tag/URL or the "5 Ways" source. {'Report-page and VSL visitors: GA4 unique users on go.aletto.ai/saasreport and /freetraining-1-7481 (ET week). ' if GA else ''}Books: Hyros "Free AI Strategy Call". Qualified: GHL tag. Bar widths are scaled (square root) so the small steps stay readable.</div>
{notes('Organic "5 Ways" leads were the only lead source that grew (52 → 61).', ('VSL visitors come from GA4 (connected Nov 13). More people see the VSL than become new leads because repeat opt-ins and email/DM clicks land there too.' if GA else 'VSL visitors are the missing step; GA4 fixes it (recommendation 5).'))}</section>''')

    # 4b VSL throughput by source (GA4)
    if GA:
        st = GA['steps']
        def badge(r):
            if r is None: return '<span class="hint">—</span>'
            if r > 5: return '<span class="tag" style="background:rgba(52,211,153,.15);color:var(--grn)">above bar</span>'
            if r >= 2: return '<span class="tag" style="background:rgba(96,165,250,.15);color:var(--blu)">on bar</span>'
            return '<span class="tag" style="background:rgba(255,90,90,.15);color:#ff6b6b">below bar</span>'
        def pc(v): return '—' if v is None else f'{v}%'
        def col(r): return 'inherit' if r is None else ('var(--grn)' if r > 5 else 'var(--blu)' if r >= 2 else '#ff6b6b')
        def nm(v): return '—' if v is None else f'{v:,}'
        def vrow(lab, t, p, cls=''):
            return (f'<tr class="{cls}"><td style="text-align:left">{lab}</td><td>{nm(t["optin_users"])} <span class="hint">({nm(p["optin_users"])})</span></td>'
                    f'<td>{pc(t["optin_to_vsl"])} <span class="hint">({pc(p["optin_to_vsl"])})</span></td><td><b>{nm(t["vsl_users"])}</b> <span class="hint">({nm(p["vsl_users"])})</span></td>'
                    f'<td>{nm(t["books"])} <span class="hint">({nm(p["books"])})</span></td><td><b style="color:{col(t["vsl_to_book"])}">{pc(t["vsl_to_book"])}</b> <span class="hint">({pc(p["vsl_to_book"])})</span></td></tr>')
        bs = {r['key']: r for r in GA['by_source']}
        vr = ''.join(vrow(bs[k]['label'], bs[k][T], bs[k][P]) for k in ('li_ads', 'meta_ads', 'li_org'))
        vr += vrow('Everything else<div class="hint" style="font-size:11px">direct, email, IG, YT, no source</div>', GA['by_source_rest'][T], GA['by_source_rest'][P])
        vr += vrow('<b>All sources</b>', st[T], st[P], 'hl')
        d30 = st['d30']
        vr += (f'<tr><td style="text-align:left;color:var(--mut)">30 days (Oct 14 – Nov 12)</td><td>{nm(d30["optin_users"])}</td><td>{pc(d30["optin_to_vsl"])}</td><td>{nm(d30["vsl_users"])}</td><td>{nm(d30["books"])}</td><td><b style="color:{col(d30["vsl_to_book"])}">{pc(d30["vsl_to_book"])}</b></td></tr>')
        dv = GA['device']
        def dev(w):
            o, v = dv.get(f'/saasreport|{w}', {}), dv.get(f'/freetraining-1-7481|{w}', {})
            return {k: (v.get(k, 0), o.get(k, 0), round(v.get(k, 0) / o[k] * 100, 1) if o.get(k) else None) for k in ('mobile', 'desktop')}
        dt_, dp_ = dev(T), dev(P)
        trk = GA['tracking']; li_s = bs['li_ads']; me_s = bs['meta_ads']
        leak = (f'<div class="glass card flag a"><b>Biggest leak: the report page</b><p>{st[T]["optin_users"]:,} visitors → {st[T]["leads"]} new leads ({st[T]["optin_rate"]}%). '
                f'Meta sends {me_s[T]["optin_users"]} visitors who stay ~{trk["meta_optin_eng_per_user_s"]:.0f}s and opt in at {me_s[T]["optin_rate"]}% (LinkedIn ads: ~{trk["li_optin_eng_per_user_s"]:.0f}s, {li_s[T]["optin_rate"]}%).</p></div>'
                f'<div class="glass card flag a"><b>Mobile drops before the VSL</b><p>Mobile: {dt_["mobile"][1]} report-page visitors → {dt_["mobile"][0]} on the VSL ({dt_["mobile"][2]}%). '
                f'Desktop: {dt_["desktop"][1]} → {dt_["desktop"][0]} ({dt_["desktop"][2]}%). Last week {dp_["mobile"][2]}% vs {dp_["desktop"][2]}%.</p></div>'
                f'<div class="glass card flag g" style="border-left-color:var(--blu)"><b>How to read it</b><p>Books are Hyros last touch in the same week, not a cohort of these visitors. '
                f'Meta\'s {me_s[T]["vsl_to_book"]}% is inflated: Meta bookers often come back through email or DM, so GA4 logs their VSL visit there.</p></div>')
        slides.append(f'''<section class="slide" data-title="VSL throughput">{top('VSL throughput by source')}
<h2>The VSL books {st[T]['vsl_to_book']}% of visitors, well over the 2–5% bar. The leak is before it.</h2>
<p class="sub">{st[T]['vsl_users']} VSL visitors ({st[P]['vsl_users']} last week) → {st[T]['books']} strategy calls booked ({st[P]['books']}). LinkedIn ads fell from {li_s[P]['vsl_to_book']}% to {li_s[T]['vsl_to_book']}% visitor → book, still above the bar. Only {st[T]['optin_to_vsl']}% of report-page visitors reach the VSL.</p>
<div class="grid g2 fill" style="grid-template-columns:1.7fr 1fr">
 <div class="glass card col"><div class="lbl">Report page → VSL → booked call · this week (last week) · <span style="color:var(--grn)">green = above the 2–5% bar</span></div>
  <div class="scroll fill"><table class="tb2" style="font-size:13px"><tr><th style="text-align:left">Source</th><th>Report-page<br>visitors</th><th>→ VSL</th><th>VSL<br>visitors</th><th>Books</th><th>VSL →<br>book</th></tr>{vr}</table></div></div>
 <div class="col" style="gap:10px">{leak}</div>
</div>
<div class="src">GA4 (property 540656492, ET): unique users on go.aletto.ai/saasreport and /freetraining-1-7481, by session source. LinkedIn/Meta ads = utm_source linkedin / fb_ad; LinkedIn organic = linkedin.com referrer. Source rows can overlap slightly (one person, two sources). Books: Hyros strategy calls, last touch; "Everything else" books = Hyros organic other + no source.</div>
{notes(f"VSL visitors {st[T]['vsl_users']} vs {st[P]['vsl_users']}; 30 days {d30['vsl_users']:,} visitors and {d30['books']} books = {d30['vsl_to_book']}%.", f"{st[T]['vsl_untracked_users']} VSL visitors ({st[T]['vsl_untracked_pct']}%) have no source in GA4.", 'The calendar sits on the VSL page itself, so GA4 can\'t see the booking yet; see Data gaps.', *GA.get('notes_extra', []))}</section>''')

    # 5 books & scopes by source
    sl = []
    import re as _re
    for s in bk_t['scope_list']:
        nm, d_, rest = [x.strip() for x in s.split('—', 2)]
        m_ = _re.match(r'^(.*) \(([^;]*); first touch (.*)\)$', rest)
        ch, ad, ft = (m_.group(1), m_.group(2).strip(), m_.group(3).strip()) if m_ else (rest, '', '')
        ad = {'li': 'LinkedIn (organic)', 'freereport': 'free report', '': '—'}.get(ad, ad)
        ftn = '' if (not ft or ft.startswith(ch)) else f'<div class="hint" style="font-size:11.5px">first touch: {E(ch_short(ft.split("  ")[0]))}</div>'
        sl.append(f'<tr><td>{E(nm)}</td><td>{d_[5:]}</td><td style="text-align:left">{E(ch_short(ch))}</td><td style="text-align:left;color:var(--mut);white-space:normal">{E(ad)}{ftn}</td></tr>')
    slides.append(f'''<section class="slide" data-title="Books & Scopes">{top('Books & Scopes by source')}
<h2>Meta and organic booked more. LinkedIn paid halved.</h2>
<p class="sub">Last-touch source. Meta {chb(bk_t, 'Meta ads', 'books')} books / {chb(bk_t, 'Meta ads', 'q')} qualified ({chb(bk_p, 'Meta ads', 'books')} / {chb(bk_p, 'Meta ads', 'q')}). LinkedIn ads {chb(bk_t, 'LinkedIn ads', 'books')} / {chb(bk_t, 'LinkedIn ads', 'q')} ({chb(bk_p, 'LinkedIn ads', 'books')} / {chb(bk_p, 'LinkedIn ads', 'q')}). Organic {org(bk_t, 'books')} / {org(bk_t, 'q')}. Scopes {bk_t['scopes']} ({bk_p['scopes']}), none from LinkedIn paid.</p>
<div class="grid g2 fill" style="grid-template-columns:1.2fr 1fr">
 <div class="glass card col"><div class="lbl">Calls booked and qualified, this week vs last</div><div class="chart"><canvas id="cBooks"></canvas></div></div>
 <div class="glass card col"><div class="lbl">The {bk_t['scopes']} Scopes booked this week</div>
  <div class="chart" style="flex:0 0 120px"><canvas id="cScopes"></canvas></div>
  <div class="scroll fill" style="margin-top:8px"><table class="tb2"><tr><th>Who</th><th>Day</th><th style="text-align:left">Source</th><th style="text-align:left">Ad / channel</th></tr>{''.join(sl)}</table></div></div>
</div>
<div class="src">Hyros booked calls, last touch. "Organic (LinkedIn)" = organic with a LinkedIn referrer (probable LinkedIn). "No source" includes returning contacts the SDRs set. 4 books have no GHL match, so their qualified status is unknown.</div>
{notes('Andrew S. Scope: last touch the free report, first touch the Meta STATIC-hard-to-reach-buyers ad.', 'LinkedIn paid had 2 last-touch Scopes last week, 0 this week.')}</section>''')

    # 6 cost per qualified / scope
    trs = ''
    for lab, s1, s0, est, b1, b0, q1, q0, c1, c0 in src_rows:
        e = est
        def cell(v, v0):
            if s1 is None: return '<td class="z">no ad spend</td>'
            return f'<td>{money(v, est=e) if v else "—"} <span class="hint">({money(v0, est=e) if v0 else "—"})</span></td>'
        trs += (f'<tr><td>{lab}{" " + EST if est and s1 else ""}</td><td>{money(s1, est=est) if s1 else "—"}</td><td>{b1} <span class="hint">({b0})</span></td><td>{q1} <span class="hint">({q0})</span></td><td>{c1} <span class="hint">({c0})</span></td>'
                + cell(per(s1, b1) if s1 else None, per(s0, b0) if s0 else None)
                + cell(per(s1, q1) if s1 else None, per(s0, q0) if s0 else None)
                + (cell(per(s1, c1), per(s0, c0)) if s1 else '<td class="z">no ad spend</td>') + '</tr>')
    slides.append(f'''<section class="slide" data-title="Cost by source">{top('Cost per qualified call & per Scope')}
<h2>Meta is the cheapest paid source on the estimate. LinkedIn cost {money(per(li_t, chb(bk_t, 'LinkedIn ads', 'q')))} per qualified call.</h2>
<p class="sub">All in: {money(tot_t / bk_t['q'], est=True)} per qualified call ({money(tot_p / bk_p['q'], est=True)}) and {money(tot_t / bk_t['scopes'], est=True)} per Scope ({money(tot_p / bk_p['scopes'], est=True)}). LinkedIn spent {money(li_t)} for 0 last-touch Scopes. Meta figures use estimated spend.</p>
<div class="grid g2" style="grid-template-columns:1fr 1fr;flex:1;min-height:0">
 <div class="glass card col"><div class="lbl">Cost per qualified call (lower is better)</div><div class="chart"><canvas id="cCpq"></canvas></div></div>
 <div class="glass card col"><div class="lbl">Cost per Scope booked (lower is better)</div><div class="chart"><canvas id="cCps"></canvas></div></div>
</div>
<div class="glass card scroll" style="margin-top:14px;flex:none"><table class="tb2"><tr><th>Source</th><th>Spend</th><th>Books</th><th>Qualified</th><th>Scopes</th><th>$ / book</th><th>$ / qualified</th><th>$ / Scope</th></tr>{trs}</table></div>
<div class="src">Last week in brackets. Spend: LinkedIn actual; Meta ~$190/day estimate. Scopes are last touch; "—" means no Scope to divide by.</div>
{notes('LinkedIn per qualified went from $346 to $554.', 'Meta went from ~$665 to ~$222 per qualified, but the spend is an estimate.')}</section>''')

    # 7 last $5k summary
    l5 = D['last5k']
    order = sorted(l5, key=lambda c: -(c['any']['scopes'] if c['any'] else 0))
    cards = ''
    for c in order:
        a_ = c['any']
        cards += f'''<div class="glass card" style="flex:1;display:flex;flex-direction:column;justify-content:center"><div class="l5h"><b>{c['camp']}</b><span class="hint">{c['start'][5:].replace('-', '/')} → 11/11 · {money(c['spend'])}</span></div>
<div class="l5k"><div><div class="t">Strict · first Strat</div><div class="n">{c['strict']['scopes']} <span style="font-size:13px;color:var(--mut)">Scopes</span></div><div class="hint">{c['strict']['asked']} asked · {money(per(c['spend'], c['strict']['asked'])) if c['strict']['asked'] else '—'} / asked</div></div>
<div><div class="t">Any Strat in window</div><div class="n" style="color:var(--grn)">{a_['scopes']} <span style="font-size:13px;color:var(--mut)">Scopes</span></div><div class="hint">{a_['asked']} asked · {money(per(c['spend'], a_['asked']))} / asked</div></div></div></div>'''
    slides.append(f'''<section class="slide" data-title="Last $5k">{top('Last $5k per LinkedIn campaign')}
<h2>bg2 EU earns its money. bg2 US looks better on the wider count.</h2>
<p class="sub"><b>Strict</b> credits a Scope to the ad on the person's first strategy-call booking (last touch). <b>Any Strat</b> credits it if any of their strategy calls in the window came from the campaign (each person once). Windows end Nov 11; Nov 12 added no LinkedIn Scope.</p>
<div class="grid g2 fill" style="grid-template-columns:1fr 1.15fr">
 <div class="glass card col"><div class="lbl">Scopes from the last $5k, by method</div><div class="chart"><canvas id="c5k"></canvas></div></div>
 <div class="col" style="gap:12px;justify-content:space-between">{cards}</div>
</div>
<div class="src">li-trim-2026-11-12: LinkedIn spend (adAnalytics, account 513100372) + Hyros Strategy first-book source + Scope-asked CSV + GHL Scope calendar + Hyros Scope calls. "Asked" = asked for a Scope. Bruce R. counts in both bg2 US and bg1 US under Any Strat.</div>
{notes('The two methods agree on bg2 EU: 6 Scopes, all deadcold.', 'bg2 US goes 1 → 4 Scopes and bg1 US 0 → 3 under Any Strat; that is why the Nov 12 trim kept both alive.')}</section>''')

    # 8 last $5k per ad
    def adtable(c):
        anym = {}
        for r in (c['any']['ads'] if c['any'] else []):
            base = r['ad'].replace('(FT)', '')
            x = anym.setdefault(base, {'asked': 0, 'scopes': 0, 'who': []})
            x['asked'] += r['asked']; x['scopes'] += r['scopes']; x['who'] += r['who']
        rows = ''
        for ad in c['ads']:
            a_ = anym.get(ad['ad'], {'asked': 0, 'scopes': 0, 'who': []})
            if ad['spend'] < 50 and not (a_['scopes'] or ad['scopes'] or ad['ft_scopes'] or a_['asked']): continue
            cls = 'hl' if (a_['scopes'] or ad['scopes']) else ('lo' if ad['spend'] > 1000 else '')
            pair = lambda x, y: f'<td class="z">0 · 0</td>' if not (x or y) else f'<td>{x} · <b style="color:{"var(--grn)" if y else "inherit"}">{y}</b></td>'
            pa = money(ad['spend'] / a_['asked']) if a_['asked'] and ad['spend'] else ('$0 spend' if a_['asked'] else '—')
            who = ', '.join(dict.fromkeys(a_['who']))
            rows += f'<tr class="{cls}"><td class="ad" title="{E(ad["ad"])}">{E(ad["ad"] if len(ad["ad"]) <= 18 else ad["ad"][:17] + "…")}</td><td>{money(ad["spend"])}</td>{pair(ad["asked"], ad["scopes"])}{pair(a_["asked"], a_["scopes"])}<td>{pa}</td></tr>' + (f'<tr class="{cls}"><td colspan="5" class="hint" style="text-align:left;white-space:normal;padding-top:0">Scopes: {E(who)}</td></tr>' if who else '')
        return f'''<div class="glass card col"><div class="l5h"><b>{c['camp']}</b><span class="hint">{money(c['spend'])}</span></div><div class="scroll fill"><table class="tb2"><tr><th>Ad</th><th>Spend</th><th>Strict<br>asked · Scopes</th><th>Any Strat<br>asked · Scopes</th><th>$ / asked<br>(any)</th></tr>{rows}</table></div></div>'''
    slides.append(f'''<section class="slide" data-title="Last $5k by ad">{top('Last $5k · per ad')}
<h2>deadcold carries EU. coldgraveyard is the only US ad with Scopes on real spend.</h2>
<p class="sub">deadcold: {money(next(a['spend'] for c in l5 for a in c['ads'] if a['ad'] == 'deadcold'))} → 6 Scopes, $762 per Scope-asked. coldgraveyard: $2,965 → 1 Scope strict, 2 any-Strat, $741 per asked. datadoesn'tlie: Will H. on just $144. 2013selling's 2 Scopes are old first touches on $0 spend in the window, and its bg1 remake was rejected by LinkedIn.</p>
<div class="grid g3 fill" style="grid-template-columns:.9fr 1.05fr 1.05fr">{''.join(adtable(c) for c in sorted(l5, key=lambda c: ['bg2 EU', 'bg2 US', 'bg1 US'].index(c['camp']) if c['camp'] in ['bg2 EU', 'bg2 US', 'bg1 US'] else 9))}</div>
<div class="src">Rows: ads with $50+ in the window or any Scope/asked credit. Green = has a Scope; red = $1k+ with none. "Duplicate_Ad_3" and "2013selling" spent $0 in the window; their credit comes from first touches before it.</div>
{notes('The per-ad view is why recommendation 2 sets a ~$1k test on bg2 US remakes before moving money to deadcold.', 'coldemail ($1,219) and colddead ($2,744 in bg1) booked Strats but no Scope-asked under either method.')}</section>''')

    # 9 creatives
    def crc(items, col):
        return ''.join(f'<div class="glass it" style="border-left:3px solid {col}"><div class="nm">{E(n)}</div><div class="ch">{E(c)}</div><p>{p}</p></div>' for n, c, p in items)
    slides.append(f'''<section class="slide" data-title="Creatives">{top('Creative winners & losers')}
<h2>One LinkedIn ad and one Meta static did most of the booking</h2>
<p class="sub">Paid last-touch books by ad this week. LinkedIn spend is actual; Meta spend per ad can't be seen.</p>
<div class="grid g3 fill" style="grid-template-columns:1fr 1.1fr 1fr">
 <div class="col"><div class="lbl c-g">Top 3</div><div class="cr">{crc(S['winners'], 'var(--grn)')}</div></div>
 <div class="glass card col"><div class="lbl">Books by ad (paid, last touch)</div><div class="chart"><canvas id="cCr"></canvas></div></div>
 <div class="col"><div class="lbl c-r">Bottom 3</div><div class="cr">{crc(S['losers'], '#ff6b6b')}</div></div>
</div>
<div class="src">Hyros last-touch ad on each strategy call; GHL qualified tag; LinkedIn creative report. Report leads from GHL UTM content.</div>
{notes('coldgraveyard spent the most for 1 book; bg2 US gets the US-first remakes test.', 'ghosted_v2 already paused Nov 12.')}</section>''')

    # 10 fatigue
    fg = ''.join(f'<div class="glass card flag {c}"><b>{t}</b><p>{p}</p></div>' for c, t, p in S['fatigue'])
    slides.append(f'''<section class="slide" data-title="Fatigue">{top('Fatigue radar')}
<h2>LinkedIn is getting more expensive to show</h2>
<p class="sub">Account CPM went ${lp['cpm']:.0f} → ${lt['cpm']:.0f} week on week and rose from $46 to $58 a day between Nov 6 and Nov 12. Frequency is creeping up in both bg2 campaigns. Meta frequency, CPM and CTR can't be seen.</p>
<div class="grid g2 fill" style="grid-template-columns:1.25fr 1fr">
 <div class="glass card col"><div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap"><div class="lbl" id="fgLbl">Daily CPM by campaign</div><div class="pill" id="fgPills"><button class="on" data-m="cpm">CPM</button><button data-m="ctr">CTR</button><button data-m="acct">Account, 14 days</button></div></div><div class="chart"><canvas id="cFat"></canvas></div></div>
 <div class="col scroll" style="gap:10px;display:flex">{fg}</div>
</div>
<div class="src">LinkedIn campaign daily and account daily reports. Frequency = impressions ÷ reach for the week. bg1 US Nov 12 jump reflects the $15 → $40 budget change.</div>
{notes('Rule of thumb: rotate creative before frequency passes ~2 on cold audiences.')}</section>''')

    # 11 content (v2: content.json from content_extract.py -> 3 slides; else the old single slide)
    cpath = os.path.join(wdir, 'content.json')
    if os.path.exists(cpath) and 'content2' in S:
        CJ, C2 = json.load(open(cpath)), S['content2']
        tt, tp = CJ['totals']['this'], CJ['totals']['prior']
        org_rep_t = ld_t['by_ch'].get('Organic (5 Ways report)', 0); org_rep_p = ld_p['by_ch'].get('Organic (5 Ways report)', 0)
        g_t, g_p = CJ['ghl']['this']['report_first'], CJ['ghl']['prior']['report_first']
        LEADMAP = {'Jake · LinkedIn': 'LinkedIn organic', 'Jake · Instagram': 'Instagram', 'Jake · YouTube': 'YouTube', 'Jake · X': 'X',
                   'Jake · Threads': 'Threads', 'Jake · TikTok': 'TikTok', 'Aletto · Facebook': 'Facebook organic'}
        fmtn = lambda v: '—' if v is None else f'{v:,}'
        rows = ''
        for r in CJ['platforms']:
            a_, b_ = r['this'], r['prior']
            lk = LEADMAP.get(r['key'])
            lv = g_t.get(lk, 0) if lk else ''
            lead_cell = (f'<b style="color:var(--grn)">{lv}*</b>' if lv and r['key'] == 'Jake · LinkedIn' else (f'<b>{lv}</b>' if lv else ('<span class="z">0</span>' if lk else '<span class="z">—</span>')))
            dv = (f'<span class="{"up" if a_["views"] >= b_["views"] else "dn"}">{pct(a_["views"], b_["views"])}</span>') if b_['posts'] else '<span class="hint">new</span>'
            rows += (f'<tr class="{"hl" if r["key"] == "Jake · LinkedIn" else ""}"><td class="ad" style="text-align:left">{E(r["key"])}</td><td>{a_["posts"]}<span class="hint"> ({b_["posts"]})</span></td>'
                     f'<td><b>{a_["views"]:,}</b></td><td>{dv}</td><td>{fmtn(a_["reach"])}</td><td>{a_["likes"]:,}</td><td>{a_["comments"]:,}</td><td>{a_["shares"]:,}</td>'
                     f'<td>{a_["saves"]:,}</td><td>{a_["er"] if a_["er"] is not None else "—"}%</td><td>{fmtn(a_["clicks"])}</td><td>{lead_cell}</td></tr>')
        slides.append(f'''<section class="slide sbslide" data-title="Content scoreboard">{top('Content · platform scoreboard')}
<h2>{C2['score_h']}</h2><p class="sub">{C2['score_sub']}</p>
<div class="grid g4 g3k" style="margin-bottom:12px">{kpi('Posts', f"{tt['posts']:,}", delta(tt['posts'], tp['posts'], 'none', lambda v: f'{v:,}'))}{kpi('Views / impressions', f"{tt['views']:,}", delta(tt['views'], tp['views'], 'up', lambda v: f'{v:,}'))}{kpi('Engagements', f"{tt['eng']:,}", delta(tt['eng'], tp['eng'], 'up', lambda v: f'{v:,}'))}{kpi('Organic report leads', org_rep_t, delta(org_rep_t, org_rep_p), color='color:var(--grn)')}</div>
<div class="glass card fill scroll"><table class="tb2 sbtab"><tr><th style="text-align:left">Brand · platform</th><th>Posts (last wk)</th><th>Views</th><th>vs last wk</th><th>Reach</th><th>Likes</th><th>Comments</th><th>Shares</th><th>Saves</th><th>Eng. rate</th><th>Clicks</th><th>Report leads</th></tr>{rows}
<tr><td style="text-align:left"><b>Total</b></td><td><b>{tt['posts']:,}</b><span class="hint"> ({tp['posts']:,})</span></td><td><b>{tt['views']:,}</b></td><td><span class="up">{pct(tt['views'], tp['views'])}</span></td><td>{fmtn(tt['reach'])}</td><td>{tt['likes']:,}</td><td>{tt['comments']:,}</td><td>{tt['shares']:,}</td><td>{tt['saves']:,}</td><td>{tt['er']}%</td><td>{fmtn(tt['clicks'])}</td><td><b>{org_rep_t}</b></td></tr></table></div>
<div class="src">Metricool post analytics (pulled Fri Nov 13, lifetime-to-date per post), cross-checked with Zernio (Threads / Instagram / TikTok / company page within ~10%). Views = platform views; LinkedIn and X = impressions. Engagements = likes + comments + shares/reposts + saves. Clicks: X profile clicks, LinkedIn page clicks. *Report leads = GHL first-touch referrer; 56 "linkedin.com" leads can't be split between Jake's profile and the company page. 5 organic leads had no referrer. Facebook page counted once (Aletto).</div>
{notes('Threads = 87% of all views but 7% of engagements and 0 leads.', 'LinkedIn: text posts median 160 impressions vs video 64.', 'Jake LinkedIn row includes reposts with comments (e.g. the Nov 8 reply to Jack Porter, 3,145 impressions).')}</section>''')

        def hrow(label, F, L):
            f = F.get(label, {'strat': 0, 'q': 0, 'scope': 0, 'scope_who': []}); l = L.get(label, {'strat': 0, 'q': 0, 'scope': 0, 'scope_who': []})
            z = lambda v: f'<span class="z">0</span>' if not v else str(v)
            who = ', '.join(f['scope_who'] or l['scope_who'])
            return (f'<tr class="{"hl" if label == "LinkedIn organic" else ""}"><td style="text-align:left" class="ad">{label}</td><td>{z(f["strat"])}</td><td>{z(f["q"])}</td><td>{z(f["scope"])}</td>'
                    f'<td>{z(l["strat"])}</td><td>{z(l["q"])}</td><td>{z(l["scope"])}</td><td style="text-align:left;color:var(--mut);white-space:normal">{E(who)}</td></tr>')
        HF, HL = CJ['hyros']['this_first'], CJ['hyros']['this_last']
        org_labels = ['LinkedIn organic', 'Instagram', 'YouTube', 'X', 'Threads', 'TikTok', 'Facebook organic', 'Google organic', 'Email', 'Free report (nurture)']
        org_labels += [k for k in list(HF) + list(HL) if k.startswith('Organic ') and k not in org_labels]
        _nz = lambda k: any((T_.get(k) or {}).get(m) for T_ in (HF, HL) for m in ('strat', 'scope'))
        org_labels = [k for k in org_labels if k in ('LinkedIn organic', 'Instagram', 'YouTube', 'X') or _nz(k)]
        hrows = ''.join(hrow(k, HF, HL) for k in org_labels)
        sum_org = lambda T_, k: sum(v[k] for n_, v in T_.items() if not n_.startswith('Paid') and n_ != 'No source')
        slides.append(f'''<section class="slide" data-title="Organic leads by source">{top('Content · organic leads by source')}
<h2>{C2['leads_h']}</h2><p class="sub">{C2['leads_sub']}</p>
<div class="grid g2 fill" style="grid-template-columns:1fr 1.25fr">
 <div class="glass card col"><div class="lbl">Organic free-report leads by first-touch source, this week vs last</div><div class="chart"><canvas id="cOrg"></canvas></div></div>
 <div class="glass card col"><div class="lbl">Strategy calls · qualified · Scopes by organic source (Hyros)</div>
  <div class="scroll fill" style="margin-top:6px"><table class="tb2"><tr><th style="text-align:left">Source</th><th colspan="3">First touch<br><span class="hint">Strat · qual · Scope</span></th><th colspan="3">Last touch<br><span class="hint">Strat · qual · Scope</span></th><th style="text-align:left">Scopes</th></tr>{hrows}
  <tr><td style="text-align:left"><b>All organic</b></td><td><b>{sum_org(HF, 'strat')}</b></td><td><b>{sum_org(HF, 'q')}</b></td><td><b>{sum_org(HF, 'scope')}</b></td><td><b>{sum_org(HL, 'strat')}</b></td><td><b>{sum_org(HL, 'q')}</b></td><td><b>{sum_org(HL, 'scope')}</b></td><td></td></tr></table></div>
  <p class="hint" style="margin-top:8px;font-size:12.5px;line-height:1.45">Paid, for scale (first touch): Meta {HF.get('Paid Meta', {}).get('strat', 0)} · {HF.get('Paid Meta', {}).get('q', 0)} · {HF.get('Paid Meta', {}).get('scope', 0)}, LinkedIn ads {HF.get('Paid LinkedIn', {}).get('strat', 0)} · {HF.get('Paid LinkedIn', {}).get('q', 0)} · {HF.get('Paid LinkedIn', {}).get('scope', 0)}, no source {HF.get('No source', {}).get('strat', 0)} · {HF.get('No source', {}).get('q', 0)} · {HF.get('No source', {}).get('scope', 0)}. Hyros source links are per channel (li, ig, fb…), not per post, so no single post can be credited with a lead yet.</p></div>
</div>
<div class="src">Leads: GHL contacts created in the week (free-report tag/URL or "5 Ways" source), first-touch referrer / in-app browser (LinkedInApp, Instagram). Books: Hyros "Free AI Strategy Call" and "Scope Call", first and last touch; qualified = GHL tag. Prospects shown as first name + last initial.</div>
{notes('Instagram last week: 3 report leads and 1 qualified strategy call; this week 0 leads and 1 unqualified call.', 'Google organic (last touch) booked 2 qualified calls and Manuel M.\'s Scope; his first touch was LinkedIn organic.')}</section>''')

        H_ = C2['hot']
        slides.append(f'''<section class="slide cslide" data-title="Hot post, hooks & tests">{top('Content · hot post, hooks & tests')}
<h2>#1 post, 5 hooks, 3 super hooks, 5 tests</h2>
<p class="sub">Built from what drove leads (LinkedIn text posts with numbers from our own data) and from the language Scope buyers used on their strategy calls (cold outreach failing, trade shows burning money, founder-led sales hitting a ceiling).</p>
<div class="grid g3 fill" style="grid-template-columns:1.05fr 1fr 1.15fr;align-items:stretch">
 <div class="glass card col scroll" style="border-left:3px solid var(--amb)"><div class="lbl" style="color:var(--amb)">🔥 Hot post #1</div><b style="font-size:clamp(17px,1.45vw,21px);margin:6px 0 2px;display:block">{E(H_['title'])}</b><div class="hint" style="margin-bottom:6px"><a href="{H_['url']}" target="_blank" rel="noopener" style="color:var(--blu)">{E(H_['meta'])} ↗</a></div>
  <ul class="clean">{''.join(f'<li>{x}</li>' for x in H_['why'])}</ul><p class="hint" style="margin-top:8px;font-size:12.5px;line-height:1.45;color:#c3c9d6">{H_['runner']}</p></div>
 <div class="col" style="gap:12px"><div class="glass card col"><div class="lbl">New hooks to try</div><ul class="clean">{''.join(f'<li>{E(x)}</li>' for x in C2['hooks'])}</ul></div>
  <div class="glass card col" style="border-left:3px solid var(--red)"><div class="lbl" style="color:#ff8a8a">Super hooks</div><ul class="clean">{''.join(f'<li><b>{E(x)}</b></li>' for x in C2['super'])}</ul></div></div>
 <div class="glass card col scroll"><div class="lbl">New things to try <span class="tag pend">awaiting go</span></div><ul class="clean">{''.join(f'<li><b>{E(t)}.</b> {E(p)}</li>' for t, p in C2['tests'])}</ul></div>
</div>
<div class="src">Hot post = #1 by engagement on the platform that produced the organic leads; post-level lead tracking doesn't exist yet (test 1 fixes that). Scope-buyer language: us-qualified-remakes-2026-11-09/scope_buyer_patterns.md (Fathom strategy-call summaries, n=9). Nothing posted or changed.</div>
{notes('Hooks are drafts for Jake / the content team. Nothing is scheduled.', 'Super hooks are deliberately bolder; run them as LinkedIn text posts first.')}</section>''')
    else:
        # 11 content
        C = D['content']
        slides.append(f'''<section class="slide" data-title="Content">{top('Content & organic')}
    <h2>The company page started posting. The testimonial was the standout.</h2>
    <p class="sub">Organic booked {org(bk_t, 'books')} calls / {org(bk_t, 'q')} qualified and {sc(bk_t, 'Organic (probable LinkedIn)') + sc(bk_t, 'Organic other')} of the {bk_t['scopes']} Scopes. Organic "5 Ways" report leads {ld_p['by_ch'].get('Organic (5 Ways report)')} → {ld_t['by_ch'].get('Organic (5 Ways report)')}.</p>
    <div class="grid g4" style="margin-bottom:14px">{kpi('Company page posts', C['posts'])}{kpi('Impressions', f"{C['imp']:,}", f'<div class="deltas">~{round(C["imp"] / C["posts"])} per post</div>')}{kpi('Likes · shares · clicks', f"{C['likes']} · {C['shares']} · {C['clicks']}")}{kpi('Organic report leads', ld_t['by_ch'].get('Organic (5 Ways report)'), delta(ld_t['by_ch'].get('Organic (5 Ways report)'), ld_p['by_ch'].get('Organic (5 Ways report)')), color='color:var(--grn)')}</div>
    <div class="grid g2 fill" style="grid-template-columns:1.4fr 1fr">
     <div class="glass card col"><div class="lbl">Impressions per company-page post, Nov 7–12</div><div class="chart"><canvas id="cPosts"></canvas></div></div>
     <div class="glass card"><ul class="clean">{''.join(f'<li>{p}</li>' for p in S['content_points'])}</ul></div>
    </div>
    <div class="src">Zernio analytics, LinkedIn, Oct 30–Nov 12 (all 19 posts fall Nov 7–12; none the week before). GHL "5 Ways" source for organic leads.</div>
    {notes('Testimonial post: 62 impressions, 41 reach, 2 likes, 3 shares.')}</section>''')

    # 12 recommendations
    rc = ''.join(f'<div class="glass card rc"><div class="num">{i}</div><div><b>{E(t)}</b><p>{p}</p></div></div>' for i, (t, p) in enumerate(S['recs'], 1))
    slides.append(f'''<section class="slide" data-title="Recommendations">{top('Recommendations')}
<h2>Five moves, all waiting on Jake's go <span class="tag pend" style="font-size:13px;vertical-align:middle">awaiting go</span></h2>
<p class="sub">Nothing below has been changed live. The Nov 12 budget changes are the only live edits this week.</p>
<div class="grid g2 fill recs" style="align-content:center">{rc}</div>
<div class="src">Recommendations only. US-first qualifying remakes: us-qualified-remakes-2026-11-09. Meta plan: pinned Nov 4 plan.</div>
{notes('Ask for a yes/no on each of the five.')}</section>''')

    # 13 data gaps
    gp = ''.join(f'<div class="glass card flag {"a" if c == "a" else "g"}" style="{"border-left-color:var(--blu)" if c == "b" else ""}"><b>{t}</b><p>{p}</p></div>' for c, t, p in S['gaps'])
    slides.append(f'''<section class="slide" data-title="Data gaps">{top('Data gaps & how to read this')}
<h2>What we can't see yet</h2>
<p class="sub">Each gap below is labelled wherever it touches a number in this deck.</p>
<div class="grid {'g3 gaps gaps6' if len(S['gaps']) > 5 else 'g2 gaps'}" style="align-content:start{';grid-template-columns:repeat(3,1fr)' if len(S['gaps']) > 5 else ''}">{gp}</div>
<div class="glass card" style="margin-top:16px"><div class="lbl">Method</div><p class="hint" style="font-size:13.5px;line-height:1.5;color:#c3c9d6">Week = Fri–Thu Eastern time vs the week before. LinkedIn: Ryze LinkedIn Ads reports, account 513100372 (campaign, creative and daily views agree: {money(li_t, 2)} / {lt['clk']} clicks). Books: Hyros "Free AI Strategy Call", last touch. Scopes: Hyros "Scope Call". Qualified: GHL tag matched by booking email. Leads: GHL contacts by date added. {'Page visitors: GA4 property 540656492 (ET), unique users. ' if GA else ''}Content: Metricool post analytics, cross-checked with Zernio. Built {S['title_date']}, read-only.</p></div>
<div class="src">Rebuilt weekly from the Friday pack with build.py. Past weeks: /archive/.</div>
{notes('Biggest unlock now: a GA4 booking event on the VSL calendar, so visitor → book is measured per person instead of matched to Hyros totals.' if GA else 'Biggest unlock: GA4 on the VSL page.')}</section>''')

    # ---------- chart data
    def daily_series(metric):
        out = {}
        for camp, days in D['li_camp_daily'].items():
            out[camp] = {d[5:]: v[metric] for d, v in days.items()}
        return out
    days = sorted({d[5:] for v in D['li_camp_daily'].values() for d in v})
    li_ads_books = {}
    for r in bk_t['by_cr']:
        li_ads_books[r['cr']] = {'books': r['books'], 'q': r['q'], 'ch': r['ch']}
    CH = {
        'spend': {'li_prosp': [sp['li_prosp'], li_p], 'li_rt': [sp['li_rt'], 0], 'meta': [meta[T], meta[P]]},
        'bud': [[{'fr-winners-bg2-ss-sd-es': 'bg2 US', 'fr-winners-bg2-ss-sd-es-eu': 'bg2 EU', 'fr-winners-bg1-hc-rm-ml': 'bg1 US', 'static-test-US': 'static-test-US (ends Nov 15)', 'rt-vsl': 'rt-vsl retargeting'}.get(b['name'], b['name']), b['daily']] for b in sorted(D['budgets_now'], key=lambda b: (b['name'] == 'rt-vsl', -b['daily']))],
        'leads': [[ch_short(c), ld_t['by_ch'].get(c, 0), ld_p['by_ch'].get(c, 0)] for c in ['LinkedIn ads', 'Meta ads', 'Organic (5 Ways report)', 'Other']],
        'books': [[ch_short(c), chb(bk_t, c, 'books'), chb(bk_t, c, 'q'), chb(bk_p, c, 'books'), chb(bk_p, c, 'q')] for c in ['Meta ads', 'LinkedIn ads', 'Organic (probable LinkedIn)', 'Organic other', 'No source']],
        'scopes': [[ch_short(c), sc(bk_t, c), sc(bk_p, c)] for c in ['Organic (probable LinkedIn)', 'Organic other', 'Meta ads', 'LinkedIn ads', 'No source']],
        'cpq': [[r[0] + (' (est.)' if r[3] else ''), round(per(r[1], r[6])) if per(r[1], r[6]) else None, round(per(r[2], r[7])) if per(r[2], r[7]) else None] for r in src_rows[:3]],
        'cps': [[r[0] + (' (est.)' if r[3] else '') + (' · 0 Scopes' if r[1] and not r[8] else ''), round(per(r[1], r[8])) if per(r[1], r[8]) else None, round(per(r[2], r[9])) if per(r[2], r[9]) else None] for r in src_rows[:3]],
        'l5': [[c['camp'], c['strict']['scopes'], c['any']['scopes'] if c['any'] else 0] for c in order],
        'cr': sorted([[r['cr'].replace(' -W', ''), r['books'], r['q'], r['ch']] for r in bk_t['by_cr']], key=lambda x: -x[1]),
        'days': days, 'cpm': daily_series('cpm'), 'ctr': daily_series('ctr'),
        'acct': [[d[5:], v['cpm'], v['spend']] for d, v in sorted(D['li_daily'].items())],
        'posts': [[p['date'][5:], p['title'][:60], p['imp'], p['title'] == S['content_best']] for p in D['content']['list']],
    }
    if os.path.exists(os.path.join(wdir, 'content.json')) and 'content2' in S:
        _cj = json.load(open(os.path.join(wdir, 'content.json')))
        _gt, _gp = _cj['ghl']['this']['report_first'], _cj['ghl']['prior']['report_first']
        _labs = [k for k in ['LinkedIn organic', 'Direct / no referrer', 'Instagram', 'YouTube', 'X', 'Threads', 'TikTok', 'Facebook organic', 'Search', 'AI search', 'Other referrer']
                 if k in ('LinkedIn organic', 'Instagram', 'YouTube', 'X') or _gt.get(k) or _gp.get(k)]
        CH['org'] = [[k, _gt.get(k, 0), _gp.get(k, 0)] for k in _labs]
    css = A('base.css') + A('presenter.css') + A('deck.css')
    body = '\n'.join(slides)
    js = A('deck.js').replace('__CH__', json.dumps(CH))
    doc = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Aletto · Top of funnel · {E(S['week_label'])}</title><meta name="robots" content="noindex"><link rel="icon" href="{logo}">
<style>{css}</style></head><body><div class="prog" id="prog"></div><div class="deck">{body}</div>
<div class="notes glass" id="notes"><h4>Speaker notes</h4><div id="notesBody"></div></div>
<div class="nav"><button class="nbtn" id="nbtn" title="Speaker notes (N)">Notes</button><button id="prev" aria-label="Previous">‹</button><span id="pg"></span><button id="next" aria-label="Next">›</button></div>
<script>{A('chart.min.js')}</script><script>{js}</script></body></html>'''
    out = os.path.join(R, date)
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'index.html'), 'w').write(doc)
    print('built', date, len(slides), 'slides', len(doc) // 1024, 'KB')
    return date, S, len(slides)


def archive(weeks):
    weeks = sorted(weeks, key=lambda w: w[0], reverse=True)
    latest = weeks[0][0]
    # root = latest week (relative links fixed up)
    doc = open(os.path.join(R, latest, 'index.html')).read().replace('href="../archive/"', 'href="archive/"')
    open(os.path.join(R, 'index.html'), 'w').write(doc)
    css = A('base.css') + A('presenter.css') + A('deck.css')
    rows = ''.join(f'<a class="glass card" href="../{d}/" style="display:block;color:#fff;text-decoration:none;margin-bottom:12px"><div class="lbl">{E(s["title_date"])}{" · latest" if d == latest else ""}</div><b style="font-size:20px">{E(s["week_label"])}</b><p class="hint" style="margin-top:6px;font-size:14px">{E(s["verdict_h"])} · {n} slides</p></a>' for d, s, n in weeks)
    os.makedirs(os.path.join(R, 'archive'), exist_ok=True)
    open(os.path.join(R, 'archive', 'index.html'), 'w').write(f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aletto · Top of funnel · archive</title><meta name="robots" content="noindex"><style>{css} html,body{{overflow:auto}}</style></head><body><div style="position:relative;z-index:1;max-width:860px;margin:0 auto;padding:6vh 20px"><div class="kicker">Aletto · Friday top-of-funnel pack</div><h1 style="margin:10px 0 24px">Every week<span class="dot">.</span></h1>{rows}</div></body></html>''')
    print('archive', [w[0] for w in weeks])


if __name__ == '__main__':
    args = sys.argv[1:]
    targets = sorted(glob.glob(os.path.join(R, 'weeks', '*'))) if (not args or args[0] == '--all') else args
    built = [build(t) for t in targets]
    # archive lists every week that has been built, not just this run
    allw = []
    for w in sorted(glob.glob(os.path.join(R, 'weeks', '*'))):
        s = json.load(open(os.path.join(w, 'story.json')))
        if os.path.exists(os.path.join(R, s['date'], 'index.html')):
            n = next((b[2] for b in built if b[0] == s['date']), open(os.path.join(R, s['date'], 'index.html')).read().count('<section class="slide"'))
            allw.append((s['date'], s, n))
    archive(allw)
