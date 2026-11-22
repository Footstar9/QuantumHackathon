/*
 * qec.js - the quantum engine behind Schrödinger's Cargo.
 *
 * Code used: the 9-qubit Shor code.
 *   |0_L> = (|000> + |111>)(|000> + |111>)(|000> + |111>) / (2*sqrt(2))
 *   |1_L> = (|000> - |111>)(|000> - |111>)(|000> - |111>) / (2*sqrt(2))
 *
 * Qubits are numbered 0..8 in code and shown to players as q1..q9.
 * Qubit 0 is the LEFTMOST character of a ket, i.e. the most significant bit
 * of the basis-state index.
 *
 * Two independent views of the same physics live in this file:
 *   1. A full state-vector simulator (512 complex amplitudes). The game uses
 *      it to light the syndrome lamps and to score the cargo.
 *   2. A fast "Pauli bookkeeping" (symplectic) model: each error is a list of
 *      I/X/Y/Z, and a check lamp lights when the error anticommutes with it.
 * tests/test_qec.js checks that both views agree for every possible error.
 *
 * Works both in the browser (window.QEC) and in Node (require('./qec.js')).
 */
(function (root) {
  'use strict';

  const N = 9;
  const DIM = 1 << N; // 512
  const PAULI = ['I', 'X', 'Y', 'Z']; // codes 0,1,2,3

  // The 8 stabilizer checks ("lamps").
  // kind 'Z' checks are made of Z's and light up for bit flips (X or Y).
  // kind 'X' checks are made of X's and light up for phase flips (Z or Y).
  const CHECKS = [
    { id: 'A12', op: 'ZZIIIIIII', kind: 'Z', qubits: [0, 1] },
    { id: 'A23', op: 'IZZIIIIII', kind: 'Z', qubits: [1, 2] },
    { id: 'B45', op: 'IIIZZIIII', kind: 'Z', qubits: [3, 4] },
    { id: 'B56', op: 'IIIIZZIII', kind: 'Z', qubits: [4, 5] },
    { id: 'C78', op: 'IIIIIIZZI', kind: 'Z', qubits: [6, 7] },
    { id: 'C89', op: 'IIIIIIIZZ', kind: 'Z', qubits: [7, 8] },
    { id: 'AB', op: 'XXXXXXIII', kind: 'X', qubits: [0, 1, 2, 3, 4, 5] },
    { id: 'BC', op: 'IIIXXXXXX', kind: 'X', qubits: [3, 4, 5, 6, 7, 8] },
  ];

  // Logical operators of the Shor code.
  // Z^9 maps |0_L> <-> |1_L>, so it is the logical X ("the cargo's bit flips").
  // X^9 gives |1_L> a minus sign, so it is the logical Z ("the cargo's phase flips").
  const LOGICAL_X = 'ZZZZZZZZZ';
  const LOGICAL_Z = 'XXXXXXXXX';

  // ---------- Pauli bookkeeping ----------

  function parse(str) {
    return str.split('').map((c) => PAULI.indexOf(c));
  }
  function toStr(p) {
    return p.map((c) => PAULI[c]).join('');
  }
  const xBit = (c) => (c === 1 || c === 2 ? 1 : 0);
  const zBit = (c) => (c === 2 || c === 3 ? 1 : 0);

  // Multiply two Pauli strings, ignoring the overall phase (it never matters
  // for which lamps light or whether the cargo survives).
  function multiply(a, b) {
    return a.map((c, i) => {
      const x = xBit(c) ^ xBit(b[i]);
      const z = zBit(c) ^ zBit(b[i]);
      return x ? (z ? 2 : 1) : z ? 3 : 0;
    });
  }

  // 1 if the two Pauli strings anticommute, 0 if they commute.
  function anticommutes(a, b) {
    let n = 0;
    for (let i = 0; i < a.length; i++) {
      n += xBit(a[i]) * zBit(b[i]) + zBit(a[i]) * xBit(b[i]);
    }
    return n % 2;
  }

  const CHECK_OPS = CHECKS.map((c) => parse(c.op));
  const LX = parse(LOGICAL_X);
  const LZ = parse(LOGICAL_Z);

  // Which lamps light (array of 8 zeros/ones), using the bookkeeping model.
  function syndrome(p) {
    return CHECK_OPS.map((s) => anticommutes(p, s));
  }

  // What a leftover error (Noise's error times Decoder's fix) does to the cargo.
  //   lit      : true if some lamp is still on (state knocked out of the code)
  //   logical  : 'I' | 'X' | 'Y' | 'Z' - the effect on the stored qubit
  //   safe     : true only if the cargo is restored exactly
  function classify(residual) {
    const s = syndrome(residual);
    const lit = s.some((v) => v === 1);
    // A logical X anticommutes with logical Z, and vice versa.
    const flipsBit = anticommutes(residual, LZ) === 1; // acts like logical X
    const flipsPhase = anticommutes(residual, LX) === 1; // acts like logical Z
    const logical = flipsBit ? (flipsPhase ? 'Y' : 'X') : flipsPhase ? 'Z' : 'I';
    return { lit, logical, safe: !lit && logical === 'I', syndrome: s };
  }

  function weight(p) {
    return p.reduce((n, c) => n + (c ? 1 : 0), 0);
  }

  // ---------- State-vector simulator ----------

  function makeState() {
    return { re: new Float64Array(DIM), im: new Float64Array(DIM) };
  }
  function copyState(s) {
    return { re: Float64Array.from(s.re), im: Float64Array.from(s.im) };
  }

  // Build alpha|0_L> + beta|1_L>. alpha, beta are {re, im}.
  function encode(alpha, beta) {
    const s = makeState();
    const norm = 1 / (2 * Math.SQRT2);
    // Each block is |000> or |111>; 8 combinations over the three blocks.
    for (let m = 0; m < 8; m++) {
      let idx = 0;
      let ones = 0; // number of blocks in |111>
      for (let blk = 0; blk < 3; blk++) {
        const bit = (m >> (2 - blk)) & 1;
        ones += bit;
        idx = (idx << 3) | (bit ? 7 : 0);
      }
      const sign1 = ones % 2 === 0 ? 1 : -1; // (|000> - |111>)^3 sign
      s.re[idx] = norm * (alpha.re + sign1 * beta.re);
      s.im[idx] = norm * (alpha.im + sign1 * beta.im);
    }
    return s;
  }

  // Apply a Pauli string to a state (returns a new state). Exact, including phases.
  function applyPauli(state, p) {
    let s = copyState(state);
    for (let q = 0; q < N; q++) {
      const c = p[q];
      if (!c) continue;
      const mask = 1 << (N - 1 - q);
      const out = makeState();
      for (let b = 0; b < DIM; b++) {
        const bit = (b & mask) ? 1 : 0;
        let re = s.re[b];
        let im = s.im[b];
        let target = b;
        if (c === 1) {
          target = b ^ mask; // X|b> = |b xor 1>
        } else if (c === 3) {
          if (bit) { re = -re; im = -im; } // Z|1> = -|1>
        } else {
          // Y|0> = i|1>, Y|1> = -i|0>
          target = b ^ mask;
          const r = re;
          if (bit) { re = im; im = -r; } // multiply by -i
          else { re = -im; im = r; } // multiply by +i
        }
        out.re[target] = re;
        out.im[target] = im;
      }
      s = out;
    }
    return s;
  }

  // <a|b> as {re, im}
  function inner(a, b) {
    let re = 0;
    let im = 0;
    for (let i = 0; i < DIM; i++) {
      re += a.re[i] * b.re[i] + a.im[i] * b.im[i];
      im += a.re[i] * b.im[i] - a.im[i] * b.re[i];
    }
    return { re, im };
  }

  function fidelity(a, b) {
    const z = inner(a, b);
    return z.re * z.re + z.im * z.im;
  }

  // <psi|P|psi>. For a stabilizer check this is exactly +1 (lamp off) or -1 (lamp on).
  function expectation(state, p) {
    return inner(state, applyPauli(state, p)).re;
  }

  // Lamps as the game shows them: measured on the simulated state.
  function measureLamps(state) {
    return CHECK_OPS.map((op) => (expectation(state, op) < 0 ? 1 : 0));
  }

  // The six standard test states of a qubit (same as the error-correction brief).
  const R = Math.SQRT1_2;
  const CARDINAL = [
    { name: '|0⟩', a: { re: 1, im: 0 }, b: { re: 0, im: 0 } },
    { name: '|1⟩', a: { re: 0, im: 0 }, b: { re: 1, im: 0 } },
    { name: '|+⟩', a: { re: R, im: 0 }, b: { re: R, im: 0 } },
    { name: '|−⟩', a: { re: R, im: 0 }, b: { re: -R, im: 0 } },
    { name: '|+i⟩', a: { re: R, im: 0 }, b: { re: 0, im: R } },
    { name: '|−i⟩', a: { re: R, im: 0 }, b: { re: 0, im: -R } },
  ];

  // Fidelity of every cardinal cargo after a leftover error, by direct simulation.
  function cardinalFidelities(residual) {
    return CARDINAL.map((c) => {
      const psi = encode(c.a, c.b);
      return { name: c.name, f: fidelity(psi, applyPauli(psi, residual)) };
    });
  }

  // A random cargo qubit: cos(t/2)|0> + e^{i phi} sin(t/2)|1>
  function randomCargo(rng) {
    const r = rng || Math.random;
    const theta = Math.acos(1 - 2 * r());
    const phi = 2 * Math.PI * r();
    return {
      theta,
      phi,
      a: { re: Math.cos(theta / 2), im: 0 },
      b: { re: Math.sin(theta / 2) * Math.cos(phi), im: Math.sin(theta / 2) * Math.sin(phi) },
    };
  }

  // ---------- A reference "fewest errors" decoder (for analysis and tests) ----------
  // Precomputed table: syndrome -> lowest-weight Pauli that produces it.
  let _table = null;
  function minWeightTable() {
    if (_table) return _table;
    _table = new Map();
    const total = Math.pow(4, N);
    const byWeight = [];
    for (let k = 0; k < total; k++) {
      const p = [];
      let v = k;
      for (let q = 0; q < N; q++) { p.push(v & 3); v >>= 2; }
      byWeight.push(p);
    }
    byWeight.sort((u, v) => weight(u) - weight(v));
    for (const p of byWeight) {
      const key = syndrome(p).join('');
      if (!_table.has(key)) _table.set(key, p);
      if (_table.size === 256) break;
    }
    return _table;
  }
  function minWeightGuess(synd) {
    return minWeightTable().get(synd.join(''));
  }

  const QEC = {
    N, PAULI, CHECKS, CHECK_OPS, LOGICAL_X, LOGICAL_Z, CARDINAL,
    parse, toStr, multiply, anticommutes, syndrome, classify, weight,
    encode, applyPauli, inner, fidelity, expectation, measureLamps,
    cardinalFidelities, randomCargo, minWeightGuess,
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = QEC;
  else root.QEC = QEC;
})(typeof window !== 'undefined' ? window : this);
