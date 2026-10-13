# -*- coding: utf-8 -*-
"""Reference implementation of the layered settings resolution (spec: docs/source-settings.en.md).
Layers, strongest first:  source x class  >  class (user)  >  source (+offset / gate / schedule / clips)  >  global defaults  >  catalog suggestion
Each resolved field also reports its provenance, so the UI can show "why" a value applies."""
import copy
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


RETENTION_CATEGORIES = ('normal', 'sensitive', 'context', 'confidential')


def retention_category(c):
    """Which clip-retention setting a class follows: its privacy level first, then whether it is a context sound."""
    if c['privacy'] == 'confidential' or c['clip_forbidden']:
        return 'confidential'
    if c['privacy'] == 'sensitive':
        return 'sensitive'
    return 'context' if c['interest'] == 'context' else 'normal'


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


# ---------------------------------------------------------------------------------------------------------------- presets
PRESET_SOUND_FIELDS = ('enabled', 'threshold', 'min_duration_s', 'cooldown_s', 'pre_roll_s', 'post_roll_s', 'clip_retention_days')
PRESET_SOURCE_FIELDS = ('min_volume_dbfs', 'clips_allowed', 'adaptive')
PRESET_MAX_VOLUME = -50       # a preset never sets a gate above this, so that safety sounds are still heard


def preset_index(cfg, catalog):
    """Presets by id: the ones of the catalog, then the ones of the user (their ids cannot collide, the configuration is validated)."""
    out = {p['id']: p for p in catalog.raw.get('presets', [])}
    for p in cfg.get('presets') or []:
        out.setdefault(p['id'], p)
    return out


def _eases(field, value, base_block, c):
    """For a safety sound a preset may only make detection easier (or equal): never a higher threshold, a longer minimum duration or a longer
    cooldown, never switching it off."""
    if field == 'enabled':
        return value is True
    base = base_block.get(field, c['suggestions'].get(field))
    if field in ('threshold', 'min_duration_s', 'cooldown_s'):
        return base is None or value <= base
    return True


def fold_source(cfg, catalog, src, index=None):
    """The source as it is in effect: the presets listed on it (in order, the last one wins) fill in what the source does not set itself.
    A copy is returned, with `_origin` saying which preset gave which value; the stored configuration is never changed."""
    index = index if index is not None else preset_index(cfg, catalog)
    ids = [i for i in src.get('presets') or [] if i in index]
    if not ids:
        return src
    gcls = _index(cfg.get('classes'), catalog)
    explicit = _index(src.get('classes'), catalog)
    from_presets, sounds_origin, fields_origin = {}, {}, {}
    for pid in ids:
        p = index[pid]
        for key, blk in (p.get('sounds') or {}).items():
            try:
                c = catalog.get(key)
            except KeyError:
                continue
            for f, v in (blk or {}).items():
                if f not in PRESET_SOUND_FIELDS or (is_safety(c) and not _eases(f, v, gcls.get(c['mid'], {}), c)):
                    continue
                from_presets.setdefault(c['mid'], {})[f] = v
                sounds_origin.setdefault(c['mid'], {})[f] = pid
        for f, v in (p.get('source') or {}).items():
            if f in PRESET_SOURCE_FIELDS:
                fields_origin[f] = (v, pid)
    e = copy.deepcopy(src)
    classes = {k: v for k, v in (src.get('classes') or {}).items() if catalog.get(k)['mid'] not in from_presets}
    for mid, blk in from_presets.items():
        merged = dict(blk)
        merged.update(explicit.get(mid, {}))                       # what the source sets itself wins
        classes[mid] = merged
        for f in explicit.get(mid, {}):
            sounds_origin[mid].pop(f, None)
    if classes:
        e['classes'] = classes
    origin = {'sounds': {m: o for m, o in sounds_origin.items() if o}, 'fields': {}, 'ids': ids}
    if 'min_volume_dbfs' in fields_origin and 'min_volume_dbfs' not in src:
        e['min_volume_dbfs'] = min(fields_origin['min_volume_dbfs'][0], PRESET_MAX_VOLUME)
        origin['fields']['min_volume_dbfs'] = fields_origin['min_volume_dbfs'][1]
    if 'clips_allowed' in fields_origin and 'allowed' not in (src.get('clips') or {}):
        e['clips'] = {**(src.get('clips') or {}), 'allowed': fields_origin['clips_allowed'][0]}
        origin['fields']['clips_allowed'] = fields_origin['clips_allowed'][1]
    if 'adaptive' in fields_origin and 'enabled' not in (src.get('adaptive') or {}):
        e['adaptive'] = {**(src.get('adaptive') or {}), 'enabled': bool(fields_origin['adaptive'][0])}
        origin['fields']['adaptive'] = fields_origin['adaptive'][1]
    e['_origin'] = origin
    return e


def fold(cfg, catalog):
    """The configuration as it is in effect, presets included (what the detection and the integration use)."""
    if not any(s.get('presets') for s in cfg.get('sources') or []):
        return cfg
    index = preset_index(cfg, catalog)
    out = dict(cfg)
    out['sources'] = [fold_source(cfg, catalog, s, index) for s in cfg.get('sources') or []]
    return out


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

    # ---- condition on Home Assistant states: same levels as the schedule; none by default
    for lvl, d in (('source_class', scls), ('class', gcls), ('source', src), ('defaults', dflt)):
        if 'condition' in d:
            out['condition'], why['condition'] = d['condition'] or None, lvl
            break
    else:
        out['condition'], why['condition'] = None, 'builtin'

    # ---- clips: source x class > class > category on the source > category (global) > catalog; then capped by the source and global
    # maxima and forced to 0 when the source disallows clips. The catalog's clip_forbidden (conversations) is only the 0-day default.
    clips = src.get('clips') or {}
    cat_key = retention_category(c)
    if 'clip_retention_days' in scls: r, w = scls['clip_retention_days'], 'source_class'
    elif 'clip_retention_days' in gcls: r, w = gcls['clip_retention_days'], 'class'
    elif cat_key in (clips.get('retention_by_category') or {}): r, w = clips['retention_by_category'][cat_key], 'source_category'
    elif cat_key in ((dflt.get('clips') or {}).get('retention_by_category') or {}): r, w = dflt['clips']['retention_by_category'][cat_key], 'category'
    elif c['clip_forbidden']: r, w = 0, 'catalog_confidential'
    else: r, w = sug['clip_retention_days'], 'catalog'
    caps = [x for x in (clips.get('max_retention_days'), (dflt.get('clips') or {}).get('max_retention_days')) if x is not None]
    if caps and r > min(caps):
        r, w = min(caps), 'cap'
    if not clips.get('allowed', (dflt.get('clips') or {}).get('allowed', True)):
        r, w = 0, 'source_clips_disallowed'
    out['clip_retention_days'], why['clip_retention_days'] = r, w
    origin = src.get('_origin')
    if origin:                                                   # a value that came from a preset says so
        for f, pid in (origin['sounds'].get(mid) or {}).items():
            if f in why and why[f] == 'source_class':
                why[f] = 'preset'
        if 'min_volume_dbfs' in origin['fields'] and why.get('min_volume_dbfs') == 'source':
            why['min_volume_dbfs'] = 'preset'
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
            if clips_off and s['clip_retention_days'] == 0 and c['suggestions']['clip_retention_days'] > 0 and not c['clip_forbidden']:
                res.append(('clip_source_disallowed', src['id'], c['audioset_name'], {}))
    seen, out = set(), []
    for r in res:
        k = (r[0], r[1], r[2])
        if k not in seen:
            seen.add(k); out.append(r)
    return out
