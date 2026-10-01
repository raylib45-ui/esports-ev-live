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


# ------------------------------------------------------- pick-level driver

def evaluate_pick(pick):
    """Full pipeline for one pick. Contaminated or evidence-free picks PASS
    both books with no projection, EV or call exposed."""
    pick = dict(pick or {})

    result = {
        'player': pick.get('player') or 'Unknown player',
        'projection': None,
        'sigma': None,
        'trailing3': None,
        'trailing3_raw': None,
        'books': {},
        'verdict': 'PASS',
        'preferredBook': None,
        'reason': None,
        'warnings': [],
    }

    # Gate 1 — integrity. Failure blocks everything; nothing leaks.
    integ = check_integrity(pick)
    if not integ['integrity_ok']:
        result['reason'] = (
            'Input integrity failed (contamination token "{0}") — PASS both '
            'books. No projection, EV or call is shown because the inputs '
            'cannot be trusted.'
        ).format(integ['hit'])
        result['books']['prizepicks'] = _blocked_book('PrizePicks', pick.get('pp_line'), result)
        result['books']['underdog'] = _blocked_book('Underdog', pick.get('ud_line'), result)
        return result

    # Gate 2 — no fabrication.
    if not has_evidence(pick):
        result['reason'] = 'No player-specific evidence — PASS both books.'
        result['books']['prizepicks'] = _blocked_book('PrizePicks', pick.get('pp_line'), result)
        result['books']['underdog'] = _blocked_book('Underdog', pick.get('ud_line'), result)
        return result

    # Projection + volatility + form.
    result['projection'] = compute_projection(pick)
    result['sigma'] = compute_sigma(pick)
    t3 = trailing_three(pick)
    result['trailing3_raw'] = t3
    result['trailing3'] = round1(t3) if t3 is not None else None

    # Per-book evaluation, fully independent.
    result['books']['prizepicks'] = evaluate_book('PrizePicks', pick.get('pp_line'), result, pick)
    result['books']['underdog'] = evaluate_book('Underdog', pick.get('ud_line'), result, pick)

    fired = [b for b in result['books'].values() if b['call'] is not None]
    if not fired:
        result['verdict'] = 'PASS'
    elif all(b['call'] == fired[0]['call'] for b in fired):
        result['verdict'] = fired[0]['call']
    else:
        result['verdict'] = 'SPLIT'

    if fired:
        best = max(
            fired,
            key=lambda b: b['ev'] if b['ev'] is not None else float('-inf'),
        )
        result['preferredBook'] = best['book']

    return result


# ------------------------------------------------------- board-level driver

def evaluate_board(picks):
    """Evaluate a slate: one prop per player, plus correlation warnings."""
    results = [evaluate_pick(p) for p in (picks or [])]

    # One prop per player: keep the highest-|EV| pick when duplicated.
    seen = {}
    for r in results:
        key = normalize_name(r['player'])
        cur = seen.get(key)
        if cur is None:
            seen[key] = r
            continue
        cur_ev = abs((cur['preferredBook'] and
                      next((b['ev'] for b in cur['books'].values()
                            if b['book'] == cur['preferredBook']), None)) or 0)
        r_ev = abs((r['preferredBook'] and
                    next((b['ev'] for b in r['books'].values()
                          if b['book'] == r['preferredBook']), None)) or 0)
        if r_ev > cur_ev:
            r['warnings'].append(
                'Duplicate prop for {0}: kept the higher-|EV| entry.'.format(r['player'])
            )
            seen[key] = r
        else:
            cur['warnings'].append(
                'Duplicate prop for {0}: kept the higher-|EV| entry.'.format(r['player'])
            )
    deduped = list(seen.values())

    # Correlation warning at 3+ same-team / same-direction plays.
    groups = {}
    for r in deduped:
        for b in r['books'].values():
            if b['call'] is None:
                continue
            gkey = '{0}|{1}'.format(normalize_name(b.get('team') or ''), b['call'])
            groups.setdefault(gkey, []).append(
                '{0} ({1} {2} {3})'.format(r['player'], b['book'], b['call'], b['line'])
            )
    warnings = []
    for legs in groups.values():
        if len(legs) >= 3:
            warnings.append(
                'Correlation risk: {0} same-team/same-direction legs — {1}. '
                'Edges stay valid; size accordingly.'.format(len(legs), '; '.join(legs))
            )

    fired = [r for r in deduped if r['verdict'] in ('MORE', 'LESS')]
    fired.sort(
        key=lambda r: max(
            (abs(b['ev']) for b in r['books'].values() if b['ev'] is not None),
            default=0,
        ),
        reverse=True,
    )
    return {'picks': deduped, 'fired': fired, 'warnings': warnings}
    # test_model.py — 28 regression tests for the model. Stdlib unittest only.
