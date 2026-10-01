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
    #!/usr/bin/env python3
"""app.py — CS2 Maps 1-2 kills prop model.

Run the web UI:      streamlit run app.py
Or use the CLI:      python app.py examples/afro.json
                     python app.py --board board.json
Run the test suite:  python -m unittest test_model -v

Streamlit is optional: without it, this file runs as a plain CLI.
"""

import json
import math
import sys
from pathlib import Path

from model import evaluate_pick, evaluate_board

HERE = Path(__file__).resolve().parent


def _in_streamlit():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


# ------------------------------------------------------------------ CLI

def _fmt_num(x):
    return '—' if x is None else str(x)


def _print_book(b):
    call = b['call'] if b['call'] is not None else 'PASS'
    head = '{0}: {1} {2}'.format(b['book'], call, _fmt_num(b['line']))
    print('  ' + head)
    if b['call'] is None:
        print('    ' + (b['reason'] or 'PASS.'))
        return
    print('    projection {0} | sigma {1} | winProb {2} | EV {3}% | {4}'.format(
        b['projection'], b['sigma'], b['winProb'], b['ev'], b['conviction']))
    print('    ' + b['reason'])
    print('    biggest risk: ' + b['biggestRisk'])


def _print_pick(r):
    print('{0} — {1}'.format(r['player'], r['verdict']))
    if r['reason']:
        print('  ' + r['reason'])
    if r['projection'] is not None:
        print('  projection {0} | sigma {1} | trailing-3 {2}'.format(
            r['projection'], r['sigma'], _fmt_num(r['trailing3'])))
    if r['preferredBook']:
        print('  preferred book: ' + r['preferredBook'])
    _print_book(r['books']['prizepicks'])
    _print_book(r['books']['underdog'])
    for w in r['warnings']:
        print('  warning: ' + w)


def run_cli(argv):
    args = [a for a in argv if not a.startswith('-')]
    is_board = any(a in ('--board', '-b') for a in argv)
    if not args:
        print('usage: python app.py <pick.json> | python app.py --board <board.json>')
        return 1
    try:
        data = json.loads(Path(args[0]).read_text())
    except (OSError, json.JSONDecodeError) as e:
        print('could not read {0}: {1}'.format(args[0], e))
        return 1

    if is_board:
        picks = data if isinstance(data, list) else data.get('picks', [])
        out = evaluate_board(picks)
        for w in out['warnings']:
            print('BOARD WARNING: ' + w)
        print('fired {0}/{1}'.format(len(out['fired']), len(out['picks'])))
        for r in out['picks']:
            _print_pick(r)
            print()
    else:
        _print_pick(evaluate_pick(data))
    return 0


# ------------------------------------------------------------------ UI

_NUM_FIELDS = [
    'pp_line', 'ud_line', 'kpr_30d', 'kpr_90d', 'expected_rounds',
    'sharp_projection', 'opponent_rank_gap',
]
_BOOL_FIELDS = ['pp_demon_more_only', 'ud_demon_more_only', 'hltv_evidence',
                'last_five_order_known']
_TEXT_FIELDS = ['player', 'team', 'matchup', 'notes', 'last_five_note']


def _num(v):
    if v is None:
        return None
    t = str(v).strip()
    if t == '':
        return None
    try:
        n = float(t)
    except (ValueError, TypeError):
        return None
    return n if math.isfinite(n) else None


def _set_example(name):
    p = HERE / 'examples' / '{0}.json'.format(name)
    if not p.exists():
        return
    data = json.loads(p.read_text())
    for k, v in data.items():
        key = 'f_' + k
        if k == 'last_five' and isinstance(v, list):
            import streamlit as st
            st.session_state[key] = ', '.join(str(x) for x in v)
        elif k == 'other_player_aliases' and isinstance(v, list):
            import streamlit as st
            st.session_state[key] = ', '.join(v)
        elif k in _BOOL_FIELDS:
            import streamlit as st
            st.session_state[key] = bool(v)
        else:
            import streamlit as st
            st.session_state[key] = '' if v is None else str(v)


def _clear_form():
    import streamlit as st
    for k in [k for k in st.session_state.keys() if k.startswith('f_')]:
        del st.session_state[k]


