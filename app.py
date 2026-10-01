{
  "name": "esports-picks-model",
  "version": "1.0.0",
  "description": "Standalone open reimplementation of the CS2 Maps 1-2 kills prop model spec: projection, canonical 1:1 EV, straddle rule, input-integrity gates, per-book evaluation. Zero dependencies.",
  "type": "module",
  "engines": { "node": ">=18" },
  "scripts": { "test": "node --test test/model.test.js" },
  "license": "MIT"
}
node_modules/
.DS_Store
// src/constants.js
// EVERY tunable weight / threshold for the CS2 Maps 1-2 kills prop model lives here.
// Nothing in src/model.js hard-codes a magic number — change it here and the whole
// engine (projection, EV, gates, conviction) follows. All values are documented so a
// re-calibration is a one-file edit.

/** Blend of recent vs longer-term kill-rate in the projection. */
export const KPR_30D_WEIGHT = 0.6;
export const KPR_90D_WEIGHT = 0.4;

/** Weight given to the rounds*KPR raw number vs the sharp projection (0.5 = even blend). */
export const SHARP_BLEND_WEIGHT = 0.5;

/**
 * Rank-gap mismatch multiplier. Applied to raw (KPR x rounds) when the player's team
 * is the favorite (team_rank < opponent_rank, lower number = better rank).
 * Heavy favorites frag above their season KPR against much weaker opposition.
 */
export const MISMATCH_GAP_100_MULT = 1.25; // rank gap >= 100
export const MISMATCH_GAP_50_MULT = 1.15;  // rank gap >= 50
export const MISMATCH_GAP_20_MULT = 1.08;  // rank gap >= 20
// gap < 20, underdog, or unknown ranks -> 1.0 (no adjustment)

/**
 * Sigma (one standard deviation of the projection distribution).
 * Population SD of last_five when >= 2 real values exist, never below SIGMA_FLOOR.
 * With < 2 values there is no measurable spread, so SIGMA_DEFAULT is used.
 */
export const SIGMA_FLOOR = 6.0;
export const SIGMA_DEFAULT = 7.0;

/**
 * Straddle gate: projection and trailing-3 average on OPPOSITE sides of the book's
 * line only force a PASS when the canonical edge is STRICTLY under this value.
 * 0.02 = 2% absolute EV.
 */
export const STRADDLE_EV_MAX = 0.02;

/** Conviction ladder, on absolute canonical 1:1 EV (decimal). */
export const EV_HAMMER = 0.06;   // |ev| >= 6%  -> HAMMER
export const EV_STANDARD = 0.02; // |ev| >= 2%  -> STANDARD
// 0 < |ev| < 2% -> LIGHT. |ev| == 0 can never fire (a cleared range implies edge).

/**
 * Tokens ignored by the cross-player contamination heuristic. Common English /
 * betting words that repeat naturally in notes and must not flag a pick.
 */
export const STOPLIST_WORDS = [
  'map', 'maps', 'kills', 'kill', 'team', 'teams', 'vs', 'average', 'avg',
  'projection', 'projected', 'rounds', 'round', 'match', 'matches', 'matchup',
  'event', 'league', 'season', 'stage', 'stages', 'final', 'finals', 'playoff',
  'playoffs', 'series', 'game', 'games',
];
// src/model.js
// Pure CS2 Maps 1-2 kills prop engine. No DOM, no I/O, no network.
// ES modules, zero dependencies. Runs in Node 18+ and in the browser.
//
// Pipeline per pick:
//   1. Input-integrity gate  (cross-player contamination -> PASS both books, nothing exposed)
//   2. No-fabrication gate   (no player-specific evidence -> PASS both books)
//   3. Projection            (KPR x rounds x mismatch, blended with sharp; null -> PASS)
//   4. Per-book evaluation   (PrizePicks and Underdog fully independent):
//        side -> demon check -> straddle gate -> range gate -> fire with conviction
//   5. Board-level warnings  (correlation, duplicate player)

import {
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
} from './constants.js';

// ---------------------------------------------------------------------------
// Small utilities
// ---------------------------------------------------------------------------

/** True for a genuine numeric input. Never true for null/undefined/NaN/Infinity. */
export function isRealNumber(x) {
  return typeof x === 'number' && Number.isFinite(x);
}

/** Real numbers only, from an array that may contain junk. */
export function realNumbers(arr) {
  return (Array.isArray(arr) ? arr : []).filter(isRealNumber);
}

