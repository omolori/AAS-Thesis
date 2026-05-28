"""Compute motion-onset-aligned kinematic RMSE and TCP deviation from Supabase.

Run once to get corrected thesis table values.
"""
import json, math
import numpy as np
import psycopg2, psycopg2.extras

DATABASE_URL = (
    "postgresql://postgres.ovzejfttavkcoqbugsii:AASsimdatabas"
    "@aws-1-eu-west-3.pooler.supabase.com:5432/postgres"
)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def load_samples(run_id):
    cur.execute("""
        SELECT wall_time, actual_q_json, actual_tcp_pose_json, actual_current_json
        FROM samples WHERE run_id=%s ORDER BY sample_idx
    """, (run_id,))
    rows = cur.fetchall()
    t, q, tcp, c = [], [], [], []
    for r in rows:
        t.append(r["wall_time"])
        q.append(json.loads(r["actual_q_json"]))
        tcp.append(json.loads(r["actual_tcp_pose_json"]))
        if r["actual_current_json"]:
            c.append(json.loads(r["actual_current_json"]))
    t = np.array(t); t -= t[0]
    return t, np.array(q), np.array(tcp), np.array(c) if c else None


# Canonical home position and tolerance (matches pick_and_place_trajectory waypoints[0])
HOME_Q   = np.array([-1.4561, -1.6660, -0.2774, -2.0748, 1.6275, -0.1098])
HOME_TOL = 0.05  # radians


def _near_home(qi):
    return bool(np.all(np.abs(qi - HOME_Q) < HOME_TOL))


def find_onset(t, q):
    """First departure from the canonical home position after reaching it.

    - Runs starting at home: returns first home departure (cycle 1 start).
    - Runs starting away from home (sim_aas boot pose): waits until home is
      reached, then returns the first departure from there.
    """
    state = "AT_HOME" if _near_home(q[0]) else "MOVING"
    for i in range(len(t)):
        at_h = _near_home(q[i])
        if state == "MOVING" and at_h:
            state = "AT_HOME"
        elif state == "AT_HOME" and not at_h:
            return float(t[i])
    return float(t[0])


def aligned_rmse(t_a, q_a, t_b, q_b, label):
    onset_a = find_onset(t_a, q_a)
    onset_b = find_onset(t_b, q_b)
    print(f"  [{label}]  onset_a={onset_a:.2f}s  onset_b={onset_b:.2f}s  "
          f"phase_offset={onset_b - onset_a:.2f}s")
    ma = t_a >= onset_a;  mb = t_b >= onset_b
    t_a2, q_a2 = t_a[ma] - onset_a, q_a[ma]
    t_b2, q_b2 = t_b[mb] - onset_b, q_b[mb]
    t_end = min(t_a2[-1], t_b2[-1])
    ka, kb = t_a2 <= t_end, t_b2 <= t_end
    print(f"  [{label}]  aligned window 0..{t_end:.1f}s, "
          f"pts_a={int(ka.sum())}  pts_b={int(kb.sum())}")
    rmse = []
    for j in range(6):
        interp = np.interp(t_a2[ka], t_b2[kb], q_b2[kb, j])
        rmse.append(math.sqrt(np.mean((q_a2[ka, j] - interp) ** 2)))
    return [math.degrees(r) for r in rmse]


def aligned_tcp(t_a, q_a, tcp_a, t_b, q_b, tcp_b, label):
    onset_a = find_onset(t_a, q_a)
    onset_b = find_onset(t_b, q_b)
    ma = t_a >= onset_a;  mb = t_b >= onset_b
    t_a2, tcp_a2 = t_a[ma] - onset_a, tcp_a[ma]
    t_b2, tcp_b2 = t_b[mb] - onset_b, tcp_b[mb]
    t_end = min(t_a2[-1], t_b2[-1])
    ka, kb = t_a2 <= t_end, t_b2 <= t_end
    t_ref = t_a2[ka]
    xyz_b = np.stack([np.interp(t_ref, t_b2[kb], tcp_b2[kb, d]) for d in range(3)], axis=1)
    dev = np.linalg.norm(tcp_a2[ka, :3] - xyz_b, axis=1) * 1000   # mm
    rms  = float(np.sqrt(np.mean(dev ** 2)))
    mean = float(np.mean(dev))
    mx   = float(dev.max())
    print(f"  [{label}]  mean={mean:.2f}mm  rms={rms:.2f}mm  max={mx:.2f}mm")
    return t_ref, dev


# ── resolve run IDs ──────────────────────────────────────────────────────────
cur.execute("SELECT run_id FROM runs WHERE pipeline='real'")
real_ids = {r["run_id"][:8]: r["run_id"] for r in cur.fetchall()}
cur.execute("SELECT run_id FROM runs WHERE pipeline='sim_no_aas'")
no_aas_ids = {r["run_id"][:8]: r["run_id"] for r in cur.fetchall()}
cur.execute("SELECT run_id FROM runs WHERE pipeline='sim_aas'")
aas_ids = {r["run_id"][:8]: r["run_id"] for r in cur.fetchall()}

real_rep    = real_ids["591b7473"]
no_aas_rep  = no_aas_ids["db4c6d73"]
aas_rep     = aas_ids["7b8c4a8e"]

print("Loading samples (may take ~60s)...")
t_r, q_r, tcp_r, c_r = load_samples(real_rep)
t_n, q_n, tcp_n, c_n = load_samples(no_aas_rep)
t_a, q_a, tcp_a, c_a = load_samples(aas_rep)
print(f"  real:       {len(t_r)} pts, {t_r[-1]:.2f}s")
print(f"  sim_no_aas: {len(t_n)} pts, {t_n[-1]:.2f}s")
print(f"  sim_aas:    {len(t_a)} pts, {t_a[-1]:.2f}s")
print()

# ── joint RMSE ───────────────────────────────────────────────────────────────
print("=== Joint RMSE (motion-onset aligned) ===")
rmse_no  = aligned_rmse(t_r, q_r, t_n, q_n, "real vs no_aas")
rmse_aas = aligned_rmse(t_r, q_r, t_a, q_a, "real vs aas   ")
joint_labels = ["J1(Base)", "J2(Shldr)", "J3(Elbow)", "J4(Wrt1)", "J5(Wrt2)", "J6(Wrt3)"]
print()
print(f"  {'':12s} {'no_aas':>10s} {'aas':>10s}  {'delta':>10s}")
for j, lbl in enumerate(joint_labels):
    delta = rmse_aas[j] - rmse_no[j]
    print(f"  {lbl:12s} {rmse_no[j]:10.2f} {rmse_aas[j]:10.2f}  {delta:+10.2f}")
combined_no  = math.sqrt(sum(r**2 for r in rmse_no)  / 6)
combined_aas = math.sqrt(sum(r**2 for r in rmse_aas) / 6)
print(f"  {'Combined':12s} {combined_no:10.2f} {combined_aas:10.2f}  {combined_aas - combined_no:+10.2f}")
print()

# ── TCP deviation ─────────────────────────────────────────────────────────────
print("=== TCP deviation (motion-onset aligned) ===")
aligned_tcp(t_r, q_r, tcp_r, t_n, q_n, tcp_n, "real vs no_aas")
aligned_tcp(t_r, q_r, tcp_r, t_a, q_a, tcp_a, "real vs aas   ")

conn.close()