def _collect_pick():
    import streamlit as st
    pick = {}
    for k in _TEXT_FIELDS:
        pick[k] = (st.session_state.get('f_' + k) or '').strip() or None
    for k in _NUM_FIELDS:
        pick[k] = _num(st.session_state.get('f_' + k))
    for k in _BOOL_FIELDS:
        pick[k] = bool(st.session_state.get('f_' + k))
    raw = (st.session_state.get('f_last_five') or '').strip()
    hist = []
    if raw:
        for part in raw.split(','):
            n = _num(part)
            if n is not None:
                hist.append(n)
    pick['last_five'] = hist or None
    raw_a = (st.session_state.get('f_other_player_aliases') or '').strip()
    pick['other_player_aliases'] = (
        [a.strip() for a in raw_a.split(',') if a.strip()] or None
    )
    return pick


def _render_result(st, r):
    st.subheader('{0} — {1}'.format(r['player'], r['verdict']))
    if r['reason']:
        st.info(r['reason'])
    if r['projection'] is not None:
        st.caption('projection {0} · sigma {1} · trailing-3 {2}'.format(
            r['projection'], r['sigma'], _fmt_num(r['trailing3'])))
    for key in ('prizepicks', 'underdog'):
        b = r['books'][key]
        star = ' ★ preferred' if r['preferredBook'] == b['book'] else ''
        with st.container(border=True):
            st.markdown('**{0}**{1}'.format(b['book'], star))
            call = b['call'] if b['call'] is not None else 'PASS'
            st.markdown('## {0} {1}'.format(call, _fmt_num(b['line'])))
            if b['call'] is not None:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric('Projection', b['projection'])
                c2.metric('Win prob', '{0:.1f}%'.format(b['winProb'] * 100))
                c3.metric('EV', '{0:+.1f}%'.format(b['ev']))
                c4.metric('Conviction', b['conviction'])
            st.write(b['reason'] or 'PASS.')
            if b['biggestRisk']:
                st.warning('Biggest risk: ' + b['biggestRisk'])
    for w in r['warnings']:
        st.warning(w)


def run_ui():
    import streamlit as st

    st.set_page_config(page_title='CS2 Prop Model', layout='centered')
    st.title('CS2 Prop Model')
    st.caption('Maps 1–2 kills · PrizePicks vs Underdog · per-book evaluation')
    st.warning(
        'Open reimplementation of the live model spec — '
        'not the hosted app\u2019s literal source.'
    )

    ex = st.columns(4)
    if ex[0].button('Load Afro'):
        _set_example('afro'); st.rerun()
    if ex[1].button('Load Phzy'):
        _set_example('phzy'); st.rerun()
    if ex[2].button('Load Fear'):
        _set_example('fear'); st.rerun()
    if ex[3].button('Clear'):
        _clear_form(); st.rerun()

    with st.form('pick'):
        c1, c2 = st.columns(2)
        c1.text_input('Player', key='f_player')
        c2.text_input('Team', key='f_team')
        c1.text_input('PrizePicks line', key='f_pp_line')
        c2.text_input('Underdog line', key='f_ud_line')
        c1.text_input('KPR 30d', key='f_kpr_30d')
        c2.text_input('KPR 90d', key='f_kpr_90d')
        c1.text_input('Expected rounds', key='f_expected_rounds')
        c2.text_input('Sharp projection', key='f_sharp_projection')
        c1.text_input('Opponent rank gap', key='f_opponent_rank_gap')
        c2.text_input('Matchup', key='f_matchup')
        st.text_input('Last five (oldest → newest, comma separated)',
                      key='f_last_five')
        st.text_input('Other player aliases (comma separated)',
                      key='f_other_player_aliases')
        b1, b2, b3, b4 = st.columns(4)
        b1.checkbox('PP demon', key='f_pp_demon_more_only')
        b2.checkbox('UD demon', key='f_ud_demon_more_only')
        b3.checkbox('HLTV evidence', key='f_hltv_evidence')
        b4.checkbox('Last-5 order known', key='f_last_five_order_known')
        st.text_area('Notes', key='f_notes')
        st.text_area('Last-five note', key='f_last_five_note')
        submitted = st.form_submit_button('Evaluate', type='primary')

    if submitted:
        _render_result(st, evaluate_pick(_collect_pick()))


if __name__ == '__main__':
    if _in_streamlit():
        run_ui()
    else:
        sys.exit(run_cli(sys.argv[1:]))
        