/** Lowercase, strip everything but a-z0-9. Used for name comparison. */
export function normalizeName(s) {
  return String(s ?? '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

export function round1(x) {
  return Math.round(x * 10) / 10;
}

// ---------------------------------------------------------------------------
// Normal distribution (dependency-free, via Abramowitz & Stegun erf 7.1.26)
// ---------------------------------------------------------------------------

export function erf(x) {
  if (x === 0) return 0;
  const sign = x < 0 ? -1 : 1;
  const ax = Math.abs(x);
  const t = 1 / (1 + 0.3275911 * ax);
  const y =
    1 -
    (((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t +
      0.254829592) *
      t *
      Math.exp(-ax * ax));
  return sign * y;
}

/** Standard normal CDF. */
export function normalCDF(z) {
  return 0.5 * (1 + erf(z / Math.SQRT2));
}

// ---------------------------------------------------------------------------
// 1) Input-integrity gate — cross-player contamination detection
// ---------------------------------------------------------------------------

const TOKEN_RE = /\b[A-Za-z][A-Za-z0-9_]{2,15}\b/g;
const STOPLIST = new Set(STOPLIST_WORDS.map((w) => w.toLowerCase()));

/**
 * Returns { integrity_ok: boolean, hit: string|null }.
 * Flags when notes/last_five_note name a different player, either via an explicit
 * alias list (inputs.other_player_aliases) or the repetition heuristic: a
 * mixed-case/alphanumeric token appearing >= 2 times that is neither the input
 * player (fuzzy both directions) nor a stoplist word.
 */
export function checkIntegrity(pick) {
  const player = normalizeName(pick.player);
  const text = `${pick.notes ?? ''} ${pick.last_five_note ?? ''}`;
  const normText = normalizeName(text);

  const aliases = Array.isArray(pick.other_player_aliases) ? pick.other_player_aliases : [];
  for (const a of aliases) {
    const na = normalizeName(a);
    if (na && normText.includes(na)) {
      return { integrity_ok: false, hit: String(a) };
    }
  }

  const counts = new Map();
  for (const m of text.matchAll(TOKEN_RE)) {
    const tok = m[0].toLowerCase();
    counts.set(tok, (counts.get(tok) ?? 0) + 1);
  }
  for (const [tok, n] of counts) {
    if (n < 2) continue;
    if (STOPLIST.has(tok)) continue;
    const nt = normalizeName(tok);
    if (player && (nt.includes(player) || player.includes(nt))) continue;
    return { integrity_ok: false, hit: tok };
  }
  return { integrity_ok: true, hit: null };
}

// ---------------------------------------------------------------------------
// 2) No-fabrication evidence gate
// ---------------------------------------------------------------------------

/**
 * Player-specific evidence exists iff: a real 30-day or 90-day KPR was supplied,
 * OR last_five holds >= 3 real numbers, OR HLTV evidence was pasted (hltv_evidence).
 * Anything else -> PASS. Defaults are never substituted.
 */
export function hasEvidence(pick) {
  return (
    isRealNumber(pick.kpr_30d) ||
    isRealNumber(pick.kpr_90d) ||
    realNumbers(pick.last_five).length >= 3 ||
    pick.hltv_evidence === true
  );
}

// ---------------------------------------------------------------------------
// 3) Projection
// ---------------------------------------------------------------------------

/** Rank-gap mismatch multiplier for the raw KPR x rounds number. */
export function mismatchMultiplier(pick) {
  if (
    isRealNumber(pick.team_rank) &&
    isRealNumber(pick.opponent_rank) &&
    pick.team_rank < pick.opponent_rank
  ) {
    const gap = pick.opponent_rank - pick.team_rank;
    if (gap >= 100) return MISMATCH_GAP_100_MULT;
    if (gap >= 50) return MISMATCH_GAP_50_MULT;
    if (gap >= 20) return MISMATCH_GAP_20_MULT;
  }
  return 1.0;
}

/**
 * Numeric projection, 1 decimal. Null when impossible (missing expected_rounds,
 * or neither KPR present). expected_rounds must be a REAL supplied number — there
 * is no fixed round baseline anywhere in this engine.
 */
export function computeProjection(pick) {
  if (!isRealNumber(pick.expected_rounds)) return null;
  const ha = isRealNumber(pick.kpr_30d);
  const hb = isRealNumber(pick.kpr_90d);
  if (!ha && !hb) return null;
  const blend = ha && hb ? KPR_30D_WEIGHT * pick.kpr_30d + KPR_90D_WEIGHT * pick.kpr_90d : ha ? pick.kpr_30d : pick.kpr_90d;
  const raw = blend * pick.expected_rounds * mismatchMultiplier(pick);
  const proj = isRealNumber(pick.sharp_projection)
    ? SHARP_BLEND_WEIGHT * raw + (1 - SHARP_BLEND_WEIGHT) * pick.sharp_projection
    : raw;
  return round1(proj);
}

// ---------------------------------------------------------------------------
// 4) Sigma and trailing-3
// ---------------------------------------------------------------------------

/** Population SD of last_five, floored at SIGMA_FLOOR; SIGMA_DEFAULT when < 2 values. */
export function computeSigma(pick) {
  const v = realNumbers(pick.last_five);
  if (v.length < 2) return SIGMA_DEFAULT;
  const mean = v.reduce((s, x) => s + x, 0) / v.length;
  const sd = Math.sqrt(v.reduce((s, x) => s + (x - mean) ** 2, 0) / v.length);
  return Math.max(sd, SIGMA_FLOOR);
}

/** Mean of the 3 most recent last_five entries (array is OLDEST -> NEWEST). Null if < 3 values. */
export function trailingThree(pick) {
  const v = realNumbers(pick.last_five);
  if (v.length < 3) return null;
  return v.slice(-3).reduce((s, x) => s + x, 0) / 3;
}

// ---------------------------------------------------------------------------
// 5) Per-book evaluation
// ---------------------------------------------------------------------------

function blockedBook(book, line, reason) {
  return {
    book,
    call: null,
    line: isRealNumber(line) ? line : null,
    side: null,
    projection: null,
    sigma: null,
    winProb: null,
    ev: null,
    conviction: null,
    reason,
    biggestRisk: reason,
  };
}

function pickRisk(pick, proj, sigma, t3, side, conviction) {
  const t3s = t3 == null ? null : round1(t3).toFixed(1);
  if (t3 != null && side === 'LESS' && t3 > proj + 4) {
    return `Heater risk: last-three avg ${t3s} well above projection ${proj}`;
  }
  if (t3 != null && side === 'MORE' && t3 < proj - 4) {
    return `Cold-form risk: last-three avg ${t3s} well below projection ${proj}`;
  }
  if (conviction === 'LIGHT') return 'Thin edge — |EV| under 2%, variance dominates';
  if (mismatchMultiplier(pick) > 1) {
    return `Rank-gap mismatch inflates projection (x${mismatchMultiplier(pick)} multiplier)`;
  }
  return 'Single-match KPR volatility';
}

/**
 * Evaluate one book's line independently.
 * Returns { book, call, line, side, projection, sigma, winProb, ev, conviction, reason, biggestRisk }.
 *   call: 'MORE' | 'LESS' | 'PASS'
 *   winProb: 3 decimals (decimal probability), ev: 1-decimal PERCENT (e.g. 2.9 = +2.9%)
 *   conviction: 'HAMMER' | 'STANDARD' | 'LIGHT' | 'NONE'
 */
export function evaluateBook(pick, proj, sigma, t3, { book, line, demon }) {
  const ctx = {
    book,
    call: 'PASS',
    line: isRealNumber(line) ? line : null,
    side: null,
    projection: proj,
    sigma: Math.round(sigma * 100) / 100,
    winProb: null,
    ev: null,
    conviction: 'NONE',
    reason: '',
    biggestRisk: '',
  };
  if (!isRealNumber(line)) {
    ctx.reason = 'No line posted for this book — PASS.';
    ctx.biggestRisk = 'Missing book line';
    return ctx;
  }

  const side = proj > line ? 'MORE' : proj < line ? 'LESS' : 'NONE';
  ctx.side = side;
  if (side === 'NONE') {
    ctx.reason = 'Projection equals line — PASS.';
    ctx.biggestRisk = 'No edge at the line';
    return ctx;
  }

  // Canonical 1:1 EV from Normal(projection, sigma). Lines are x.5: no pushes.
  const z = (line - proj) / sigma;
  const pWin = side === 'MORE' ? 1 - normalCDF(z) : normalCDF(z);
  const ev = 2 * pWin - 1;
  ctx.winProb = Math.round(pWin * 1000) / 1000;
  ctx.ev = Math.round(ev * 1000) / 10;

  // More-only demon lines are bait: never take the MORE side.
  if (demon === true && side === 'MORE') {
    ctx.reason = 'More-only demon line — bait, wait for the two-sided board.';
    ctx.biggestRisk = 'More-only demon line — no two-sided price';
    return ctx;
  }

  // STRADDLE (key rule): projection and trailing-3 on opposite sides of THIS
  // book's line with a strictly sub-2% edge -> PASS, never a play.
  const opposite =
    t3 != null && ((proj > line && t3 < line) || (proj < line && t3 > line));
  if (opposite && Math.abs(ev) < STRADDLE_EV_MAX) {
    const t3s = round1(t3).toFixed(1);
    ctx.reason =
      `Form/KPR straddle: trailing-3 avg ${t3s} vs projection ${proj} ` +
      `on opposite sides of the ${line} line, edge under 2%.`;
    ctx.biggestRisk =
      `Last-three avg ${t3s} vs projection ${proj} — recent form far ` +
      `${t3 > proj ? 'above' : 'below'} baseline, edge under 2%`;
    return ctx;
  }

  // RANGE: the line sits inside [projection - sigma, projection + sigma]
  // (inclusive) -> thin edge -> PASS. Only fire when the whole band clears.
  const lo = proj - sigma;
  const hi = proj + sigma;
  if (line >= lo && line <= hi) {
    ctx.reason = 'Adjusted range straddles the line — PASS (thin edge).';
    ctx.biggestRisk = 'Thin edge — line sits inside the projected range';
    return ctx;
  }

  const aev = Math.abs(ev);
  const conviction =
    aev >= EV_HAMMER ? 'HAMMER' : aev >= EV_STANDARD ? 'STANDARD' : aev > 0 ? 'LIGHT' : 'NONE';
  if (conviction === 'NONE') {
    ctx.reason = 'No edge — PASS.';
    ctx.biggestRisk = 'No measurable edge';
    return ctx;
  }

  ctx.call = side;
  ctx.conviction = conviction;
  ctx.reason = `Projection ${proj} clears the ${line} line — ${conviction} ${side} (${ctx.ev}% EV).`;
  ctx.biggestRisk = pickRisk(pick, proj, sigma, t3, side, conviction);
  return ctx;
}

// ---------------------------------------------------------------------------
// Full pick evaluation
// ---------------------------------------------------------------------------

/**
 * evaluate_pick(pick) -> {
 *   player, team, opponent, matchup, event,
 *   integrity_ok, evidence_ok, projection, sigma, trailing3,
 *   verdict: 'PASS' | 'MORE' | 'LESS' | 'SPLIT',
 *   books: { prizepicks, underdog },
 *   preferredBook: 'PrizePicks' | 'Underdog' | null
 * }
 * Gates run in order: integrity -> evidence -> projection -> per-book.
 * A failed gate returns PASS on BOTH books and exposes no analysis.
 */
export function evaluate_pick(pick) {
  const result = {
    player: pick.player ?? null,
    team: pick.team ?? null,
    opponent: pick.opponent ?? null,
    matchup: pick.matchup ?? null,
    event: pick.event ?? null,
    integrity_ok: true,
    evidence_ok: null,
    projection: null,
    sigma: null,
    trailing3: null,
    verdict: 'PASS',
    books: null,
    preferredBook: null,
  };

  const integ = checkIntegrity(pick);
  result.integrity_ok = integ.integrity_ok;
  if (!integ.integrity_ok) {
    const r = 'Cross-player contamination — PASS per input-integrity rule.';
    result.books = {
      prizepicks: blockedBook('PrizePicks', pick.pp_line, r),
      underdog: blockedBook('Underdog', pick.ud_line, r),
    };
    return result;
  }

  const evd = hasEvidence(pick);
  result.evidence_ok = evd;
  if (!evd) {
    const r = 'No player-specific evidence — PASS per no-fabrication rule.';
    result.books = {
      prizepicks: blockedBook('PrizePicks', pick.pp_line, r),
      underdog: blockedBook('Underdog', pick.ud_line, r),
    };
    return result;
  }

  const proj = computeProjection(pick);
  if (proj == null) {
    const r = 'No supported projection — PASS.';
    result.books = {
      prizepicks: blockedBook('PrizePicks', pick.pp_line, r),
      underdog: blockedBook('Underdog', pick.ud_line, r),
    };
    return result;
  }

  const sigma = computeSigma(pick);
  const t3 = trailingThree(pick);
  result.projection = proj;
  result.sigma = Math.round(sigma * 100) / 100;
  result.trailing3 = t3 == null ? null : round1(t3);

  const pp = evaluateBook(pick, proj, sigma, t3, {
    book: 'PrizePicks',
    line: pick.pp_line,
    demon: pick.pp_demon_more_only === true,
  });
  const ud = evaluateBook(pick, proj, sigma, t3, {
    book: 'Underdog',
    line: pick.ud_line,
    demon: pick.ud_demon_more_only === true,
  });
  result.books = { prizepicks: pp, underdog: ud };

  const fired = [pp, ud].filter((b) => b.call === 'MORE' || b.call === 'LESS');
  result.verdict =
    fired.length === 0 ? 'PASS' : fired.every((b) => b.call === fired[0].call) ? fired[0].call : 'SPLIT';
  if (fired.length > 0) {
    result.preferredBook = fired.reduce((m, b) => ((b.ev ?? -Infinity) > (m.ev ?? -Infinity) ? b : m)).book;
  }
  return result;
}

// ---------------------------------------------------------------------------
// Board evaluation
// ---------------------------------------------------------------------------

/**
 * evaluate_board(picks) -> { results, warnings[] }.
 * Warnings: 3+ same-team same-direction fired plays (correlation), duplicate player.
 */
export function evaluate_board(picks) {
  const list = Array.isArray(picks) ? picks : [];
  const results = list.map(evaluate_pick);
  const warnings = [];

  const seen = new Set();
  for (const r of results) {
    const n = normalizeName(r.player);
    if (!n) continue;
    if (seen.has(n)) warnings.push(`Duplicate player: ${r.player} — one prop per player.`);
    else seen.add(n);
  }

  const groups = new Map();
  for (const r of results) {
    const team = normalizeName(r.team);
    if (!team) continue;
    for (const key of ['prizepicks', 'underdog']) {
      const b = r.books[key];
      if (b.call !== 'MORE' && b.call !== 'LESS') continue;
      const gk = `${team}|${b.call}`;
      if (!groups.has(gk)) groups.set(gk, []);
      groups.get(gk).push(`${r.player} (${b.book} ${b.call} ${b.line})`);
    }
  }
  for (const [gk, legs] of groups) {
    if (legs.length >= 3) {
      const dir = gk.split('|')[1];
      warnings.push(`Correlation: 3+ same-team same-direction plays (${dir}): ${legs.join(', ')}`);
    }
  }

  return { results, warnings };
}
#!/usr/bin/env node
// cli.js — evaluate one pick or a whole board from JSON files.
//   node cli.js <pick.json>
//   node cli.js --board <board.json>     (board.json = array of picks)
// No dependencies. Node 18+.
import { readFile } from 'node:fs/promises';
import { evaluate_pick, evaluate_board } from './src/model.js';

function fmtEv(ev) {
  if (ev == null) return '—';
  return `${ev > 0 ? '+' : ''}${ev}%`;
}

function printBook(b) {
  const call = b.call ?? 'PASS';
  const head = b.call == null ? 'PASS (blocked)' : `${call}`;
  console.log(`  [${b.book}] ${head} — line ${b.line ?? '—'}`);
  if (b.side) console.log(`    side: ${b.side} | projection: ${b.projection} | sigma: ${b.sigma}`);
  if (b.winProb != null) console.log(`    win prob: ${b.winProb} | EV: ${fmtEv(b.ev)}`);
  if (b.conviction && b.conviction !== 'NONE') console.log(`    conviction: ${b.conviction}`);
  console.log(`    reason: ${b.reason}`);
  if (b.biggestRisk && b.biggestRisk !== b.reason) console.log(`    biggest risk: ${b.biggestRisk}`);
}

function printPick(r) {
  const title = [r.player, r.team && r.opponent ? `(${r.team} vs ${r.opponent})` : null]
    .filter(Boolean)
    .join(' ');
  console.log(`\n${title} — verdict: ${r.verdict}`);
  console.log(
    `  projection: ${r.projection ?? '—'} | sigma: ${r.sigma ?? '—'} | trailing-3: ${r.trailing3 ?? '—'} | integrity: ${r.integrity_ok ? 'OK' : 'FAILED'} | evidence: ${r.evidence_ok === null ? '—' : r.evidence_ok ? 'OK' : 'MISSING'}`
  );
  printBook(r.books.prizepicks);
  printBook(r.books.underdog);
  console.log(`  preferred book: ${r.preferredBook ?? '—'}`);
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args.includes('-h') || args.includes('--help')) {
    console.log('Usage:');
    console.log('  node cli.js <pick.json>');
    console.log('  node cli.js --board <board.json>');
    process.exit(args.length === 0 ? 1 : 0);
  }
  if (args[0] === '--board') {
    const file = args[1];
    if (!file) throw new Error('Missing board file after --board');
    const picks = JSON.parse(await readFile(file, 'utf8'));
    const { results, warnings } = evaluate_board(picks);
    for (const r of results) printPick(r);
    if (warnings.length) {
      console.log('\nWARNINGS:');
      for (const w of warnings) console.log(`  ! ${w}`);
    } else {
      console.log('\nNo board warnings.');
    }
    return;
  }
  const pick = JSON.parse(await readFile(args[0], 'utf8'));
  printPick(evaluate_pick(pick));
}

main().catch((e) => {
  console.error(`Error: ${e.message}`);
  process.exit(1);
});
// test/model.test.js — node:test suite for the CS2 prop engine.
// Run: node --test test/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import {
  evaluate_pick,
  evaluate_board,
  computeProjection,
  computeSigma,
  trailingThree,
  checkIntegrity,
  hasEvidence,
  normalCDF,
  evaluateBook,
} from '../src/model.js';

const here = path.dirname(fileURLToPath(import.meta.url));
async function example(name) {
  return JSON.parse(await readFile(path.join(here, '..', 'examples', name), 'utf8'));
}

const approx = (a, b, tol = 0.011) => Math.abs(a - b) < tol;

// --- math sanity -----------------------------------------------------------

test('normalCDF is sane', () => {
  assert.equal(normalCDF(0), 0.5);
  assert.ok(normalCDF(3) > 0.998 && normalCDF(3) < 1);
  assert.ok(normalCDF(-3) > 0 && normalCDF(-3) < 0.002);
});

// --- afro: historical straddle case -----------------------------------------

test('afro.json: projection 30.5, trailing-3 39.7, PASS both books', async () => {
  const r = evaluate_pick(await example('afro.json'));
  assert.equal(r.integrity_ok, true);
  assert.equal(r.evidence_ok, true);
  assert.equal(r.projection, 30.5);
  assert.ok(approx(r.trailing3, 39.7));
  assert.ok(approx(r.sigma, 13.91, 0.02));
  assert.equal(r.verdict, 'PASS');
  assert.equal(r.books.prizepicks.call, 'PASS');
  assert.equal(r.books.underdog.call, 'PASS');
  // Spec-math note: with sigma=13.9 the canonical edges are 2.9% (PP) and 5.7%
  // (UD), so the strict sub-2% straddle gate does not trigger; both books PASS
  // via the adjusted-range gate instead. The historical +0.8% EV came from the
  // live app's different sigma calibration.
  assert.match(r.books.prizepicks.reason, /Adjusted range straddles/);
  assert.match(r.books.underdog.reason, /Adjusted range straddles/);
  // Opposite-sides structure of the straddle is still present:
  assert.ok(r.trailing3 > 31.5 && r.projection < 31.0);
  assert.equal(r.preferredBook, null);
});

// --- phzy: per-book independence --------------------------------------------

test('phzy.json: projection 30.1, each book judged on its own line', async () => {
  const r = evaluate_pick(await example('phzy.json'));
  assert.equal(r.projection, 30.1);
  assert.ok(approx(r.trailing3, 29.3));
  // PP 29.5: projection above, trailing-3 below -> opposite sides, but the
  // canonical edge (3.9%) is not strictly under 2%, so no straddle; range PASS.
  assert.equal(r.books.prizepicks.side, 'MORE');
  assert.equal(r.books.prizepicks.call, 'PASS');
  // UD 30.5: both projection and trailing-3 below the line -> evaluated alone.
  assert.equal(r.books.underdog.side, 'LESS');
  assert.equal(r.books.underdog.call, 'PASS');
  assert.equal(r.verdict, 'PASS');
  assert.equal(r.preferredBook, null);
});

// --- fear: contamination -----------------------------------------------------

test('fear.json: cross-player contamination -> PASS both, nothing exposed', async () => {
  const r = evaluate_pick(await example('fear.json'));
  assert.equal(r.integrity_ok, false);
  assert.equal(r.verdict, 'PASS');
  for (const key of ['prizepicks', 'underdog']) {
    const b = r.books[key];
    assert.equal(b.call, null);
    assert.equal(b.conviction, null);
    assert.equal(b.ev, null);
    assert.equal(b.winProb, null);
    assert.equal(b.projection, null);
    assert.equal(
      b.reason,
      'Cross-player contamination — PASS per input-integrity rule.'
    );
  }
  assert.equal(r.preferredBook, null);
});

test('integrity heuristic flags a repeated foreign token without an alias list', () => {
  const { integrity_ok } = checkIntegrity({
    player: 'Fear',
    notes: 'zed zed on fire tonight',
    last_five_note: '',
  });
  assert.equal(integrity_ok, false);
});

test('integrity does not flag the player himself or stoplist words', () => {
  const { integrity_ok } = checkIntegrity({
    player: 'afro',
    notes: 'afro afro maps 1-2 kills projection rounds',
    last_five_note: '',
  });
  assert.equal(integrity_ok, true);
});

// --- no-fabrication gate -------------------------------------------------------

test('no player-specific evidence -> PASS both with no-fabrication reason', () => {
  const r = evaluate_pick({
    player: 'Ghost',
    team: 'TBD',
    notes: 'player struggling lately',
    last_five: [12],
    hltv_evidence: false,
    pp_line: 25.5,
    ud_line: 25.5,
  });
  assert.equal(r.evidence_ok, false);
  assert.equal(r.verdict, 'PASS');
  for (const key of ['prizepicks', 'underdog']) {
    const b = r.books[key];
    assert.equal(b.call, null);
    assert.equal(b.ev, null);
    assert.equal(b.reason, 'No player-specific evidence — PASS per no-fabrication rule.');
  }
});

test('never invent: notes-only pick with zero numbers -> PASS both', () => {
  const r = evaluate_pick({
    player: 'GhostTwo',
    notes: 'some scouting chatter here',
    pp_line: 24.5,
    ud_line: 24.5,
  });
  assert.equal(r.verdict, 'PASS');
  assert.equal(
    r.books.prizepicks.reason,
    'No player-specific evidence — PASS per no-fabrication rule.'
  );
});

test('hasEvidence: kpr alone, last_five>=3 alone, or hltv flag alone all count', () => {
  assert.equal(hasEvidence({ kpr_30d: 0.7 }), true);
  assert.equal(hasEvidence({ last_five: [1, 2, 3] }), true);
  assert.equal(hasEvidence({ hltv_evidence: true }), true);
  assert.equal(hasEvidence({ last_five: [1, 2], notes: 'x' }), false);
});

// --- projection --------------------------------------------------------------

test('no expected_rounds and no fixed baseline -> null projection -> PASS', () => {
  const r = evaluate_pick({
    player: 'NoRounds',
    kpr_30d: 0.8,
    notes: 'rounds unknown',
    pp_line: 29.5,
    ud_line: 29.5,
  });
  assert.equal(r.projection, null);
  assert.equal(r.books.prizepicks.reason, 'No supported projection — PASS.');
});

test('projection blends 30d/90d KPR x rounds', () => {
  // 0.6*0.72 + 0.4*0.695 = 0.71 KPR x 43 rounds = 30.53 -> 30.5 (1 decimal)
  assert.equal(
    computeProjection({ kpr_30d: 0.72, kpr_90d: 0.695, expected_rounds: 43 }),
    30.5
  );
});

test('single KPR is used alone when the other is missing', () => {
  assert.equal(computeProjection({ kpr_30d: 0.8, expected_rounds: 40 }), 32.0);
});

test('sharp projection blends 50/50 with raw', () => {
  // raw 30.53, sharp 34 -> 32.265 -> 32.3 (1 decimal)
  const p = computeProjection({
    kpr_30d: 0.72,
    kpr_90d: 0.695,
    expected_rounds: 43,
    sharp_projection: 34,
  });
  assert.equal(p, 32.3);
});

test('rank-gap mismatch multiplier inflates favorites', () => {
  const fav = computeProjection({
    kpr_30d: 0.8,
    expected_rounds: 40,
    team_rank: 5,
    opponent_rank: 120,
  });
  assert.equal(fav, 40.0); // 32 x 1.25
  const dog = computeProjection({
    kpr_30d: 0.8,
    expected_rounds: 40,
    team_rank: 120,
    opponent_rank: 5,
  });
  assert.equal(dog, 32.0); // underdog: no multiplier
});

// --- sigma / trailing-3 -------------------------------------------------------

test('sigma is floored at 6.0 and defaults to 7.0', () => {
  assert.equal(computeSigma({ last_five: [36, 37, 38, 37, 38] }), 6.0);
  assert.equal(computeSigma({ last_five: [10] }), 7.0);
  assert.equal(computeSigma({}), 7.0);
});

test('trailing-3 is the mean of the 3 most recent entries', () => {
  assert.ok(approx(trailingThree({ last_five: [9, 17, 37, 35, 47] }), 39.67));
  assert.equal(trailingThree({ last_five: [1, 2] }), null);
});

// --- straddle gate (synthetic, genuinely triggers) -----------------------------

test('straddle: opposite sides + sub-2% edge -> PASS with exact reason', () => {
  const r = evaluate_pick({
    player: 'StraddleTest',
    expected_rounds: 43,
    kpr_30d: 0.707,
    kpr_90d: 0.707,
    last_five: [20, 22, 31, 32, 33],
    notes: 'straddle test notes',
    pp_line: 30.5,
    ud_line: 30.5,
  });
  assert.equal(r.projection, 30.4);
  const b = r.books.prizepicks;
  assert.equal(b.call, 'PASS');
  assert.equal(
    b.reason,
    'Form/KPR straddle: trailing-3 avg 32.0 vs projection 30.4 on opposite sides of the 30.5 line, edge under 2%.'
  );
});

// --- demon --------------------------------------------------------------------

test('more-only demon with MORE side -> PASS; other book independent', () => {
  const r = evaluate_pick({
    player: 'DemonPick',
    expected_rounds: 43,
    kpr_30d: 0.75,
    kpr_90d: 0.75,
    last_five: [31, 32, 33, 32, 33],
    notes: 'demon test legs',
    pp_line: 29.5,
    pp_demon_more_only: true,
    ud_line: 25.5,
  });
  assert.equal(r.books.prizepicks.call, 'PASS');
  assert.match(r.books.prizepicks.reason, /More-only demon line/);
  assert.equal(r.books.underdog.call, 'MORE');
  assert.equal(r.books.underdog.conviction, 'HAMMER');
  assert.equal(r.preferredBook, 'Underdog');
});

// --- hammer --------------------------------------------------------------------

test('clear range -> HAMMER MORE with positive EV', () => {
  const r = evaluate_pick({
    player: 'HammerTest',
    expected_rounds: 43,
    kpr_30d: 0.9,
    kpr_90d: 0.86,
    last_five: [36, 37, 38, 37, 38],
    notes: 'clean hammer test',
    pp_line: 29.5,
    ud_line: 29.5,
  });
  assert.equal(r.projection, 38.0);
  for (const key of ['prizepicks', 'underdog']) {
    const b = r.books[key];
    assert.equal(b.call, 'MORE');
    assert.equal(b.conviction, 'HAMMER');
    assert.ok(b.ev > 0);
    assert.ok(b.winProb > 0.5 && b.winProb < 1);
  }
  assert.equal(r.verdict, 'MORE');
});

// --- projection equals line ------------------------------------------------------

test('projection equals line -> PASS', () => {
  const r = evaluate_pick({
    player: 'EqualTest',
    expected_rounds: 43,
    kpr_30d: 0.72,
    kpr_90d: 0.695,
    last_five: [28, 30, 32, 31, 33],
    notes: 'equal line test',
    pp_line: 30.5,
    ud_line: 31.5,
  });
  assert.equal(r.projection, 30.5);
  assert.equal(r.books.prizepicks.call, 'PASS');
  assert.equal(r.books.prizepicks.reason, 'Projection equals line — PASS.');
});

// --- board -----------------------------------------------------------------------

function corrPick(player, note) {
  return {
    player,
    team: 'Astralis',
    opponent: 'Alliance',
    expected_rounds: 43,
    kpr_30d: 0.814,
    kpr_90d: 0.814,
    last_five: [33, 34, 35, 34, 35],
    notes: note,
    pp_line: 28.5,
    ud_line: 28.5,
  };
}

test('board warns on 3+ same-team same-direction plays', () => {
  const { results, warnings } = evaluate_board([
    corrPick('Alpha', 'alpha first entry'),
    corrPick('Bravo', 'bravo second entry'),
    corrPick('Charlie', 'charlie third entry'),
  ]);
  assert.ok(results.every((r) => r.books.prizepicks.call === 'MORE'));
  assert.ok(warnings.some((w) => w.startsWith('Correlation: 3+ same-team same-direction plays')));
});

test('board warns on duplicate player', () => {
  const base = {
    team: 'Astralis',
    expected_rounds: 43,
    kpr_30d: 0.7,
    last_five: [20, 25, 30, 35, 40],
    pp_line: 29.5,
    ud_line: 30.5,
  };
  const { warnings } = evaluate_board([
    { ...base, player: 'Dup', notes: 'dup first' },
    { ...base, player: 'Dup', notes: 'dup second' },
  ]);
  assert.ok(warnings.some((w) => w.startsWith('Duplicate player: Dup')));
});

test('never turn a PASS into a play: all-PASS board has no preferred book', async () => {
  const { results } = evaluate_board([await example('afro.json'), await example('phzy.json')]);
  assert.ok(results.every((r) => r.verdict === 'PASS'));
  assert.ok(results.every((r) => r.preferredBook === null));
});
// test/model.test.js — node:test suite for the CS2 prop engine.
// Run: node --test test/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import {
  evaluate_pick,
  evaluate_board,
  computeProjection,
  computeSigma,
  trailingThree,
  checkIntegrity,
  hasEvidence,
  normalCDF,
  evaluateBook,
} from '../src/model.js';