# Run:  python -m unittest test_model -v
#
# The fixtures below recreate the stored cards from the live app (Afro,
# Phzy, Fear) with synthetic supporting inputs where the original inputs
# were unavailable. They verify the rules, not the app's exact calibration.

import math
import unittest

from model import (
    check_integrity,
    compute_projection,
    compute_sigma,
    evaluate_board,
    evaluate_pick,
    has_evidence,
    mismatch_multiplier,
    normal_cdf,
    trailing_three,
)


def base_pick(**over):
    p = {
        'player': 'Test Player',
        'team': 'Test Team',
        'pp_line': 29.5,
        'ud_line': 30.5,
        'kpr_30d': 0.72,
        'kpr_90d': 0.695,
        'expected_rounds': 43,
        'sharp_projection': None,
        'opponent_rank_gap': None,
        'last_five': [28, 31, 33, 29, 34],
        'last_five_order_known': True,
        'pp_demon_more_only': False,
        'ud_demon_more_only': False,
        'hltv_evidence': True,
        'notes': 'HLTV stats pasted by user',
        'last_five_note': None,
        'other_player_aliases': [],
    }
    p.update(over)
    return p


class TestHelpers(unittest.TestCase):
    def test_normal_cdf_midpoint(self):
        self.assertAlmostEqual(normal_cdf(0), 0.5, places=6)

    def test_normal_cdf_two_sigma(self):
        self.assertAlmostEqual(normal_cdf(2), 0.97725, places=4)

    def test_mismatch_multipliers(self):
        self.assertEqual(mismatch_multiplier(120), 1.25)
        self.assertEqual(mismatch_multiplier(60), 1.15)
        self.assertEqual(mismatch_multiplier(25), 1.08)
        self.assertEqual(mismatch_multiplier(10), 1.0)
        self.assertEqual(mismatch_multiplier(None), 1.0)

    def test_trailing_three(self):
        self.assertAlmostEqual(
            trailing_three(base_pick(last_five=[10, 20, 31, 32, 33])), 32.0, places=2)
        self.assertIsNone(trailing_three(base_pick(last_five_order_known=False)))
        self.assertIsNone(trailing_three(base_pick(last_five=[30, 31])))

    def test_compute_sigma_floors(self):
        self.assertAlmostEqual(compute_sigma(base_pick()), 6.0, places=2)
        self.assertAlmostEqual(
            compute_sigma(base_pick(last_five=[9, 17, 37, 35, 47])), 13.91, places=2)
        self.assertEqual(compute_sigma(base_pick(last_five=None)), 7.0)

    def test_compute_projection_blend(self):
        # blend: 0.6*0.72 + 0.4*0.695 = 0.71; 0.71 * 43 = 30.53 -> 30.5
        self.assertAlmostEqual(compute_projection(base_pick()), 30.5, places=2)

    def test_compute_projection_sharp_blend(self):
        self.assertAlmostEqual(
            compute_projection(base_pick(sharp_projection=32.0)), 31.3, places=2)

    def test_compute_projection_mismatch(self):
        self.assertAlmostEqual(
            compute_projection(base_pick(opponent_rank_gap=120)), 38.2, places=2)

    def test_compute_projection_no_inputs(self):
        p = base_pick(kpr_30d=None, kpr_90d=None, sharp_projection=None)
        self.assertIsNone(compute_projection(p))
        p2 = base_pick(kpr_30d=0.72, expected_rounds=None)
        self.assertIsNone(compute_projection(p2))

    def test_has_evidence(self):
        self.assertTrue(has_evidence(base_pick()))
        self.assertFalse(has_evidence(base_pick(
            hltv_evidence=False, kpr_30d=None, kpr_90d=None,
            sharp_projection=None, last_five=None, notes='')))


