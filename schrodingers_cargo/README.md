# Schrödinger's |Cargo⟩

A two-player, pass-the-computer browser game about **quantum error correction**, built for the Qublitz 2026 *Quantum Create* challenge.

One player is the **Noise**: they secretly flip up to 2 of 9 qubits with bit flips (X), phase flips (Z) or both (Y).
The other player is the **Decoder**: they never see the qubits, only 8 warning lamps (the *syndrome*), and must undo the damage.
Roles swap every round and the score shows who outsmarted whom.

Under the hood the cargo is a real logical qubit in **Shor's 9-qubit code**, simulated with a full 512-amplitude state vector.

## How to run (no install)

1. On GitHub, click the green **Code** button, then **Download ZIP**, and unzip it.
   (Or, in VS Code: *Clone Git Repository…*, paste the repo URL, then switch to this branch.)
2. Open the `schrodingers_cargo` folder.
3. **Double-click `index.html`.** It opens in your browser. It works offline.

The printable rules and the full write-up are in [`handout.html`](handout.html) (open it and press *Print / save as PDF*) and [`handout.pdf`](handout.pdf).

## How to play (short version)

1. Type two names, choose rounds and the Noise budget (1 = tutorial, 2 = classic, 3 = chaos).
2. **Noise** picks I / X / Y / Z on up to *budget* qubits, then presses *Seal the cargo*.
3. A curtain screen appears: pass the computer. The **Decoder** sees only the lamps:
   - orange lamps (inside a crate): "do these two qubits have the same bit?" They light for X or Y.
   - blue lamps (between crates): "do these two crates have the same phase?" They light for Z or Y.
4. The Decoder applies fixes with the same switches (the lamps preview the result) and presses *Ship it*.
5. Cargo exactly restored: Decoder scores. Otherwise: Noise scores.

## What the code can and cannot do

- Every **single** error (27 of them) can always be fixed.
- Some different errors light the same lamps and are fixed the same way (e.g. Z on q1, q2 or q3): this is *degeneracy*.
- **Two** errors can impersonate one: X on q1 and q2 looks like X on q3, and "fixing" q3 silently flips the cargo (a *logical* error). That is the heart of the game.
- With random budget-2 moves a fewest-errors decoder wins 66.8% of the time, so a smart Decoder usually has a good guess but never a sure thing.

## Files

| File | What it does |
|---|---|
| `index.html`, `style.css` | The page and its look |
| `game.js` | Screens, turns, scoring |
| `qec.js` | The quantum engine: state-vector simulator, stabilizer checks, verdicts |
| `tests/test_qec.js` | Verifies the lamp table and the verdicts against direct simulation |
| `handout.html` / `handout.pdf` | Rules, the physics, implementation, verification, limitations, demo script, judge Q&A, attribution |

## Verifying it

Install [Node.js](https://nodejs.org), open a terminal in this folder and run:

```
node tests/test_qec.js
```

Expected output starts with `45529 checks passed, 0 failed.` The test:

- checks every error on up to 3 qubits (2,620 errors) and 3,000 random heavier ones: the lamps from direct simulation match the syndrome table;
- encodes the six test states |0⟩, |1⟩, |+⟩, |−⟩, |+i⟩, |−i⟩, applies each leftover error and confirms the game's verdict ("safe" exactly when all six fidelities are 1);
- confirms all single-qubit errors are fixable, and plays 400 simulated rounds.

## Attribution

Concept and direction by Oscar. Code, tests, styling and documentation were written with the help of Claude (an AI assistant by Anthropic) and reviewed and tested by us. Shor's code: P. W. Shor, Phys. Rev. A 52, R2493 (1995).