const here = path.dirname(fileURLToPath(import.meta.url));
async function example(name) {
  return JSON.parse(await readFile(path.join(here, '..', 'examples', name), 'utf8'));
}

const approx = (a, b, tol = 0.011) => Math.abs(a - b) < tol;

// --- math sanity -----------------------------------------------------------

test('normalCDF is sane', () => {
  assert.equal(normalCDF(0), 0.5);
  assert.ok(normalCDF(3) > 0.998 && normalCDF(3) < 1);
  assert.ok(normalCDF(-3) > 0 && normalCDF(-3) < 0.002);
});

// --- afro: historical straddle case -----------------------------------------

test('afro.json: projection 30.5, trailing-3 39.7, PASS both books', async () => {
  const r = evaluate_pick(await example('afro.json'));
  assert.equal(r.integrity_ok, true);
  assert.equal(r.evidence_ok, true);
  assert.equal(r.projection, 30.5);
  assert.ok(approx(r.trailing3, 39.7));
  assert.ok(approx(r.sigma, 13.91, 0.02));
  assert.equal(r.verdict, 'PASS');
  assert.equal(r.books.prizepicks.call, 'PASS');
  assert.equal(r.books.underdog.call, 'PASS');
  // Spec-math note: with sigma=13.9 the canonical edges are 2.9% (PP) and 5.7%
  // (UD), so the strict sub-2% straddle gate does not trigger; both books PASS
  // via the adjusted-range gate instead. The historical +0.8% EV came from the
  // live app's different sigma calibration.
  assert.match(r.books.prizepicks.reason, /Adjusted range straddles/);
  assert.match(r.books.underdog.reason, /Adjusted range straddles/);
  // Opposite-sides structure of the straddle is still present:
  assert.ok(r.trailing3 > 31.5 && r.projection < 31.0);
  assert.equal(r.preferredBook, null);
});