class TestIntegrity(unittest.TestCase):
    def test_alias_contamination(self):
        r = evaluate_pick(base_pick(
            player='Fear',
            other_player_aliases=['Phzy', 'phzycs'],
            notes='Phzy dropped 43 kills last series phzycs was unreal',
        ))
        self.assertEqual(r['verdict'], 'PASS')
        self.assertIsNone(r['projection'])
        self.assertIn('contamination', r['reason'])
        for b in r['books'].values():
            self.assertIsNone(b['call'])
            self.assertIsNone(b['ev'])
            self.assertIsNone(b['biggestRisk'])

    def test_repeated_token_contamination(self):
        r = evaluate_pick(base_pick(
            player='Fear',
            notes='esenthial went huge, esenthial is in form',
        ))
        self.assertEqual(r['verdict'], 'PASS')
        self.assertIsNone(r['projection'])

    def test_clean_player_name_repetition(self):
        r = evaluate_pick(base_pick(
            player='Fear',
            kpr_30d=0.9, kpr_90d=0.86,
            notes='Fear has been consistent, fear the reaper fear',
        ))
        self.assertEqual(r['books']['prizepicks']['call'], 'MORE')

    def test_stoplist_tokens_ignored(self):
        self.assertTrue(check_integrity(
            base_pick(notes='the the the and and and'))['integrity_ok'])


class TestGates(unittest.TestCase):
    def test_no_evidence_blocks_everything(self):
        r = evaluate_pick(base_pick(
            hltv_evidence=False, kpr_30d=None, kpr_90d=None,
            sharp_projection=None, last_five=None, notes='',
            last_five_note=''))
        self.assertEqual(r['verdict'], 'PASS')
        self.assertIsNone(r['projection'])
        self.assertIsNone(r['books']['prizepicks']['call'])
        self.assertIsNone(r['books']['underdog']['call'])

    def test_equal_projection_passes(self):
        r = evaluate_pick(base_pick(pp_line=30.5, ud_line=30.5))
        self.assertEqual(r['verdict'], 'PASS')
        self.assertEqual(r['projection'], 30.5)

    def test_demon_more_only_blocks(self):
        r = evaluate_pick(base_pick(
            kpr_30d=0.75, kpr_90d=0.75, pp_line=29.5, ud_line=25.5,
            pp_demon_more_only=True,
        ))
        self.assertIsNone(r['books']['prizepicks']['call'])
        self.assertRegex(r['books']['prizepicks']['reason'], r'[Dd]emon')
        self.assertEqual(r['books']['underdog']['call'], 'MORE')
        self.assertEqual(r['books']['underdog']['conviction'], 'HAMMER')
        self.assertEqual(r['preferredBook'], 'Underdog')


class TestStraddle(unittest.TestCase):
    def test_straddle_triggers_exact_reason(self):
        # kpr 0.707*43 = 30.4 proj; trailing-3 = 32.0 opposite side of 30.5;
        # sigma floored to 6.0 -> EV ~1.3% < 2%
        r = evaluate_pick(base_pick(
            kpr_30d=0.707, kpr_90d=0.707, pp_line=30.5, ud_line=31.5,
            last_five=[20, 22, 31, 32, 33],
        ))
        self.assertEqual(r['projection'], 30.4)
        b = r['books']['prizepicks']
        self.assertIsNone(b['call'])
        self.assertEqual(
            b['reason'],
            'Form/KPR straddle: trailing-3 avg 32.0 vs projection 30.4 on '
            'opposite sides of the 30.5 line, edge under 2%.')

    def test_straddle_needs_opposite_sides(self):
        r = evaluate_pick(base_pick(
            kpr_30d=0.707, kpr_90d=0.707, pp_line=37.0, ud_line=31.5,
            last_five=[20, 22, 31, 32, 21],  # trailing-3 = 28.0, same side
        ))
        self.assertEqual(r['books']['prizepicks']['call'], 'LESS')

    def test_straddle_needs_low_edge(self):
        # projection 30.6 vs line 24.0: opposite sides but EV ~73% — the edge
        # is real, so it fires instead of straddle-passing
        r = evaluate_pick(base_pick(
            kpr_30d=0.72, kpr_90d=0.70, pp_line=24.0, ud_line=31.5,
            last_five=[20, 22, 31, 20, 21],
        ))
        b = r['books']['prizepicks']
        self.assertEqual(b['call'], 'MORE')

    def test_straddle_never_flips_pass(self):
        # whole range above the line is not a straddle — it fires
        r = evaluate_pick(base_pick(
            kpr_30d=0.9, kpr_90d=0.86, pp_line=29.5,
            last_five=[36, 37, 38, 39, 40],
        ))
        self.assertEqual(r['books']['prizepicks']['call'], 'MORE')


