"""
Level 1 (bit-flip code) on IQM quantum hardware, compared with simulation.

This turns the circuit from level1.py into a Qiskit circuit and runs it in
three places:

    ideal      perfect simulator (Qiskit Aer, no noise)        -> what theory says
    noisy      IQMFakeGarnet: a local simulator with a noise    -> a preview of hardware
               model of IQM's Garnet chip (no token needed)
    hardware   the real IQM computer through IQM Resonance      -> needs your token

Commands (run from the level1_python folder):

    python iqm/run_level1_iqm.py simulate          # ideal + noisy, free, no token
    python iqm/run_level1_iqm.py hardware          # sends ONE job to IQM (uses credits)
    python iqm/run_level1_iqm.py fetch JOB_ID      # get results of an earlier job
    python iqm/run_level1_iqm.py plot              # draw the comparison plots

The token is read from the IQM_TOKEN environment variable by IQM's own
library. It is never written to any file by this script.

How the hardware circuit differs from level1.py (and why it is still the same code)
------------------------------------------------------------------------------------
level1.py measures the helpers in the middle, then flips the blamed qubit.
On hardware we keep every gate the same but measure everything at the END and
apply the flip in software ("Pauli frame" correction). This is how real QEC
experiments do it: a flip X just before a measurement only changes how we read
the result, so doing it on paper is exactly equivalent and saves a slow,
error-prone mid-circuit measurement.

To check the *quantum* information (not just 0/1), each of the six test
states is read in its own basis after decoding:
    |0>, |1>   read in Z   (plain measurement)
    |+>, |->   read in X   (H then measure)
    |+i>, |-i> read in Y   (S-dagger, H, then measure)
If the phases were damaged, the X and Y readings would come out wrong.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))      # so "import level1" works

import level1  # noqa: E402  (Oscar's Level 1 code: qubit layout, errors, syndrome table)

from qiskit import QuantumCircuit, transpile  # noqa: E402

RESULTS_DIR = os.path.join(HERE, "results")
DEFAULT_SERVER = "https://resonance.iqm.tech"
DEFAULT_COMPUTER = "garnet"

# state name -> (gates that make it from |0>, basis to read it in, correct answer)
STATES = {
    "|0>":  ([],            "Z", 0),
    "|1>":  (["x"],         "Z", 1),
    "|+>":  (["h"],         "X", 0),
    "|->":  (["x", "h"],    "X", 1),
    "|+i>": (["h", "s"],    "Y", 0),
    "|-i>": (["h", "sdg"],  "Y", 1),
}
ERRORS = list(level1.ERRORS)          # ["I", "X0", "X1", "X2"]
A01, A12 = level1.ANCILLA_01, level1.ANCILLA_12


# ---------------------------------------------------------------------------
# 1. Build the circuits
# ---------------------------------------------------------------------------

def build_circuit(state_name, error_name):
    """The Level 1 circuit for one (test state, error) pair, as a Qiskit circuit."""
    prep_gates, basis, _ = STATES[state_name]
    qc = QuantumCircuit(level1.NUM_QUBITS, level1.NUM_QUBITS,
                        name=f"L1_{state_name}_{error_name}")

    # Stage 0: make the secret state on q0
    for g in prep_gates:
        getattr(qc, g)(0)
    qc.barrier()

    # Stage 1: encode  a|0>+b|1>  ->  a|000>+b|111>   (same CNOTs as level1.encode)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.barrier()

    # Stage 2: the "mine" (barriers stop the compiler from deleting it)
    qubit = level1.ERRORS[error_name]
    if qubit is not None:
        qc.x(qubit)
    qc.barrier()

    # Stage 3: syndrome  (same CNOTs as level1.extract_syndrome)
    qc.cx(0, A01)
    qc.cx(1, A01)
    qc.cx(1, A12)
    qc.cx(2, A12)
    qc.barrier()

    # Stage 5: decode (same as level1.decode). Recovery happens in software later.
    qc.cx(0, 2)
    qc.cx(0, 1)

    # Read q0 in the basis that matches the test state
    if basis == "X":
        qc.h(0)
    elif basis == "Y":
        qc.sdg(0)
        qc.h(0)
    qc.barrier()

    qc.measure(range(level1.NUM_QUBITS), range(level1.NUM_QUBITS))
    return qc


def all_cases():
    return [(s, e) for s in STATES for e in ERRORS]


# ---------------------------------------------------------------------------
# 2. Turn raw counts into answers
# ---------------------------------------------------------------------------

def bit(key, i):
    """Qiskit writes bitstrings with qubit 0 on the RIGHT, so bit i is key[-1-i]."""
    key = key.replace(" ", "")
    return int(key[-1 - i])


def analyse(state_name, error_name, counts):
    """
    For each shot: read the syndrome, look it up in Oscar's SYNDROME_TABLE,
    and apply the correction in software. Returns success rates and syndromes.
    """
    _, basis, answer = STATES[state_name]
    expected_syndrome = {None: (0, 0), 0: (1, 0), 1: (1, 1), 2: (0, 1)}[level1.ERRORS[error_name]]
    shots = sum(counts.values())
    ok_corrected = ok_raw = right_syndrome = 0
    syndromes = {"00": 0, "10": 0, "11": 0, "01": 0}

    for key, n in counts.items():
        s = (bit(key, A01), bit(key, A12))
        syndromes[f"{s[0]}{s[1]}"] += n
        out = bit(key, 0)
        if out == answer:
            ok_raw += n
        # A flip on q0 before decoding is still a flip (X) on q0 after decoding.
        # X flips a Z or Y reading but leaves an X reading unchanged.
        if level1.SYNDROME_TABLE[s] == 0 and basis in ("Z", "Y"):
            out ^= 1
        if out == answer:
            ok_corrected += n
        if s == expected_syndrome:
            right_syndrome += n

    return {
        "state": state_name, "error": error_name, "basis": basis, "shots": shots,
        "success_corrected": ok_corrected / shots,
        "success_uncorrected": ok_raw / shots,
        "syndrome_correct": right_syndrome / shots,
        "syndromes": {k: v / shots for k, v in syndromes.items()},
        "counts": counts,
    }


def summarise(rows, label):
    avg = lambda k: sum(r[k] for r in rows) / len(rows)  # noqa: E731
    print(f"\n{label}: {len(rows)} circuits, {rows[0]['shots']} shots each")
    print(f"{'state':>6} {'error':>5} {'syndrome ok':>12} {'success':>8} {'no fix':>7}")
    for r in rows:
        print(f"{r['state']:>6} {r['error']:>5} {r['syndrome_correct']:>12.3f} "
              f"{r['success_corrected']:>8.3f} {r['success_uncorrected']:>7.3f}")
    print(f"average: syndrome ok {avg('syndrome_correct'):.3f}, "
          f"success with correction {avg('success_corrected'):.3f}, "
          f"without {avg('success_uncorrected'):.3f}")


def save(name, payload):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, name)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"saved {os.path.relpath(path)}")


def circuit_stats(transpiled):
    two_q = [sum(1 for ins in c.data if ins.operation.num_qubits == 2) for c in transpiled]
    depth = [c.depth() for c in transpiled]
    return {"two_qubit_gates_max": max(two_q), "two_qubit_gates_min": min(two_q),
            "depth_max": max(depth)}


# ---------------------------------------------------------------------------
# 3. Run
# ---------------------------------------------------------------------------

def run_on(backend, shots, seed=None):
    cases = all_cases()
    circuits = [build_circuit(s, e) for s, e in cases]
    transpiled = transpile(circuits, backend=backend, optimization_level=3,
                           layout_method="sabre", seed_transpiler=2026)
    stats = circuit_stats(transpiled)
    print(f"compiled for {backend.name}: up to {stats['two_qubit_gates_max']} "
          f"two-qubit gates, depth up to {stats['depth_max']}")
    kwargs = {"shots": shots}
    if seed is not None:
        kwargs["seed_simulator"] = seed
    job = backend.run(transpiled, **kwargs)
    return cases, transpiled, stats, job


def counts_from(result, n):
    return [{k: int(v) for k, v in result.get_counts(i).items()} for i in range(n)]


def cmd_simulate(args):
    from qiskit_aer import AerSimulator
    from iqm.qiskit_iqm import IQMFakeGarnet

    for label, backend, fname in [
        ("ideal simulator", AerSimulator(), "ideal.json"),
        ("noisy simulator (IQMFakeGarnet)", IQMFakeGarnet(), "noisy_fake_garnet.json"),
    ]:
        cases, _, stats, job = run_on(backend, args.shots, seed=2026)
        counts = counts_from(job.result(), len(cases))
        rows = [analyse(s, e, c) for (s, e), c in zip(cases, counts)]
        summarise(rows, label)
        save(fname, {"backend": label, "shots": args.shots, "circuit_stats": stats, "rows": rows})


def get_iqm_backend(args):
    if not os.environ.get("IQM_TOKEN"):
        sys.exit("IQM_TOKEN is not set. See the README in this folder for how to set it.")
    from iqm.qiskit_iqm import IQMProvider
    # IQMProvider reads the token from the IQM_TOKEN environment variable itself.
    provider = IQMProvider(args.server, quantum_computer=args.computer)
    return provider.get_backend()


def finish_hardware(job, cases, meta):
    print("waiting for the results (this can take a while if there is a queue)...")
    result = job.result()
    counts = counts_from(result, len(cases))
    rows = [analyse(s, e, c) for (s, e), c in zip(cases, counts)]
    summarise(rows, f"IQM hardware ({meta.get('computer')})")
    try:
        meta["calibration_set_id"] = str(result.parameters.calibration_set_id)
    except Exception:
        pass
    meta["rows"] = rows
    save("hardware.json", meta)


def cmd_hardware(args):
    backend = get_iqm_backend(args)
    cases, _, stats, job = run_on(backend, args.shots)
    meta = {"backend": "IQM hardware", "computer": args.computer, "server": args.server,
            "shots": args.shots, "circuit_stats": stats, "job_id": str(job.job_id()),
            "submitted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    # Save the job id straight away so the results can be fetched later
    # even if this window is closed.
    save("hardware_job.json", {k: meta[k] for k in ("job_id", "computer", "server", "shots",
                                                    "submitted_utc")})
    print(f"job submitted: {meta['job_id']}")
    finish_hardware(job, cases, meta)


def cmd_fetch(args):
    backend = get_iqm_backend(args)
    job = backend.retrieve_job(args.job_id)
    meta = {"backend": "IQM hardware", "computer": args.computer, "server": args.server,
            "job_id": args.job_id}
    finish_hardware(job, all_cases(), meta)


def cmd_plot(args):
    import plot_level1_iqm
    plot_level1_iqm.main(RESULTS_DIR)


def cmd_draw(args):
    print(build_circuit(args.state, args.error).draw(output="text"))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--server", default=os.environ.get("IQM_SERVER_URL", DEFAULT_SERVER))
    p.add_argument("--computer", default=os.environ.get("IQM_QUANTUM_COMPUTER", DEFAULT_COMPUTER),
                   help="IQM computer name, e.g. garnet (default), emerald")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, default_shots in [("simulate", cmd_simulate, 4000),
                                    ("hardware", cmd_hardware, 1000)]:
        sp = sub.add_parser(name)
        sp.add_argument("--shots", type=int, default=default_shots)
        sp.set_defaults(fn=fn)
    sp = sub.add_parser("fetch")
    sp.add_argument("job_id")
    sp.set_defaults(fn=cmd_fetch)
    sub.add_parser("plot").set_defaults(fn=cmd_plot)
    sp = sub.add_parser("draw", help="print one circuit, e.g. draw '|+>' X1")
    sp.add_argument("state", nargs="?", default="|+>")
    sp.add_argument("error", nargs="?", default="X0")
    sp.set_defaults(fn=cmd_draw)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