// --- phzy: per-book independence --------------------------------------------

test('phzy.json: projection 30.1, each book judged on its own line', async () => {
  const r = evaluate_pick(await example('phzy.json'));
  assert.equal(r.projection, 30.1);
  assert.ok(approx(r.trailing3, 29.3));
  // PP 29.5: projection above, trailing-3 below -> opposite sides, but the
  // canonical edge (3.9%) is not strictly under 2%, so no straddle; range PASS.
  assert.equal(r.books.prizepicks.side, 'MORE');
  assert.equal(r.books.prizepicks.call, 'PASS');
  // UD 30.5: both projection and trailing-3 below the line -> evaluated alone.
  assert.equal(r.books.underdog.side, 'LESS');
  assert.equal(r.books.underdog.call, 'PASS');
  assert.equal(r.verdict, 'PASS');
  assert.equal(r.preferredBook, null);
});

// --- fear: contamination -----------------------------------------------------

test('fear.json: cross-player contamination -> PASS both, nothing exposed', async () => {
  const r = evaluate_pick(await example('fear.json'));
  assert.equal(r.integrity_ok, false);
  assert.equal(r.verdict, 'PASS');
  for (const key of ['prizepicks', 'underdog']) {
    const b = r.books[key];
    assert.equal(b.call, null);
    assert.equal(b.conviction, null);
    assert.equal(b.ev, null);
    assert.equal(b.winProb, null);
    assert.equal(b.projection, null);
    assert.equal(
      b.reason,
      'Cross-player contamination — PASS per input-integrity rule.'
    );
  }
  assert.equal(r.preferredBook, null);
});

