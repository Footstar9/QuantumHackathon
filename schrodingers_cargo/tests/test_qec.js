/*
 * Verifies the quantum engine of Schrödinger's Cargo.
 * Run from the schrodingers_cargo folder:   node tests/test_qec.js
 *
 * What it checks:
 *  1. The encoded cargo really is a Shor-code state (normalised, all 8 checks = +1).
 *  2. The lamp table (fast Pauli bookkeeping) matches a direct state-vector
 *     simulation for EVERY error on up to 3 qubits (2,620 errors) plus 3,000
 *     random heavier errors.
 *  3. The win/lose judgement matches simulation: for each leftover error we
 *     encode the six test states |0>,|1>,|+>,|->,|+i>,|-i>, apply it, and
 *     compare the fidelity with what the judgement predicts.
 *  4. Every single-qubit error (27 of them) is always fixed by a
 *     fewest-errors decoder (the code has distance 3).
 *  5. A full round of the game (random cargo, Noise error, Decoder fix) gives
 *     fidelity 1 exactly when the game says "cargo safe".
 * Then it prints the statistics quoted in the handout.
 */
'use strict';
const path = require('path');
const Q = require(path.join(__dirname, '..', 'qec.js'));

let passed = 0;
let failed = 0;
function check(cond, msg) {
  if (cond) passed++;
  else { failed++; if (failed < 20) console.error('FAIL:', msg); }
}
const close = (a, b, eps = 1e-9) => Math.abs(a - b) < eps;

// Small deterministic random generator so runs are repeatable.
let seed = 12345;
function rng() {
  seed = (seed * 1103515245 + 12345) & 0x7fffffff;
  return seed / 0x7fffffff;
}

// All Pauli strings with exactly k non-identity entries.
function errorsOfWeight(k) {
  const out = [];
  function rec(start, left, p) {
    if (left === 0) { out.push(p.slice()); return; }
    for (let q = start; q < Q.N; q++) {
      for (let c = 1; c <= 3; c++) { p[q] = c; rec(q + 1, left - 1, p); p[q] = 0; }
    }
  }
  rec(0, k, new Array(Q.N).fill(0));
  return out;
}
const I9 = new Array(Q.N).fill(0);

// ---- 1. Code space ----
{
  const zero = Q.encode({ re: 1, im: 0 }, { re: 0, im: 0 });
  const one = Q.encode({ re: 0, im: 0 }, { re: 1, im: 0 });
  check(close(Q.fidelity(zero, zero), 1), '|0_L> normalised');
  check(close(Q.fidelity(one, one), 1), '|1_L> normalised');
  check(close(Q.fidelity(zero, one), 0), '|0_L> and |1_L> orthogonal');
  for (let t = 0; t < 20; t++) {
    const c = Q.randomCargo(rng);
    const psi = Q.encode(c.a, c.b);
    check(close(Q.fidelity(psi, psi), 1), 'random cargo normalised');
    for (const op of Q.CHECK_OPS) check(close(Q.expectation(psi, op), 1), 'check = +1 on code state');
  }
  // Logical operators act as advertised.
  const LX = Q.parse(Q.LOGICAL_X);
  const LZ = Q.parse(Q.LOGICAL_Z);
  check(close(Q.fidelity(Q.applyPauli(zero, LX), one), 1), 'Z^9 maps |0_L> to |1_L>');
  const plus = Q.encode({ re: Math.SQRT1_2, im: 0 }, { re: Math.SQRT1_2, im: 0 });
  const minus = Q.encode({ re: Math.SQRT1_2, im: 0 }, { re: -Math.SQRT1_2, im: 0 });
  check(close(Q.fidelity(Q.applyPauli(plus, LZ), minus), 1), 'X^9 maps |+_L> to |-_L>');
  // Every check commutes with every other check and with both logicals.
  for (const a of Q.CHECK_OPS) {
    for (const b of Q.CHECK_OPS) check(Q.anticommutes(a, b) === 0, 'checks commute');
    check(Q.anticommutes(a, LX) === 0 && Q.anticommutes(a, LZ) === 0, 'logicals commute with checks');
  }
  check(Q.anticommutes(LX, LZ) === 1, 'logical X and Z anticommute');
}

// ---- 2. Lamp table vs simulation ----
const testErrors = [I9, ...errorsOfWeight(1), ...errorsOfWeight(2), ...errorsOfWeight(3)];
const nLow = testErrors.length;
for (let t = 0; t < 3000; t++) {
  testErrors.push(Array.from({ length: Q.N }, () => Math.floor(rng() * 4)));
}
{
  const cargo = Q.randomCargo(rng);
  const psi = Q.encode(cargo.a, cargo.b);
  for (const e of testErrors) {
    const lampsSim = Q.measureLamps(Q.applyPauli(psi, e));
    const lampsTable = Q.syndrome(e);
    check(lampsSim.join('') === lampsTable.join(''), 'lamps match for ' + Q.toStr(e));
  }
}

