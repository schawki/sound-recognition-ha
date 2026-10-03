# -*- coding: utf-8 -*-
"""Reference implementation of the layered settings resolution (spec: docs/source-settings.en.md).
Layers, strongest first:  source x class  >  class (user)  >  source (+offset / gate / schedule / clips)  >  global defaults  >  catalog suggestion
Each resolved field also reports its provenance, so the UI can show "why" a value applies."""
import datetime as dt

DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
SAFETY_USAGES = {'fire', 'security', 'baby'}
CONTINUOUS = {'mode': 'continuous'}


class Catalog:
    def __init__(self, cat):
        self.raw = cat
        self.by_mid = {c['mid']: c for c in cat['classes']}
        self.by_name = {c['audioset_name']: c for c in cat['classes']}

    def get(self, key):
        c = self.by_mid.get(key) or self.by_name.get(key)
        if not c:
            raise KeyError(f'unknown class: {key}')
        return c


def _index(d, catalog):
    """config dict keyed by mid OR AudioSet name -> keyed by mid"""
    return {catalog.get(k)['mid']: v for k, v in (d or {}).items()}


def is_safety(c):
    """safety class = recommended as an alert AND its primary (first) usage is fire, security or baby"""
    return c['interest'] == 'monitor' and bool(c['usages']) and c['usages'][0] in SAFETY_USAGES


def is_always_on(schedule):
    return schedule.get('mode', 'continuous') == 'continuous'


def parse_hm(s):
    h, m = s.split(':')
    return dt.time(int(h), int(m))


def covers_24_7(schedule):
    """True if the schedule never leaves a gap (continuous, or windows that jointly cover every minute)."""
    if is_always_on(schedule):
        return True
    base = dt.datetime(2024, 1, 1)  # a Monday
    for minute in range(7 * 24 * 60):
        if not is_active(schedule, base + dt.timedelta(minutes=minute)):
            return False
    return True


def is_active(schedule, now):
    """now: naive datetime already expressed in the HA time zone."""
    if is_always_on(schedule):
        return True
    for w in schedule.get('windows', []):
        days = w.get('days') or DAYS
        start, end = parse_hm(w['from']), parse_hm(w['to'])
        for back in (0, 1):  # a window that crosses midnight belongs to the day it starts on
            day = now.date() - dt.timedelta(days=back)
            if DAYS[day.weekday()] not in days:
                continue
            t0 = dt.datetime.combine(day, start)
            t1 = dt.datetime.combine(day, end)
            if t1 <= t0:
                t1 += dt.timedelta(days=1)
            if t0 <= now < t1:
                return True
    return False