test('integrity heuristic flags a repeated foreign token without an alias list', () => {
  const { integrity_ok } = checkIntegrity({
    player: 'Fear',
    notes: 'zed zed on fire tonight',
    last_five_note: '',
  });
  assert.equal(integrity_ok, false);
});

test('integrity does not flag the player himself or stoplist words', () => {
  const { integrity_ok } = checkIntegrity({
    player: 'afro',
    notes: 'afro afro maps 1-2 kills projection rounds',
    last_five_note: '',
  });
  assert.equal(integrity_ok, true);
});

// --- no-fabrication gate -------------------------------------------------------

test('no player-specific evidence -> PASS both with no-fabrication reason', () => {
  const r = evaluate_pick({
    player: 'Ghost',
    team: 'TBD',
    notes: 'player struggling lately',
    last_five: [12],
    hltv_evidence: false,
    pp_line: 25.5,
    ud_line: 25.5,
  });
  assert.equal(r.evidence_ok, false);
  assert.equal(r.verdict, 'PASS');
  for (const key of ['prizepicks', 'underdog']) {
    const b = r.books[key];
    assert.equal(b.call, null);
    assert.equal(b.ev, null);
    assert.equal(b.reason, 'No player-specific evidence — PASS per no-fabrication rule.');
  }
});

test('never invent: notes-only pick with zero numbers -> PASS both', () => {
  const r = evaluate_pick({
    player: 'GhostTwo',
    notes: 'some scouting chatter here',
    pp_line: 24.5,
    ud_line: 24.5,
  });
  assert.equal(r.verdict, 'PASS');
  assert.equal(
    r.books.prizepicks.reason,
    'No player-specific evidence — PASS per no-fabrication rule.'
  );
});

test('hasEvidence: kpr alone, last_five>=3 alone, or hltv flag alone all count', () => {
  assert.equal(hasEvidence({ kpr_30d: 0.7 }), true);
  assert.equal(hasEvidence({ last_five: [1, 2, 3] }), true);
  assert.equal(hasEvidence({ hltv_evidence: true }), true);
  assert.equal(hasEvidence({ last_five: [1, 2], notes: 'x' }), false);
});

// --- projection --------------------------------------------------------------

test('no expected_rounds and no fixed baseline -> null projection -> PASS', () => {
  const r = evaluate_pick({
    player: 'NoRounds',
    kpr_30d: 0.8,
    notes: 'rounds unknown',
    pp_line: 29.5,
    ud_line: 29.5,
  });
  assert.equal(r.projection, null);
  assert.equal(r.books.prizepicks.reason, 'No supported projection — PASS.');
});

test('projection blends 30d/90d KPR x rounds', () => {
  // 0.6*0.72 + 0.4*0.695 = 0.71 KPR x 43 rounds = 30.53 -> 30.5 (1 decimal)
  assert.equal(
    computeProjection({ kpr_30d: 0.72, kpr_90d: 0.695, expected_rounds: 43 }),
    30.5
  );
});

test('single KPR is used alone when the other is missing', () => {
  assert.equal(computeProjection({ kpr_30d: 0.8, expected_rounds: 40 }), 32.0);
});

test('sharp projection blends 50/50 with raw', () => {
  // raw 30.53, sharp 34 -> 32.265 -> 32.3 (1 decimal)
  const p = computeProjection({
    kpr_30d: 0.72,
    kpr_90d: 0.695,
    expected_rounds: 43,
    sharp_projection: 34,
  });
  assert.equal(p, 32.3);
});

test('rank-gap mismatch multiplier inflates favorites', () => {
  const fav = computeProjection({
    kpr_30d: 0.8,
    expected_rounds: 40,
    team_rank: 5,
    opponent_rank: 120,
  });
  assert.equal(fav, 40.0); // 32 x 1.25
  const dog = computeProjection({
    kpr_30d: 0.8,
    expected_rounds: 40,
    team_rank: 120,
    opponent_rank: 5,
  });
  assert.equal(dog, 32.0); // underdog: no multiplier
});

// --- sigma / trailing-3 -------------------------------------------------------

