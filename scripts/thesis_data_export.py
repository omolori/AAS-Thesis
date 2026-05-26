"""Pull all run data from Supabase and compute Chapter 7 metrics."""
import json, math, sys
import numpy as np
from collections import defaultdict

DATABASE_URL = (
    "postgresql://postgres.ovzejfttavkcoqbugsii:AASsimdatabas"
    "@aws-1-eu-west-3.pooler.supabase.com:5432/postgres"
)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    sys.exit("Run:  pip install psycopg2-binary")

print("Connecting to Supabase...")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── 1. Run inventory ────────────────────────────────────────────────────────
cur.execute("SELECT pipeline, COUNT(*) AS n FROM runs GROUP BY pipeline ORDER BY pipeline")
print("\n=== RUNS PER PIPELINE ===")
pipeline_counts = {}
for r in cur.fetchall():
    pipeline_counts[r["pipeline"]] = r["n"]
    print(f"  {r['pipeline']}: {r['n']}")

# ── 2. Cycle times ──────────────────────────────────────────────────────────
cur.execute("SELECT pipeline, run_id, started_at_unix, ended_at_unix FROM runs ORDER BY pipeline, started_at_unix")
all_runs = cur.fetchall()
durations = defaultdict(list)
run_ids_by_pipeline = defaultdict(list)
for r in all_runs:
    d = r["ended_at_unix"] - r["started_at_unix"]
    durations[r["pipeline"]].append(d)
    run_ids_by_pipeline[r["pipeline"]].append(r["run_id"])

print("\n=== CYCLE TIMES (total run duration, 3 cycles) ===")
import statistics as st
for p in sorted(durations):
    d = durations[p]
    mean = st.mean(d)
    std = st.stdev(d) if len(d) > 1 else 0.0
    print(f"  {p}: n={len(d)}  mean={mean:.2f}s  std={std:.2f}s  "
          f"min={min(d):.2f}s  max={max(d):.2f}s")

# ── 3. Load samples for a run ───────────────────────────────────────────────
def load_samples(run_id):
    cur.execute("""
        SELECT wall_time, actual_q_json, actual_tcp_pose_json, actual_current_json
        FROM samples WHERE run_id=%s ORDER BY sample_idx
    """, (run_id,))
    rows = cur.fetchall()
    if not rows:
        return None, None, None, None
    times, joints, tcps, currents = [], [], [], []
    for r in rows:
        times.append(r["wall_time"])
        joints.append(json.loads(r["actual_q_json"]))
        tcps.append(json.loads(r["actual_tcp_pose_json"]))
        if r["actual_current_json"]:
            currents.append(json.loads(r["actual_current_json"]))
    t = np.array(times); t -= t[0]
    return t, np.array(joints), np.array(tcps), np.array(currents) if currents else None

def rmse_joints(t_a, q_a, t_b, q_b):
    t_end = min(t_a[-1], t_b[-1])
    ma, mb = t_a <= t_end, t_b <= t_end
    rmse = []
    for j in range(6):
        b_i = np.interp(t_a[ma], t_b[mb], q_b[mb, j])
        rmse.append(math.sqrt(np.mean((q_a[ma, j] - b_i) ** 2)))
    return rmse

def tcp_dev_mm(t_a, tcp_a, t_b, tcp_b):
    t_end = min(t_a[-1], t_b[-1])
    ma, mb = t_a <= t_end, t_b <= t_end
    xyz_b = np.stack([np.interp(t_a[ma], t_b[mb], tcp_b[mb, d]) for d in range(3)], axis=1)
    diff = np.linalg.norm(tcp_a[ma, :3] - xyz_b, axis=1)
    return float(np.mean(diff)) * 1000, float(np.max(diff)) * 1000

def rms_current(currents):
    if currents is None: return [None]*6
    return [math.sqrt(np.mean(currents[:, j] ** 2)) for j in range(6)]

# ── 4. Pick representative runs ─────────────────────────────────────────────
# Use the most recent run of each pipeline as representative
def latest_run(pipeline):
    cur.execute(
        "SELECT run_id FROM runs WHERE pipeline=%s ORDER BY started_at_unix DESC LIMIT 1",
        (pipeline,)
    )
    r = cur.fetchone()
    return r["run_id"] if r else None

