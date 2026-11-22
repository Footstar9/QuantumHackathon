# Level 1 on IQM quantum hardware

This folder runs the Level 1 bit-flip code (from `../level1.py`) on a perfect
simulator, on a noisy model of IQM's Garnet chip, and on the real IQM
computer, then plots all three side by side.

| File | What it is |
| --- | --- |
| `run_level1_iqm.py` | Builds the Qiskit circuits and runs them (`simulate`, `hardware`, `fetch`, `plot`, `draw`). |
| `plot_level1_iqm.py` | Draws the comparison plots. |
| `results/` | Saved counts (`ideal.json`, `noisy_fake_garnet.json`, `hardware.json`) and plots. |
| `../tests/test_iqm_circuit.py` | Checks all 24 Qiskit circuits are perfect on the ideal simulator. |

## What gets run

24 circuits: 6 test states (|0⟩, |1⟩, |+⟩, |−⟩, |+i⟩, |−i⟩) × 4 errors (I, X0, X1, X2),
1000 shots each on hardware, all sent as **one job**.

Each circuit is exactly the Level 1 circuit (encode, error, syndrome with helpers
q3 and q4, decode) with two hardware-friendly choices:

1. **All measurements at the end, correction in software.** The helpers are
   measured at the end and the syndrome table picks which qubit to fix. The fix
   (an X) is applied to the *reading* instead of the qubit. This is called
   Pauli-frame correction and is what real QEC experiments do. It is exactly
   equivalent, because an X just before a measurement only flips how the result
   is read, and it avoids slow, noisy mid-circuit measurements.
2. **Each state is read in its own basis.** |0⟩, |1⟩ in Z, |+⟩, |−⟩ in X (H first),
   |+i⟩, |−i⟩ in Y (S† then H). This checks the phases survived, not just 0/1.

The compiled circuits are small: 5 qubits, at most 11 two-qubit gates on Garnet.

## Running it

```
pip install -r iqm/requirements-iqm.txt
python iqm/run_level1_iqm.py simulate     # free, no token
python iqm/run_level1_iqm.py hardware     # needs IQM_TOKEN, uses credits
python iqm/run_level1_iqm.py plot
```

The token is read from the `IQM_TOKEN` environment variable. Never put it in a file in this repo.
Use `--computer emerald` (or another name from the IQM Resonance dashboard) to pick a different machine.
If the window closes while waiting, the job id is in `results/hardware_job.json`; get the results with
`python iqm/run_level1_iqm.py fetch <job id>`.

## Simulation results (noisy Garnet model, 4000 shots)

* Ideal simulator: every one of the 24 cases succeeds 100% of the time.
* Noisy model: the syndrome is right about 89% of the time and the secret comes back
  right about 90% of the time on average.
* With correction switched off, X0 on |0⟩, |1⟩, |±i⟩ fails about 90–95% of the time,
  so the correction is clearly doing its job.
* X errors on |+⟩, |−⟩ do no harm even without correction, because X leaves |±⟩ unchanged.
* When there is no error, the correction slightly *lowers* success (about 0.92 instead of 0.96
  for |0⟩), because noise sometimes produces a false syndrome and we then "fix" a good qubit.