test('sigma is floored at 6.0 and defaults to 7.0', () => {
  assert.equal(computeSigma({ last_five: [36, 37, 38, 37, 38] }), 6.0);
  assert.equal(computeSigma({ last_five: [10] }), 7.0);
  assert.equal(computeSigma({}), 7.0);
});

test('trailing-3 is the mean of the 3 most recent entries', () => {
  assert.ok(approx(trailingThree({ last_five: [9, 17, 37, 35, 47] }), 39.67));
  assert.equal(trailingThree({ last_five: [1, 2] }), null);
});

// --- straddle gate (synthetic, genuinely triggers) -----------------------------

test('straddle: opposite sides + sub-2% edge -> PASS with exact reason', () => {
  const r = evaluate_pick({
    player: 'StraddleTest',
    expected_rounds: 43,
    kpr_30d: 0.707,
    kpr_90d: 0.707,
    last_five: [20, 22, 31, 32, 33],
    notes: 'straddle test notes',
    pp_line: 30.5,
    ud_line: 30.5,
  });
  assert.equal(r.projection, 30.4);
  const b = r.books.prizepicks;
  assert.equal(b.call, 'PASS');
  assert.equal(
    b.reason,
    'Form/KPR straddle: trailing-3 avg 32.0 vs projection 30.4 on opposite sides of the 30.5 line, edge under 2%.'
  );
});

// --- demon --------------------------------------------------------------------

test('more-only demon with MORE side -> PASS; other book independent', () => {
  const r = evaluate_pick({
    player: 'DemonPick',
    expected_rounds: 43,
    kpr_30d: 0.75,
    kpr_90d: 0.75,
    last_five: [31, 32, 33, 32, 33],
    notes: 'demon test legs',
    pp_line: 29.5,
    pp_demon_more_only: true,
    ud_line: 25.5,
  });
  assert.equal(r.books.prizepicks.call, 'PASS');
  assert.match(r.books.prizepicks.reason, /More-only demon line/);
  assert.equal(r.books.underdog.call, 'MORE');
  assert.equal(r.books.underdog.conviction, 'HAMMER');
  assert.equal(r.preferredBook, 'Underdog');
});

// --- hammer --------------------------------------------------------------------

test('clear range -> HAMMER MORE with positive EV', () => {
  const r = evaluate_pick({
    player: 'HammerTest',
    expected_rounds: 43,
    kpr_30d: 0.9,
    kpr_90d: 0.86,
    last_five: [36, 37, 38, 37, 38],
    notes: 'clean hammer test',
    pp_line: 29.5,
    ud_line: 29.5,
  });
  assert.equal(r.projection, 38.0);
  for (const key of ['prizepicks', 'underdog']) {
    const b = r.books[key];
    assert.equal(b.call, 'MORE');
    assert.equal(b.conviction, 'HAMMER');
    assert.ok(b.ev > 0);
    assert.ok(b.winProb > 0.5 && b.winProb < 1);
  }
  assert.equal(r.verdict, 'MORE');
});

// --- projection equals line ------------------------------------------------------

test('projection equals line -> PASS', () => {
  const r = evaluate_pick({
    player: 'EqualTest',
    expected_rounds: 43,
    kpr_30d: 0.72,
    kpr_90d: 0.695,
    last_five: [28, 30, 32, 31, 33],
    notes: 'equal line test',
    pp_line: 30.5,
    ud_line: 31.5,
  });
  assert.equal(r.projection, 30.5);
  assert.equal(r.books.prizepicks.call, 'PASS');
  assert.equal(r.books.prizepicks.reason, 'Projection equals line — PASS.');
});

// --- board -----------------------------------------------------------------------

function corrPick(player, note) {
  return {
    player,
    team: 'Astralis',
    opponent: 'Alliance',
    expected_rounds: 43,
    kpr_30d: 0.814,
    kpr_90d: 0.814,
    last_five: [33, 34, 35, 34, 35],
    notes: note,
    pp_line: 28.5,
    ud_line: 28.5,
  };
}

test('board warns on 3+ same-team same-direction plays', () => {
  const { results, warnings } = evaluate_board([
    corrPick('Alpha', 'alpha first entry'),
    corrPick('Bravo', 'bravo second entry'),
    corrPick('Charlie', 'charlie third entry'),
  ]);
  assert.ok(results.every((r) => r.books.prizepicks.call === 'MORE'));
  assert.ok(warnings.some((w) => w.startsWith('Correlation: 3+ same-team same-direction plays')));
});

test('board warns on duplicate player', () => {
  const base = {
    team: 'Astralis',
    expected_rounds: 43,
    kpr_30d: 0.7,
    last_five: [20, 25, 30, 35, 40],
    pp_line: 29.5,
    ud_line: 30.5,
  };
  const { warnings } = evaluate_board([
    { ...base, player: 'Dup', notes: 'dup first' },
    { ...base, player: 'Dup', notes: 'dup second' },
  ]);
  assert.ok(warnings.some((w) => w.startsWith('Duplicate player: Dup')));
});

test('never turn a PASS into a play: all-PASS board has no preferred book', async () => {
  const { results } = evaluate_board([await example('afro.json'), await example('phzy.json')]);
  assert.ok(results.every((r) => r.verdict === 'PASS'));
  assert.ok(results.every((r) => r.preferredBook === null));
});
{"event":"European Pro League Series 9","expected_rounds":43,"hltv_evidence":true,"kpr_30d":0.72,"kpr_90d":0.695,"last_five":[9,17,37,35,47],"last_five_note":"last five maps 1-2 kills","matchup":"B8 vs Luminosity","notes":"Luminosity map veto pending","opponent":"B8","player":"afro","pp_line":31.0,"team":"Luminosity","ud_line":31.5}
{"expected_rounds":43,"hltv_evidence":true,"kpr_30d":0.7,"kpr_90d":0.7,"last_five":[21,37,9,36,43],"last_five_note":"five most recent maps 1-2 totals","matchup":"Astralis vs Alliance","notes":"Astralis veto watch","opponent":"Alliance","player":"Phzy","pp_line":29.5,"team":"Astralis","ud_line":30.5}
{"expected_rounds":43,"hltv_evidence":false,"kpr_30d":0.7,"kpr_90d":0.7,"last_five":[21,37,9,36,43],"last_five_note":"copied five-game sample","matchup":"BIG vs fnatic","notes":"phzy phzy Astralis vs Alliance numbers on this card","opponent":"BIG","other_player_aliases":["phzy","Astralis"],"player":"Fear","pp_line":23.5,"team":"fnatic","ud_line":22.5}
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CS2 Prop Model — Maps 1-2 Kills</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header>
  <h1>CS2 Prop Model</h1>
  <p class="sub">Maps 1–2 kills · PrizePicks vs Underdog · per-book evaluation</p>
  <p class="honesty">Open reimplementation of the live model spec — not the hosted app's literal source.
  Serve this folder over HTTP (e.g. <code>python3 -m http.server</code>) or deploy to GitHub Pages.</p>
</header>

<main>
  <section class="card form-card">
    <h2>Pick inputs</h2>
    <div class="examples">
      <span>Load example:</span>
      <button type="button" data-example="afro">afro</button>
      <button type="button" data-example="phzy">phzy</button>
      <button type="button" data-example="fear">fear</button>
      <button type="button" id="clearBtn" class="ghost">clear</button>
    </div>
    <form id="pickForm">
      <div class="grid">
        <label>Player <input name="player" autocomplete="off"></label>
        <label>Team <input name="team" autocomplete="off"></label>
        <label>Opponent <input name="opponent" autocomplete="off"></label>
        <label>Matchup <input name="matchup" autocomplete="off" placeholder="Team A vs Team B"></label>
        <label>Event <input name="event" autocomplete="off"></label>
        <label>Team rank <input name="team_rank" inputmode="decimal" placeholder="#"></label>
        <label>Opp rank <input name="opponent_rank" inputmode="decimal" placeholder="#"></label>
        <label>KPR 30d <input name="kpr_30d" inputmode="decimal" placeholder="0.72"></label>
        <label>KPR 90d <input name="kpr_90d" inputmode="decimal" placeholder="0.70"></label>
        <label>HSPR <input name="hspr" inputmode="decimal"></label>
        <label>Expected rounds <input name="expected_rounds" inputmode="decimal" placeholder="43"></label>
        <label>Sharp projection <input name="sharp_projection" inputmode="decimal"></label>
        <label>PP line <input name="pp_line" inputmode="decimal" placeholder="31.0"></label>
        <label>UD line <input name="ud_line" inputmode="decimal" placeholder="31.5"></label>
        <label class="check"><input type="checkbox" name="pp_demon_more_only"> PP more-only demon</label>
        <label class="check"><input type="checkbox" name="ud_demon_more_only"> UD more-only demon</label>
        <label class="check"><input type="checkbox" name="hltv_evidence"> HLTV evidence pasted</label>
        <label class="wide">Last five (oldest → newest, comma-separated)
          <input name="last_five" autocomplete="off" placeholder="9, 17, 37, 35, 47">
        </label>
        <label class="wide">Other-player aliases (comma-separated, integrity check)
          <input name="other_player_aliases" autocomplete="off" placeholder="phzy, Astralis">
        </label>
        <label class="wide">Last-five note <input name="last_five_note" autocomplete="off"></label>
        <label class="wide">Notes <textarea name="notes" rows="3"></textarea></label>
      </div>
      <button type="submit" class="primary">Evaluate</button>
    </form>
  </section>

  <section id="results" class="hidden">
    <h2 id="resultTitle">Result</h2>
    <div id="metaLine" class="meta"></div>
    <div id="bookCards" class="books"></div>
    <div id="boardWarn"></div>
  </section>