real_id    = latest_run("real")
no_aas_id  = latest_run("sim_no_aas")
aas_id     = latest_run("sim_aas")

print(f"\n=== REPRESENTATIVE RUNS ===")
print(f"  real:       {real_id}")
print(f"  sim_no_aas: {no_aas_id}")
print(f"  sim_aas:    {aas_id}")

# ── 5. Load samples ──────────────────────────────────────────────────────────
print("\nLoading samples (may take a moment)...")
t_r, q_r, tcp_r, cur_r     = load_samples(real_id)
t_n, q_n, tcp_n, cur_n     = load_samples(no_aas_id)
t_a, q_a, tcp_a, cur_a     = load_samples(aas_id)

for label, t in [("real", t_r), ("sim_no_aas", t_n), ("sim_aas", t_a)]:
    if t is not None:
        print(f"  {label}: {len(t)} samples, {t[-1]:.1f}s")
    else:
        print(f"  {label}: NO SAMPLES FOUND")

# ── 6. RMSE: real vs sim_no_aas ──────────────────────────────────────────────
print("\n=== JOINT RMSE: real vs sim_no_aas (rad / deg) ===")
if t_r is not None and t_n is not None:
    rmse_no = rmse_joints(t_r, q_r, t_n, q_n)
    for j, v in enumerate(rmse_no):
        print(f"  J{j+1}: {v:.4f} rad  ({math.degrees(v):.3f} deg)")
    tcp_no_mean, tcp_no_max = tcp_dev_mm(t_r, tcp_r, t_n, tcp_n)
    print(f"  TCP mean dev: {tcp_no_mean:.2f} mm   max: {tcp_no_max:.2f} mm")
else:
    print("  MISSING DATA")

# ── 7. RMSE: real vs sim_aas ─────────────────────────────────────────────────
print("\n=== JOINT RMSE: real vs sim_aas (rad / deg) ===")
if t_r is not None and t_a is not None:
    rmse_aas = rmse_joints(t_r, q_r, t_a, q_a)
    for j, v in enumerate(rmse_aas):
        print(f"  J{j+1}: {v:.4f} rad  ({math.degrees(v):.3f} deg)")
    tcp_aas_mean, tcp_aas_max = tcp_dev_mm(t_r, tcp_r, t_a, tcp_a)
    print(f"  TCP mean dev: {tcp_aas_mean:.2f} mm   max: {tcp_aas_max:.2f} mm")
else:
    print("  MISSING DATA")

# ── 8. Improvement summary ───────────────────────────────────────────────────
if t_r is not None and t_n is not None and t_a is not None:
    print("\n=== IMPROVEMENT: sim_aas vs sim_no_aas (relative to real) ===")
    for j in range(6):
        imp = (rmse_no[j] - rmse_aas[j]) / rmse_no[j] * 100 if rmse_no[j] > 0 else 0
        print(f"  J{j+1}: {imp:+.1f}%  ({math.degrees(rmse_no[j]):.3f} → {math.degrees(rmse_aas[j]):.3f} deg)")
    tcp_imp = (tcp_no_mean - tcp_aas_mean) / tcp_no_mean * 100
    print(f"  TCP: {tcp_imp:+.1f}%  ({tcp_no_mean:.2f} → {tcp_aas_mean:.2f} mm)")

# ── 9. RMS current ───────────────────────────────────────────────────────────
print("\n=== RMS CURRENT per joint (A) ===")
for label, c in [("real", cur_r), ("sim_no_aas", cur_n), ("sim_aas", cur_a)]:
    rms = rms_current(c)
    vals = "  ".join(f"J{j+1}:{v:.3f}" for j, v in enumerate(rms) if v is not None)
    print(f"  {label:12s}: {vals}")

# ── 10. All run durations for table ─────────────────────────────────────────
print("\n=== ALL INDIVIDUAL RUN DURATIONS ===")
for r in all_runs:
    d = r["ended_at_unix"] - r["started_at_unix"]
    print(f"  {r['pipeline']:12s}  {r['run_id'][:8]}  {d:.2f}s")

conn.close()
print("\nDone.")
