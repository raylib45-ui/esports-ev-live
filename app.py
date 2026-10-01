# constants.py
# Every tunable in the model lives here. Nothing in model.py hard-codes a
# magic number — change it here and the whole pipeline follows.

# KPR blend (30-day recency vs 90-day sample)
KPR_30D_WEIGHT = 0.6
KPR_90D_WEIGHT = 0.4

# Sharp blend: how much the sharp projection pulls the KPR x rounds number
SHARP_BLEND_WEIGHT = 0.5

# Mismatch multipliers (screenshot rank gap, HLTV ranks only)
MISMATCH_GAP_100_MULT = 1.25
MISMATCH_GAP_50_MULT = 1.15
MISMATCH_GAP_20_MULT = 1.08

# Volatility floor / default (last-five population SD, kills)
SIGMA_FLOOR = 6.0
SIGMA_DEFAULT = 7.0

# Straddle gate: straddle PASSes only when canonical 1:1 EV is strictly
# under this absolute value
STRADDLE_EV_MAX = 0.02

# Conviction cutoffs (absolute canonical 1:1 EV)
EV_HAMMER = 0.06
EV_STANDARD = 0.02

# Words too generic to ever count as a contamination hit
STOPLIST_WORDS = [
    'the', 'and', 'for', 'with', 'from', 'this', 'that', 'last', 'five',
    'maps', 'kills', 'line', 'projection', 'more', 'less', 'over', 'under',
    'match', 'team', 'game', 'player', 'stats', 'round', 'rounds', 'map1',
    'map2', 'hltv', 'prizepicks', 'underdog', 'sharp', 'form', 'recent',
]
# model.py
# Pure CS2 Maps 1-2 kills prop engine. Standard library only.
#
# Pipeline per pick:
#   1. Input-integrity gate  (cross-player contamination -> PASS both books,
#                             nothing exposed)
#   2. No-fabrication gate   (no player-specific evidence -> PASS both books)
#   3. Projection            (KPR x rounds x mismatch, blended with sharp;
#                             None -> PASS)
#   4. Per-book evaluation   (PrizePicks and Underdog fully independent):
#        side -> demon check -> straddle gate -> range gate -> fire with conviction
#   5. Board-level warnings  (correlation, duplicate player)
#
# Faithful Python port of the model specification. It is NOT the hosted app's
# literal source — same rules, documented tunables (see constants.py), and its
# own sigma calibration.

import math
import re

from constants import (
    KPR_30D_WEIGHT,
    KPR_90D_WEIGHT,
    SHARP_BLEND_WEIGHT,
    MISMATCH_GAP_100_MULT,
    MISMATCH_GAP_50_MULT,
    MISMATCH_GAP_20_MULT,
    SIGMA_FLOOR,
    SIGMA_DEFAULT,
    STRADDLE_EV_MAX,
    EV_HAMMER,
    EV_STANDARD,
    STOPLIST_WORDS,
)

_TOKEN_RE = re.compile(r'\b[A-Za-z][A-Za-z0-9_]{2,15}\b')
_STOPLIST = {w.lower() for w in STOPLIST_WORDS}


# ---------------------------------------------------------------- helpers