</main>

<script type="module" src="app.js"></script>
</body>
</html>
// web/app.js — minimal UI wiring. Imports the pure engine from ../src/model.js.
// No build step: serve over HTTP (python3 -m http.server) or GitHub Pages.
import { evaluate_pick } from '../src/model.js';

const form = document.getElementById('pickForm');
const results = document.getElementById('results');

const NUM_FIELDS = [
  'team_rank', 'opponent_rank', 'kpr_30d', 'kpr_90d', 'hspr',
  'expected_rounds', 'sharp_projection', 'pp_line', 'ud_line',
];
const CHECK_FIELDS = ['pp_demon_more_only', 'ud_demon_more_only', 'hltv_evidence'];

function num(v) {
  if (v == null) return undefined;
  const t = String(v).trim();
  if (t === '') return undefined;
  const n = Number(t);
  return Number.isFinite(n) ? n : undefined;
}

function readForm() {
  const fd = new FormData(form);
  const pick = {};
  for (const [k, v] of fd.entries()) {
    if (CHECK_FIELDS.includes(k)) continue;
    pick[k] = v;
  }
  for (const f of NUM_FIELDS) pick[f] = num(pick[f]);
  for (const f of CHECK_FIELDS) pick[f] = form.elements[f].checked;
  pick.last_five = String(pick.last_five ?? '')
    .split(',')
    .map((s) => Number(s.trim()))
    .filter((n) => Number.isFinite(n));
  pick.other_player_aliases = String(pick.other_player_aliases ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  for (const k of ['player', 'team', 'opponent', 'matchup', 'event', 'last_five_note', 'notes']) {
    if (pick[k] !== undefined && String(pick[k]).trim() === '') delete pick[k];
  }
  return pick;
}

function fillForm(pick) {
  for (const el of form.elements) {
    if (!el.name) continue;
    if (CHECK_FIELDS.includes(el.name)) {
      el.checked = pick[el.name] === true;
    } else if (el.name === 'last_five') {
      el.value = Array.isArray(pick.last_five) ? pick.last_five.join(', ') : '';
    } else if (el.name === 'other_player_aliases') {
      el.value = Array.isArray(pick.other_player_aliases) ? pick.other_player_aliases.join(', ') : '';
    } else {
      el.value = pick[el.name] ?? '';
    }
  }
}

function evBadge(ev) {
  if (ev == null) return '';
  const cls = ev > 0 ? 'pos' : ev < 0 ? 'neg' : 'flat';
  return `<span class="ev ${cls}">${ev > 0 ? '+' : ''}${ev}% EV</span>`;
}

function bookCard(b, preferred) {
  const call = b.call ?? 'PASS';
  const blocked = b.call == null;
  const cls = blocked || call === 'PASS' ? 'pass' : call === 'MORE' ? 'more' : 'less';
  const conv = b.conviction && b.conviction !== 'NONE'
    ? `<span class="conv ${b.conviction.toLowerCase()}">${b.conviction}</span>` : '';
  return `
  <article class="book ${cls}${preferred ? ' preferred' : ''}">
    <div class="book-head">
      <span class="book-name">${b.book}${preferred ? ' ★ preferred' : ''}</span>
      ${conv}
    </div>
    <div class="call">${blocked ? 'PASS' : call}<span class="line"> ${b.line ?? '—'}</span></div>
    <div class="nums">
      <span>proj <b>${b.projection ?? '—'}</b></span>
      ${b.winProb != null ? `<span>win <b>${b.winProb}</b></span>` : ''}
      ${evBadge(b.ev)}
    </div>
    <p class="reason">${b.reason}</p>
    ${b.biggestRisk && b.biggestRisk !== b.reason ? `<p class="risk">⚠ ${b.biggestRisk}</p>` : ''}
  </article>`;
}

function render(r) {
  document.getElementById('resultTitle').textContent =
    `${r.player ?? 'Pick'} — ${r.verdict}`;
  document.getElementById('metaLine').textContent =
    `projection ${r.projection ?? '—'} · sigma ${r.sigma ?? '—'} · trailing-3 ${r.trailing3 ?? '—'} · ` +
    `integrity ${r.integrity_ok ? 'OK' : 'FAILED'} · evidence ${r.evidence_ok === null ? '—' : r.evidence_ok ? 'OK' : 'missing'}`;
  document.getElementById('bookCards').innerHTML =
    bookCard(r.books.prizepicks, r.preferredBook === 'PrizePicks') +
    bookCard(r.books.underdog, r.preferredBook === 'Underdog');
  results.classList.remove('hidden');
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  render(evaluate_pick(readForm()));
});