def resolve(cfg, catalog, source_id, cls_key):
    c = catalog.get(cls_key)
    mid = c['mid']
    src = next(s for s in cfg['sources'] if s['id'] == source_id)
    dflt = cfg.get('defaults') or {}
    gcls = _index(cfg.get('classes'), catalog).get(mid, {})
    scls = _index(src.get('classes'), catalog).get(mid, {})
    sug = c['suggestions']
    out, why = {}, {}

    # ---- enabled
    if not src.get('enabled', True):
        out['enabled'], why['enabled'] = False, 'source'
    elif 'enabled' in scls:
        out['enabled'], why['enabled'] = scls['enabled'], 'source_class'
    elif 'enabled' in gcls:
        out['enabled'], why['enabled'] = gcls['enabled'], 'class'
    else:
        out['enabled'], why['enabled'] = False, 'default'

    # ---- threshold (absolute on source x class; otherwise class value + source offset)
    if 'threshold' in scls:
        v, w = scls['threshold'], 'source_class'
    else:
        base, w0 = (gcls['threshold'], 'class') if 'threshold' in gcls else (sug['threshold'], 'catalog')
        off = src.get('threshold_offset', 0.0)
        v, w = base + off, (w0 + '+source_offset' if off else w0)
    out['threshold'], why['threshold'] = round(min(0.99, max(0.05, v)), 3), w

    # ---- plain numbers: source x class > class > catalog
    for f, key in (('min_duration_s', 'min_duration_s'), ('cooldown_s', 'cooldown_s'),
                   ('pre_roll_s', 'pre_roll_s'), ('post_roll_s', 'post_roll_s')):
        if key in scls: out[f], why[f] = scls[key], 'source_class'
        elif key in gcls: out[f], why[f] = gcls[key], 'class'
        else: out[f], why[f] = sug[key], 'catalog'

    # ---- minimum volume gate (dBFS): explicit source x class wins; otherwise the stricter (higher) of class and source/global
    if 'min_volume_dbfs' in scls:
        out['min_volume_dbfs'], why['min_volume_dbfs'] = scls['min_volume_dbfs'], 'source_class'
    else:
        cands = [(src.get('min_volume_dbfs', dflt.get('min_volume_dbfs')), 'source' if 'min_volume_dbfs' in src else 'defaults'),
                 (gcls.get('min_volume_dbfs'), 'class')]
        cands = [(v, w) for v, w in cands if v is not None]
        out['min_volume_dbfs'], why['min_volume_dbfs'] = max(cands) if cands else (None, 'none')

    # ---- schedule
    for lvl, d in (('source_class', scls), ('class', gcls), ('source', src), ('defaults', dflt)):
        if 'schedule' in d:
            out['schedule'], why['schedule'] = d['schedule'], lvl
            break
    else:
        out['schedule'], why['schedule'] = CONTINUOUS, 'builtin'

    # ---- clips: class/source x class value, capped by source and global maxima; forced to 0 when forbidden or disallowed
    if 'clip_retention_days' in scls: r, w = scls['clip_retention_days'], 'source_class'
    elif 'clip_retention_days' in gcls: r, w = gcls['clip_retention_days'], 'class'
    else: r, w = sug['clip_retention_days'], 'catalog'
    clips = src.get('clips') or {}
    caps = [x for x in (clips.get('max_retention_days'), (dflt.get('clips') or {}).get('max_retention_days')) if x is not None]
    if caps and r > min(caps):
        r, w = min(caps), 'cap'
    if not clips.get('allowed', (dflt.get('clips') or {}).get('allowed', True)):
        r, w = 0, 'source_clips_disallowed'
    if c['clip_forbidden']:
        r, w = 0, 'catalog_clip_forbidden'
    out['clip_retention_days'], why['clip_retention_days'] = r, w
    out['provenance'] = why
    return out


def warnings(cfg, catalog):
    """Source-specific warnings (the 3 automatic rules added for per-source settings)."""
    res = []
    for src in cfg['sources']:
        if not src.get('enabled', True):
            continue
        for key in list(_index(cfg.get('classes'), catalog)) + list(_index(src.get('classes'), catalog)):
            c = catalog.get(key)
            s = resolve(cfg, catalog, src['id'], c['mid'])
            if not s['enabled']:
                continue
            if is_safety(c):
                if s['provenance']['schedule'] in ('source', 'defaults') and not covers_24_7(s['schedule']):
                    res.append(('schedule_gap_safety', src['id'], c['audioset_name'], {}))
                g = s['min_volume_dbfs']
                if g is not None and g > -40:
                    res.append(('volume_gate_safety', src['id'], c['audioset_name'], {'gate': g}))
            clips_off = not (src.get('clips') or {}).get('allowed', ((cfg.get('defaults') or {}).get('clips') or {}).get('allowed', True))
            if clips_off and c['suggestions']['clip_retention_days'] > 0 and not c['clip_forbidden']:
                res.append(('clip_source_disallowed', src['id'], c['audioset_name'], {}))
    seen, out = set(), []
    for r in res:
        k = (r[0], r[1], r[2])
        if k not in seen:
            seen.add(k); out.append(r)
    return out