def is_real_number(x):
    """True only for a finite int/float (bools excluded)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def real_numbers(arr):
    return [x for x in (arr if isinstance(arr, list) else []) if is_real_number(x)]


def normalize_name(s):
    return re.sub(r'[^a-z0-9]', '', str(s if s is not None else '').lower())


def round_n(x, n):
    """Round-half-up to n decimals (matches the JS Math.round semantics)."""
    f = 10 ** n
    return math.floor(x * f + 0.5) / f


def round1(x):
    return round_n(x, 1)


def normal_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ------------------------------------------------------- gate 1: integrity

def check_integrity(pick):
    """Cross-player contamination check over notes + last_five_note.

    A hard FAIL if any registered alias of another player appears anywhere in
    the text, or any non-stoplist token (excluding the pick's own player name)
    repeats 2+ times. Never guesses: a single mention is not a hit.
    """
    player = normalize_name(pick.get('player'))
    text = '{0} {1}'.format(pick.get('notes') or '', pick.get('last_five_note') or '')
    norm_text = normalize_name(text)

    for a in pick.get('other_player_aliases') or []:
        na = normalize_name(a)
        if na and na in norm_text:
            return {'integrity_ok': False, 'hit': str(a)}

    counts = {}
    for m in _TOKEN_RE.finditer(text):
        tok = m.group(0).lower()
        counts[tok] = counts.get(tok, 0) + 1

    for tok, n in counts.items():
        if n < 2:
            continue
        if tok in _STOPLIST:
            continue
        nt = normalize_name(tok)
        if player and (player in nt or nt in player):
            continue
        return {'integrity_ok': False, 'hit': tok}

    return {'integrity_ok': True, 'hit': None}


# -------------------------------------------------- gate 2: no fabrication

def has_evidence(pick):
    """True only when there is player-specific evidence for THIS pick."""
    return bool(
        pick.get('hltv_evidence') is True
        or pick.get('kpr_30d') is not None
        or pick.get('kpr_90d') is not None
        or pick.get('sharp_projection') is not None
        or real_numbers(pick.get('last_five'))
        or (pick.get('notes') or '').strip()
    )


# ------------------------------------------------------- projection math

def mismatch_multiplier(gap):
    if not is_real_number(gap):
        return 1.0
    if gap >= 100:
        return MISMATCH_GAP_100_MULT
    if gap >= 50:
        return MISMATCH_GAP_50_MULT
    if gap >= 20:
        return MISMATCH_GAP_20_MULT
    return 1.0


def compute_projection(pick):
    """Numeric projection, or None when the inputs do not support one.

    Never invents inputs: no KPR and no sharp projection means no number.
    """
    ha = is_real_number(pick.get('kpr_30d'))
    hb = is_real_number(pick.get('kpr_90d'))
    has_sharp = is_real_number(pick.get('sharp_projection'))
    has_rounds = is_real_number(pick.get('expected_rounds'))

    if not (ha or hb) and not has_sharp:
        return None  # no KPR at all and no sharp: nothing to project from

    kpr = None
    if ha and hb:
        kpr = KPR_30D_WEIGHT * pick['kpr_30d'] + KPR_90D_WEIGHT * pick['kpr_90d']
    elif ha:
        kpr = pick['kpr_30d']
    elif hb:
        kpr = pick['kpr_90d']

    kpr_proj = None
    if kpr is not None and has_rounds:
        kpr_proj = (
            kpr
            * pick['expected_rounds']
            * mismatch_multiplier(pick.get('opponent_rank_gap'))
        )

    sharp = pick.get('sharp_projection') if has_sharp else None

    if kpr_proj is not None and sharp is not None:
        return round1(
            (1 - SHARP_BLEND_WEIGHT) * kpr_proj + SHARP_BLEND_WEIGHT * sharp
        )
    if kpr_proj is not None:
        return round1(kpr_proj)
    if sharp is not None:
        return round1(sharp)
    return None


def compute_sigma(pick):
    """Population SD of submitted last-five, floored; default when absent."""
    hist = real_numbers(pick.get('last_five'))
    if len(hist) >= 2:
        mean = sum(hist) / len(hist)
        var = sum((x - mean) ** 2 for x in hist) / len(hist)
        return round_n(max(math.sqrt(var), SIGMA_FLOOR), 2)
    return SIGMA_DEFAULT


def trailing_three(pick):
    """Mean of the most recent three games, or None when order is unknown.

    Requires last_five_order_known; last-five submitted oldest->newest.
    """
    if not pick.get('last_five_order_known'):
        return None
    hist = real_numbers(pick.get('last_five'))
    if len(hist) < 3:
        return None
    return sum(hist[-3:]) / 3.0


# ------------------------------------------------------- per-book engine

def _blocked_book(book, line, result):
    return {
        'book': book,
        'call': None,
        'line': line if is_real_number(line) else None,
        'side': None,
        'projection': result['projection'],
        'sigma': result['sigma'],
        'trailing3': result['trailing3'],
        'winProb': None,
        'ev': None,
        'conviction': None,
        'reason': None,
        'biggestRisk': None,
    }


def evaluate_book(book, line, result, pick):
    """Evaluate ONE book fully independently. Never sees the other book."""
    ctx = _blocked_book(book, line, result)
    if ctx['line'] is None:
        ctx['reason'] = 'No line for this book — PASS.'
        return ctx
    if result['projection'] is None:
        ctx['reason'] = 'No supported projection — PASS.'
        return ctx

    proj = result['projection']
    sigma = result['sigma']

    if proj == ctx['line']:
        ctx['reason'] = 'Projection equals line — PASS.'
        return ctx
    side = 'MORE' if proj > ctx['line'] else 'LESS'
    ctx['side'] = side

    # PrizePicks More-only demons are bait — never recommend them.
    demon = book == 'PrizePicks' and pick.get('pp_demon_more_only') is True
    if side == 'MORE' and demon:
        ctx['reason'] = 'PrizePicks More-only demon line — bait, PASS.'
        return ctx

    # Straddle gate: form (trailing-3) and projection on opposite sides of the
    # line with a tiny canonical edge -> the recent form disagrees, PASS.
    t3 = result.get('trailing3_raw')
    if t3 is not None and sigma > 0:
        z = (ctx['line'] - proj) / sigma
        p_win = (1 - normal_cdf(z)) if side == 'MORE' else normal_cdf(z)
        ev = 2 * p_win - 1
        opposite = (t3 > ctx['line']) != (proj > ctx['line'])
        if opposite and abs(ev) < STRADDLE_EV_MAX:
            t3s = '{0:.1f}'.format(round1(t3))
            ctx['reason'] = (
                'Form/KPR straddle: trailing-3 avg {0} vs projection {1} on '
                'opposite sides of the {2} line, edge under 2%.'
            ).format(t3s, proj, ctx['line'])
            return ctx

    # Fire: projection is on one side, sigma quantifies the doubt.
    z = (ctx['line'] - proj) / sigma
    p_win = (1 - normal_cdf(z)) if side == 'MORE' else normal_cdf(z)
    ev = 2 * p_win - 1  # canonical 1:1 EV
    ctx['winProb'] = round_n(p_win, 3)
    ctx['ev'] = round_n(ev * 100, 1)
    abs_ev = abs(ev)
    ctx['conviction'] = (
        'HAMMER' if abs_ev >= EV_HAMMER
        else 'STANDARD' if abs_ev >= EV_STANDARD
        else 'LIGHT'
    )

    lo = proj - sigma
    hi = proj + sigma
    clears = ctx['line'] < lo if side == 'MORE' else ctx['line'] > hi
    if not clears:
        ctx['call'] = None
        ctx['reason'] = (
            'Projection ± sigma range {0}-{1} straddles the {2} line — PASS.'
        ).format(round1(lo), round1(hi), ctx['line'])
        ctx['biggestRisk'] = (
            'Range straddle: {0} of the projection ± sigma band sits on the '
            'wrong side of the line.'.format(side.lower())
        )
        return ctx

    ctx['call'] = side
    ctx['reason'] = (
        'Projection {0} vs {1} line; canonical 1:1 EV {2}%.'
    ).format(proj, ctx['line'], ctx['ev'])
    ctx['biggestRisk'] = (
        'Volatility: last-five sigma {0} — a cold two maps sinks this.'
        if side == 'MORE' else
        'Volatility: last-five sigma {0} — a pop-off two maps sinks this.'
    ).format(sigma)
    return ctx