class TestFiring(unittest.TestCase):
    def test_range_gate_straddle_passes(self):
        # proj 30.5, sigma 6.0 -> range 24.5-36.5 straddles both lines
        r = evaluate_pick(base_pick(pp_line=29.5, ud_line=31.0))
        for b in r['books'].values():
            self.assertIsNone(b['call'])
            self.assertRegex(b['reason'], r'[Ss]traddles')
        self.assertEqual(r['verdict'], 'PASS')

    def test_clear_range_fires(self):
        r = evaluate_pick(base_pick(kpr_30d=0.9, kpr_90d=0.86))
        b = r['books']['prizepicks']
        self.assertEqual(b['call'], 'MORE')
        self.assertEqual(b['conviction'], 'HAMMER')
        self.assertGreaterEqual(b['ev'], 6.0)
        self.assertEqual(r['preferredBook'], 'PrizePicks')

    def test_split_verdict(self):
        # proj 30.3, sigma 6.0: PP line 24.0 clears below, UD line 36.5 clears above
        r = evaluate_pick(base_pick(
            kpr_30d=0.705, kpr_90d=0.705, pp_line=24.0, ud_line=36.5,
            last_five=[30, 31, 30, 31, 30],
        ))
        self.assertEqual(r['books']['prizepicks']['call'], 'MORE')
        self.assertEqual(r['books']['underdog']['call'], 'LESS')
        self.assertEqual(r['verdict'], 'SPLIT')
        self.assertEqual(r['preferredBook'], 'PrizePicks')


class TestHistoricalFixtures(unittest.TestCase):
    def test_afro_fixture(self):
        r = evaluate_pick(base_pick(
            player='Afro', team='Luminosity', matchup='Luminosity vs Legacy',
            pp_line=31.0, ud_line=31.5,
            kpr_30d=0.72, kpr_90d=0.695, expected_rounds=43,
            last_five=[9, 17, 37, 35, 47],
        ))
        self.assertEqual(r['projection'], 30.5)
        self.assertAlmostEqual(r['sigma'], 13.91, places=2)
        self.assertAlmostEqual(r['trailing3'], 39.7, places=2)
        self.assertEqual(r['verdict'], 'PASS')
        self.assertIsNone(r['books']['prizepicks']['call'])
        self.assertIsNone(r['books']['underdog']['call'])

    def test_phzy_fixture(self):
        r = evaluate_pick(base_pick(
            player='Phzy', team='Astralis', matchup='Astralis vs Alliance',
            pp_line=29.5, ud_line=30.5,
            kpr_30d=0.70, kpr_90d=0.70, expected_rounds=43,
            last_five=[21, 37, 9, 36, 43],
        ))
        self.assertEqual(r['projection'], 30.1)
        self.assertAlmostEqual(r['trailing3'], 29.3, places=2)
        self.assertEqual(r['verdict'], 'PASS')

    def test_fear_fixture_contaminated(self):
        r = evaluate_pick(base_pick(
            player='Fear', team='fnatic', matchup='fnatic vs BIG',
            pp_line=23.5, ud_line=22.5,
            kpr_30d=0.70, kpr_90d=0.70, expected_rounds=43,
            last_five=[21, 37, 9, 36, 43],
            other_player_aliases=['Phzy'],
            notes='Phzy dropped 43 last series, Phzy is in form',
            last_five_note='phzy last five 21 37 9 36 43',
        ))
        self.assertEqual(r['verdict'], 'PASS')
        self.assertIsNone(r['projection'])
        self.assertIsNone(r['books']['prizepicks']['call'])
        self.assertIsNone(r['books']['underdog']['call'])
        self.assertIsNone(r['books']['prizepicks']['ev'])
        self.assertIsNone(r['books']['underdog']['biggestRisk'])