document.querySelectorAll('[data-example]').forEach((btn) => {
  btn.addEventListener('click', async () => {
    try {
      const res = await fetch(`../examples/${btn.dataset.example}.json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const pick = await res.json();
      fillForm(pick);
      render(evaluate_pick(pick));
    } catch (err) {
      alert(`Could not load example (serve over HTTP first): ${err.message}`);
    }
  });
});

document.getElementById('clearBtn').addEventListener('click', () => {
  form.reset();
  results.classList.add('hidden');
});
/* web/styles.css — clean dark mobile-friendly UI. No build step. */
:root {
  --bg: #0e1116;
  --card: #171c24;
  --line: #262d38;
  --text: #e8ecf1;
  --muted: #9aa4b2;
  --more: #22c55e;
  --less: #ef4444;
  --pass: #6b7280;
  --accent: #38bdf8;
  --warn: #f59e0b;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.45;
}
header { padding: 20px 16px 8px; max-width: 720px; margin: 0 auto; }
header h1 { margin: 0 0 4px; font-size: 1.5rem; }
.sub { color: var(--muted); margin: 0 0 8px; }
.honesty {
  font-size: 0.8rem; color: var(--muted);
  border-left: 3px solid var(--warn);
  padding-left: 10px; margin: 0 0 8px;
}
.honesty code { color: var(--text); }
main { max-width: 720px; margin: 0 auto; padding: 8px 16px 40px; }
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}
h2 { margin: 0 0 12px; font-size: 1.1rem; }
.examples { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }
.examples span { color: var(--muted); font-size: 0.85rem; }
button {
  background: var(--line); color: var(--text);
  border: 1px solid var(--line); border-radius: 8px;
  padding: 8px 14px; font-size: 0.9rem; cursor: pointer;
}
button:hover { border-color: var(--accent); }
button.ghost { background: transparent; }
button.primary {
  background: var(--accent); border-color: var(--accent);
  color: #06222e; font-weight: 700; width: 100%;
  padding: 12px; font-size: 1rem; margin-top: 12px;
}
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
label { display: flex; flex-direction: column; gap: 4px; font-size: 0.8rem; color: var(--muted); }
label.wide { grid-column: 1 / -1; }
label.check { flex-direction: row; align-items: center; gap: 8px; font-size: 0.9rem; color: var(--text); }
input, textarea {
  background: #0e1116; color: var(--text);
  border: 1px solid var(--line); border-radius: 8px;
  padding: 9px 10px; font-size: 0.95rem; width: 100%;
}
input:focus, textarea:focus { outline: none; border-color: var(--accent); }
input[type="checkbox"] { width: auto; accent-color: var(--accent); }
.hidden { display: none; }
.meta { color: var(--muted); font-size: 0.85rem; margin-bottom: 12px; }
.books { display: grid; gap: 12px; }
@media (min-width: 560px) { .books { grid-template-columns: 1fr 1fr; } }
.book {
  background: var(--card); border: 1px solid var(--line);
  border-left-width: 5px; border-radius: 12px; padding: 14px;
}
.book.more { border-left-color: var(--more); }
.book.less { border-left-color: var(--less); }
.book.pass { border-left-color: var(--pass); opacity: 0.92; }
.book.preferred { box-shadow: 0 0 0 2px var(--accent); }
.book-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.book-name { font-weight: 700; font-size: 0.85rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.conv { font-size: 0.7rem; font-weight: 800; padding: 3px 8px; border-radius: 20px; }
.conv.hammer { background: #f59e0b; color: #1a1005; }
.conv.standard { background: #38bdf8; color: #06222e; }
.conv.light { background: #334155; color: #cbd5e1; }
.call { font-size: 2rem; font-weight: 800; margin: 2px 0 8px; }
.book.more .call { color: var(--more); }
.book.less .call { color: var(--less); }
.book.pass .call { color: var(--pass); }
.call .line { font-size: 1.1rem; color: var(--muted); font-weight: 600; }
.nums { display: flex; gap: 12px; flex-wrap: wrap; font-size: 0.85rem; color: var(--muted); margin-bottom: 8px; }
.nums b { color: var(--text); }
.ev { font-weight: 700; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; }
.ev.pos { background: rgba(34,197,94,.15); color: var(--more); }
.ev.neg { background: rgba(239,68,68,.15); color: var(--less); }
.ev.flat { background: #334155; color: #cbd5e1; }
.reason { font-size: 0.88rem; margin: 0 0 6px; }
.risk { font-size: 0.85rem; color: var(--warn); margin: 0; }
# esports-picks-model

CS2 **Maps 1–2 kills** player-prop model: projection engine, canonical 1:1 EV, the
Form/KPR **straddle rule**, input-integrity gates, and fully independent
PrizePicks vs Underdog per-book evaluation. Pure JavaScript (ES modules), **zero
dependencies**. Runs on plain Node 18+ and in the browser with no build step.

> **Honesty note (read this first).** This is a faithful **open reimplementation
> of the live model's spec** — projection math, EV, straddle rule, integrity
> gates, per-book evaluation. It is **not the hosted app's literal source**; the
> hosted app's exact internal calibration constants are approximated here as
> documented tunables in `src/constants.js`. If the hosted app's numbers and this
> repo's numbers ever disagree on the same inputs, the difference is in those
> tunables — see the Tuning guide below.

## Quickstart
The web UI also deploys as-is to GitHub Pages (it imports `../src/model.js` as an
ES module — just needs plain HTTP, no bundler).

## Layout
## Rules reference

Inputs per pick: `player, team, opponent, matchup, event, kpr_30d, kpr_90d,
hspr, expected_rounds, sharp_projection, team_rank, opponent_rank, pp_line,
pp_demon_more_only, ud_line, ud_demon_more_only, last_five` (array of 5,
oldest→newest), `last_five_note, notes, hltv_evidence`, optional
`other_player_aliases`. All numerics optional except the lines; **missing data is
never invented**.

1. **Input integrity (runs first).** Names are normalized (lowercase, strip
   non-alphanumerics). Flagged if `notes`/`last_five_note` contain any alias from
   `other_player_aliases`, OR a token (`/[A-Za-z][A-Za-z0-9_]{2,15}/`) repeats ≥2
   times that is neither the player (fuzzy both directions) nor a stoplist word
   (`map, maps, kills, team, vs, average, projection, rounds, match, event,
   league, season, stage, final, playoff`, …). Flagged → **PASS both books**,
   reason `Cross-player contamination — PASS per input-integrity rule.`, and the
   pick exposes **no** call, confidence, EV, winProb, projection, or preferred
   book (all null).
2. **No-fabrication evidence gate.** Evidence exists iff a real `kpr_30d`/`kpr_90d`,
   or ≥3 real `last_five` numbers, or `hltv_evidence === true`. Else **PASS both
   books**: `No player-specific evidence — PASS per no-fabrication rule.`
3. **Projection** (1 decimal; null → `No supported projection — PASS.`). Needs a
   **real** `expected_rounds` (no fixed baseline exists anywhere) **and** a real
   KPR. `blend = 0.6·kpr_30d + 0.4·kpr_90d` (single KPR used alone);
   `raw = blend × expected_rounds × mismatch`, where mismatch = 1.25/1.15/1.08
   for rank gaps ≥100/≥50/≥20 when the player's team is favored, else 1.0.
   With a real `sharp_projection`: `0.5·raw + 0.5·sharp`.
4. **Sigma / trailing-3.** Sigma = population SD of `last_five` (≥2 values),
   floored at 6.0; 7.0 default when <2 values. Trailing-3 = mean of the 3 most
   recent entries (null when <3).
5. **Canonical 1:1 EV** per book: `p_win = P(Normal(projection, sigma) ⋛ line)`
   (lines are x.5, no pushes; dependency-free erf normal CDF), `ev = 2·p_win − 1`.
6. **Per-book evaluation** (PrizePicks vs `pp_line`, Underdog vs `ud_line`,
   fully independent):
   - side = MORE / LESS / NONE (equal → `Projection equals line — PASS.`).
   - **Demon:** more-only demon + MORE side → PASS (`More-only demon line —
     bait, wait for the two-sided board.`).
   - **Straddle (the key rule):** projection and trailing-3 on **opposite sides**
     of *this book's line* **and** `|ev|` strictly under 2% →
     `Form/KPR straddle: trailing-3 avg {t3} vs projection {proj} on opposite sides of the {line} line, edge under 2%.`
   - **Range:** line inside `[projection − sigma, projection + sigma]` (inclusive)
     → `Adjusted range straddles the line — PASS (thin edge).` Fire only when the
     whole band clears the line.
   - **Conviction** on |ev|: ≥6% HAMMER, ≥2% STANDARD, >0 LIGHT.
   - Every book PASS → pick verdict PASS. A PASS is never turned into a play.
   - `preferredBook`: among fired calls, the book with the higher EV (the more
     favorable line); null when nothing fires.
7. **Board:** `evaluate_board` warns on **3+ same-team same-direction** fired
   plays (correlation) and on **duplicate players** (one prop per player).

## Examples → expected outcomes

- **`examples/afro.json`** — afro (Luminosity vs B8), last-five
  `[9,17,37,35,47]`, projection computes to **30.5**, trailing-3 **39.7**,
  PP 31.0 / UD 31.5. **Expected: PASS both books.** Spec-math note: with
  sigma 13.9 the canonical edges are 2.9% (PP) and 5.7% (UD), so the strict
  sub-2% straddle gate does *not* trigger — both books PASS via the
  adjusted-range gate instead. The historical +0.8% EV came from the live app's
  different sigma calibration; the opposite-sides structure (39.7 vs 30.5 around
  both lines) is preserved.
- **`examples/phzy.json`** — Phzy (Astralis vs Alliance), projection **30.1**,
  trailing-3 **29.3**, PP 29.5 / UD 30.5. **Expected: PASS both, evaluated
  independently** — PP takes the MORE side vs 29.5 (opposite sides vs trailing-3,
  but edge 3.8% ≥ 2% → range PASS); UD takes the LESS side vs 30.5 (both below
  the line → range PASS). Demonstrates per-book independence.
- **`examples/fear.json`** — Fear (fnatic vs BIG) whose notes carry another
  player's data (`phzy` twice + alias list). **Expected: integrity FAILED →
  PASS both books**, reason `Cross-player contamination — PASS per
  input-integrity rule.`, with call/confidence/EV/winProb/projection and
  preferred book all null.

## Tuning guide

Every number that shapes behavior lives in `src/constants.js` — re-calibration
is a one-file edit, and `npm test` (23 tests, incl. the three fixtures) tells you
immediately what moved:

| Constant | Default | Effect |
|---|---|---|
| `KPR_30D_WEIGHT` / `KPR_90D_WEIGHT` | 0.6 / 0.4 | recency vs stability in KPR blend |
| `SHARP_BLEND_WEIGHT` | 0.5 | raw KPR×rounds vs sharp projection |
| `MISMATCH_GAP_{100,50,20}_MULT` | 1.25 / 1.15 / 1.08 | favorite's frag inflation vs weaker ranks |
| `SIGMA_FLOOR` / `SIGMA_DEFAULT` | 6.0 / 7.0 | minimum / fallback spread |
| `STRADDLE_EV_MAX` | 0.02 | straddle PASS only when edge strictly under this |
| `EV_HAMMER` / `EV_STANDARD` | 0.06 / 0.02 | conviction ladder on |ev| |
| `STOPLIST_WORDS` | (list) | tokens the contamination heuristic ignores |

Known approximation vs the hosted app: the hosted app's sigma calibration
produced smaller canonical edges on volatile histories (e.g. afro's +0.8% vs
2.9%/5.7% here). If you want this repo to reproduce those edges, raise
`SIGMA_FLOOR`/`SIGMA_DEFAULT` — the afro fixture documents the exact numbers to
match against.

## License

MIT — do what you want with it.