// ---- 3. Judgement vs simulation on the six test states ----
// Expected fidelity |<c|L|c>|^2 for a single qubit, where L is the logical Pauli.
function singleQubitFid(c, L) {
  const a = c.a, b = c.b; // state a|0> + b|1>
  let a2, b2; // L applied
  if (L === 'I') { a2 = a; b2 = b; }
  else if (L === 'X') { a2 = b; b2 = a; }
  else if (L === 'Z') { a2 = a; b2 = { re: -b.re, im: -b.im }; }
  else { a2 = { re: b.im, im: -b.re }; b2 = { re: -a.im, im: a.re }; } // Y = [[0,-i],[i,0]]
  const re = a.re * a2.re + a.im * a2.im + b.re * b2.re + b.im * b2.im;
  const im = a.re * a2.im - a.im * a2.re + b.re * b2.im - b.im * b2.re;
  return re * re + im * im;
}
for (const r of testErrors) {
  const verdict = Q.classify(r);
  const sims = Q.cardinalFidelities(r);
  sims.forEach((s, i) => {
    const expected = verdict.lit ? 0 : singleQubitFid(Q.CARDINAL[i], verdict.logical);
    check(close(s.f, expected), 'fidelity ' + Q.toStr(r) + ' ' + s.name + ' got ' + s.f + ' want ' + expected);
  });
  const allOne = sims.every((s) => close(s.f, 1));
  check(allOne === verdict.safe, 'safe <=> all six fidelities are 1 for ' + Q.toStr(r));
}

// ---- 4. Single errors are always fixable ----
for (const e of [I9, ...errorsOfWeight(1)]) {
  const fix = Q.minWeightGuess(Q.syndrome(e));
  check(Q.classify(Q.multiply(e, fix)).safe, 'single error fixed: ' + Q.toStr(e));
}

// ---- 5. Whole rounds with a random cargo ----
for (let t = 0; t < 400; t++) {
  const cargo = Q.randomCargo(rng);
  const psi = Q.encode(cargo.a, cargo.b);
  const noise = testErrors[Math.floor(rng() * nLow)];
  const fix = rng() < 0.5 ? Q.minWeightGuess(Q.measureLamps(Q.applyPauli(psi, noise)))
    : Array.from({ length: Q.N }, () => (rng() < 0.2 ? 1 + Math.floor(rng() * 3) : 0));
  const after = Q.applyPauli(Q.applyPauli(psi, noise), fix);
  const f = Q.fidelity(psi, after);
  const verdict = Q.classify(Q.multiply(noise, fix));
  if (verdict.safe) check(close(f, 1), 'safe round has fidelity 1');
  if (verdict.lit) check(close(f, 0), 'lit round has fidelity 0');
}

console.log(`\n${passed} checks passed, ${failed} failed.`);
console.log(`(${nLow} errors on up to 3 qubits checked exhaustively, plus 3000 random errors.)\n`);

// ---- Statistics for the handout ----
console.log('How often does a "fewest-errors" decoder win, if Noise picks uniformly at random');
console.log('among all errors that use at most B qubits?');
for (let B = 1; B <= 3; B++) {
  let total = 0, wins = 0;
  for (let k = 0; k <= B; k++) {
    for (const e of (k === 0 ? [I9] : errorsOfWeight(k))) {
      total++;
      if (Q.classify(Q.multiply(e, Q.minWeightGuess(Q.syndrome(e)))).safe) wins++;
    }
  }
  console.log(`  budget ${B}: ${wins}/${total} = ${(100 * wins / total).toFixed(1)}% saved`);
}
// Two-qubit errors broken down by type.
{
  const groups = { 'two bit flips (X,X)': [0, 0], 'two phase flips (Z,Z)': [0, 0], 'mixed / Y': [0, 0] };
  for (const e of errorsOfWeight(2)) {
    const nz = e.filter((c) => c);
    const key = nz.every((c) => c === 1) ? 'two bit flips (X,X)' : nz.every((c) => c === 3) ? 'two phase flips (Z,Z)' : 'mixed / Y';
    groups[key][1]++;
    if (Q.classify(Q.multiply(e, Q.minWeightGuess(Q.syndrome(e)))).safe) groups[key][0]++;
  }
  console.log('Two-qubit errors, fewest-errors decoder:');
  for (const [k, [w, t]] of Object.entries(groups)) console.log(`  ${k}: ${w}/${t} = ${(100 * w / t).toFixed(1)}% saved`);
}

process.exit(failed ? 1 : 0);