class TestBoard(unittest.TestCase):
    def test_board_dedupes_and_warns(self):
        picks = [
            base_pick(player='Afro', team='Luminosity',
                      kpr_30d=0.9, kpr_90d=0.9, pp_line=29.5),
            base_pick(player='afro', team='Luminosity',
                      kpr_30d=0.7, kpr_90d=0.7, pp_line=29.5),
            base_pick(player='Mate', team='Luminosity',
                      kpr_30d=0.9, kpr_90d=0.9, pp_line=29.5),
            base_pick(player='Third', team='Luminosity',
                      kpr_30d=0.9, kpr_90d=0.9, pp_line=29.5),
        ]
        out = evaluate_board(picks)
        self.assertEqual(len(out['picks']), 3)
        self.assertTrue(any('Correlation risk' in w for w in out['warnings']))
        self.assertTrue(any('Duplicate prop' in w
                            for r in out['picks'] for w in r['warnings']))


if __name__ == '__main__':
    unittest.main()
    {"player": "afro", "team": "Luminosity", "matchup": "B8 vs Luminosity", "event": "European Pro League Series 9", "pp_line": 31.0, "ud_line": 31.5, "kpr_30d": 0.72, "kpr_90d": 0.695, "expected_rounds": 43, "last_five": [9, 17, 37, 35, 47], "hltv_evidence": true, "notes": "Luminosity map veto pending", "last_five_note": "last five maps 1-2 kills", "opponent": "B8"}
    {"player": "phzy", "team": "Astralis", "matchup": "Astralis vs Alliance", "event": "European Pro League Series 9", "pp_line": 29.5, "ud_line": 30.5, "kpr_30d": 0.7, "kpr_90d": 0.7, "expected_rounds": 43, "last_five": [21, 37, 9, 36, 43], "hltv_evidence": true, "notes": "Astralis map veto pending", "last_five_note": "last five maps 1-2 kills", "opponent": "Alliance"}
    {"player": "fear", "team": "fnatic", "matchup": "fnatic vs BIG", "event": "European Pro League Series 9", "pp_line": 23.5, "ud_line": 22.5, "kpr_30d": 0.7, "kpr_90d": 0.7, "expected_rounds": 43, "last_five": [21, 37, 9, 36, 43], "hltv_evidence": true, "notes": "Phzy dropped 43 last series, Phzy is in form", "last_five_note": "phzy last five 21 37 9 36 43", "opponent": "BIG", "other_player_aliases": ["Phzy"]}
    streamlit>=1.32
    __pycache__/
*.pyc
.streamlit/secrets.toml
# esports-ev-live

CS2 Maps 1–2 kills prop model, in pure Python (standard library only).
PrizePicks and Underdog are evaluated independently per pick, with their own
line, call, win probability, canonical 1:1 EV, conviction and biggest risk.

> **Honesty note.** This is a faithful open reimplementation of the model
> specification — same rules, same gates, same reason strings. It is **not**
> the hosted app's literal source, and its sigma calibration is its own.
> The example KPR values were chosen to recreate stored projections; they
> are not the original user-entered HLTV values.

## Run it

Web UI (needs `pip install -r requirements.txt`):
CLI (no dependencies):
Tests (28, stdlib only):
## Layout

| File | What it is |
|---|---|
| `app.py` | Streamlit web UI; falls back to CLI when Streamlit isn't installed |
| `model.py` | The engine: gates, projection math, per-book evaluation, board driver |
| `constants.py` | Every tunable — change numbers here, the whole pipeline follows |
| `test_model.py` | 28 regression tests (stdlib `unittest`) |
| `examples/` | Afro / Phzy / Fear fixtures as JSON pick inputs |
| `requirements.txt` | `streamlit` (UI only) |

## Pipeline per pick

1. **Input-integrity gate** — cross-player contamination (alias match, or any
   repeated non-stoplist token that isn't the player's own name) → PASS both
   books, no projection/EV/call exposed.
2. **No-fabrication gate** — no player-specific evidence → PASS both books.
3. **Projection** — 30d/90d KPR blend × expected rounds × mismatch multiplier,
   blended with the sharp projection when present. No KPR and no sharp →
   no projection → PASS.
4. **Per-book evaluation** — side → PrizePicks demon check → straddle gate
   (form vs projection on opposite sides, canonical EV strictly under 2%)
   → projection ± sigma range gate → fire with LIGHT / STANDARD / HAMMER
   conviction and the single biggest risk.
5. **Board driver** — one prop per player, correlation warning at 3+
   same-team/same-direction legs.

Result dicts keep the original camelCase keys (`winProb`, `biggestRisk`,
`preferredBook`, …) so they cross-reference 1:1 with the spec.
