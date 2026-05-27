"""Generate all Chapter 8 evaluation figures for the thesis."""
import json, math, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import psycopg2, psycopg2.extras

DATABASE_URL = (
    "postgresql://postgres.ovzejfttavkcoqbugsii:AASsimdatabas"
    "@aws-1-eu-west-3.pooler.supabase.com:5432/postgres"
)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "thesis_figures")
os.makedirs(OUT_DIR, exist_ok=True)

# Colour palette consistent with the dashboard
C_REAL   = "#4A9EFF"
C_NO_AAS = "#FF6B6B"
C_AAS    = "#51CF66"

PIPELINE_LABELS = {
    "real":       "Real UR3",
    "sim_no_aas": "Sim (no AAS)",
    "sim_aas":    "Sim (AAS)",
}

print("Connecting to Supabase...")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── helpers ─────────────────────────────────────────────────────────────────

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

def align_and_rmse(t_a, q_a, t_b, q_b):
    t_end = min(t_a[-1], t_b[-1])
    ma, mb = t_a <= t_end, t_b <= t_end
    rmse = []
    for j in range(6):
        b_i = np.interp(t_a[ma], t_b[mb], q_b[mb, j])
        rmse.append(math.sqrt(np.mean((q_a[ma, j] - b_i) ** 2)))
    return [math.degrees(r) for r in rmse]

def align_and_tcp_dev(t_a, tcp_a, t_b, tcp_b):
    t_end = min(t_a[-1], t_b[-1])
    ma, mb = t_a <= t_end, t_b <= t_end
    t_ref = t_a[ma]
    xyz_b = np.stack([np.interp(t_ref, t_b[mb], tcp_b[mb, d]) for d in range(3)], axis=1)
    dev = np.linalg.norm(tcp_a[ma, :3] - xyz_b, axis=1) * 1000  # mm
    return t_ref, dev

def rms_current(currents):
    return [math.sqrt(np.mean(currents[:, j] ** 2)) for j in range(6)]

def save(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")

# ── load runs ────────────────────────────────────────────────────────────────
cur.execute("SELECT run_id, pipeline, started_at_unix, ended_at_unix FROM runs ORDER BY pipeline, started_at_unix")
all_runs = cur.fetchall()

REAL_IDS   = ["17bdd86a", "ad686ab3", "f1fc0d71", "52c26cbc", "4430d0da", "591b7473"]
NO_AAS_ID  = "db4c6d73"
AAS_ID     = "7b8c4a8e"  # mass=1.2 kg, basyx live, evaluation run

cur.execute("SELECT run_id FROM runs WHERE pipeline='real'")
real_full_ids = {r["run_id"][:8]: r["run_id"] for r in cur.fetchall()}
cur.execute("SELECT run_id FROM runs WHERE pipeline='sim_no_aas'")
no_aas_full = {r["run_id"][:8]: r["run_id"] for r in cur.fetchall()}
cur.execute("SELECT run_id FROM runs WHERE pipeline='sim_aas'")
aas_full = {r["run_id"][:8]: r["run_id"] for r in cur.fetchall()}

real_rep_id  = real_full_ids["591b7473"]  # representative real run
no_aas_rep_id = no_aas_full[NO_AAS_ID]
aas_rep_id    = aas_full[AAS_ID]

# ── Figure 1: per-cycle duration bar chart ───────────────────────────────────
print("\nFigure 1: cycle time bar chart")

durations = {"real": [], "sim_no_aas": [], "sim_aas": []}
for r in all_runs:
    d = (r["ended_at_unix"] - r["started_at_unix"]) / 3  # per cycle
    if r["pipeline"] == "real" and r["run_id"][:8] in REAL_IDS:
        durations["real"].append(d)
    elif r["pipeline"] == "sim_no_aas" and r["run_id"][:8] in [NO_AAS_ID]:
        durations["sim_no_aas"].append(d)
    elif r["pipeline"] == "sim_aas" and r["run_id"][:8] in [AAS_ID]:
        durations["sim_aas"].append(d)

# All valid sim runs for context
for r in all_runs:
    d = (r["ended_at_unix"] - r["started_at_unix"]) / 3
    if r["pipeline"] == "sim_no_aas" and 50 <= (d*3) <= 65:
        durations["sim_no_aas"].append(d)
    elif r["pipeline"] == "sim_aas" and 50 <= (d*3) <= 65:
        durations["sim_aas"].append(d)

fig, ax = plt.subplots(figsize=(7, 4))
pipelines = ["real", "sim_no_aas", "sim_aas"]
colors    = [C_REAL, C_NO_AAS, C_AAS]
x = np.arange(len(pipelines))
means = [np.mean(durations[p]) for p in pipelines]
stds  = [np.std(durations[p]) if len(durations[p]) > 1 else 0 for p in pipelines]

bars = ax.bar(x, means, yerr=stds, capsize=5, color=colors, alpha=0.85,
              edgecolor="white", linewidth=0.8, error_kw={"elinewidth": 1.5})
ax.set_xticks(x)
ax.set_xticklabels([PIPELINE_LABELS[p] for p in pipelines], fontsize=11)
ax.set_ylabel("Per-cycle duration (s)", fontsize=11)
ax.set_title("Per-cycle execution time by pipeline", fontsize=12, fontweight="bold")
ax.set_ylim(0, max(means) * 1.3)
for bar, mean, std in zip(bars, means, stds):
    ax.text(bar.get_x() + bar.get_width()/2, mean + std + 0.5,
            f"{mean:.1f}s", ha="center", va="bottom", fontsize=10, fontweight="bold")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
save(fig, "fig8_cycle_time_bar.pdf")

# ── Figure 2: joint RMSE grouped bar chart ───────────────────────────────────
print("Figure 2: joint RMSE grouped bar chart")
print("  Loading samples (this may take 30-60 seconds)...")

t_r, q_r, tcp_r, cur_r = load_samples(real_rep_id)
t_n, q_n, tcp_n, cur_n = load_samples(no_aas_rep_id)
t_a, q_a, tcp_a, cur_a = load_samples(aas_rep_id)

rmse_no  = align_and_rmse(t_r, q_r, t_n, q_n)
rmse_aas = align_and_rmse(t_r, q_r, t_a, q_a)

joint_labels = ["J1\nBase", "J2\nShoulder", "J3\nElbow",
                "J4\nWrist 1", "J5\nWrist 2", "J6\nWrist 3"]
x = np.arange(6)
w = 0.35

fig, ax = plt.subplots(figsize=(9, 4.5))
b1 = ax.bar(x - w/2, rmse_no,  w, label="Sim (no AAS)", color=C_NO_AAS, alpha=0.85, edgecolor="white")
b2 = ax.bar(x + w/2, rmse_aas, w, label="Sim (AAS)",    color=C_AAS,    alpha=0.85, edgecolor="white")
ax.set_xticks(x)
ax.set_xticklabels(joint_labels, fontsize=10)
ax.set_ylabel("RMSE vs real robot (degrees)", fontsize=11)
ax.set_title("Joint position RMSE: simulation pipelines vs real robot", fontsize=12, fontweight="bold")
ax.legend(fontsize=10, framealpha=0.4)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
save(fig, "fig8_joint_rmse_bar.pdf")

# ── Figure 3: TCP deviation time series ──────────────────────────────────────
print("Figure 3: TCP deviation time series")

t_no, dev_no   = align_and_tcp_dev(t_r, tcp_r, t_n, tcp_n)
t_aa, dev_aa   = align_and_tcp_dev(t_r, tcp_r, t_a, tcp_a)

fig, ax = plt.subplots(figsize=(9, 4))
ax.fill_between(t_no, dev_no, alpha=0.35, color=C_NO_AAS)
ax.plot(t_no, dev_no, color=C_NO_AAS, linewidth=1.2, label=f"real vs sim_no_aas  (mean {np.mean(dev_no):.1f} mm)")
ax.fill_between(t_aa, dev_aa, alpha=0.35, color=C_AAS)
ax.plot(t_aa, dev_aa, color=C_AAS, linewidth=1.2, label=f"real vs sim_aas  (mean {np.mean(dev_aa):.1f} mm)")
ax.set_xlabel("Elapsed time (s)", fontsize=11)
ax.set_ylabel("TCP deviation (mm)", fontsize=11)
ax.set_title("TCP path deviation from real robot over time", fontsize=12, fontweight="bold")
ax.legend(fontsize=10, framealpha=0.4)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(alpha=0.3)
fig.tight_layout()
save(fig, "fig8_tcp_deviation.pdf")

# ── Figure 4: RMS current grouped bar chart ──────────────────────────────────
print("Figure 4: RMS current bar chart")
print("  Loading additional real runs for averaging...")

real_rms_all = []
for short_id in REAL_IDS[:3]:
    full_id = real_full_ids.get(short_id)
    if full_id:
        _, _, _, c = load_samples(full_id)
        if c is not None:
            real_rms_all.append(rms_current(c))

real_rms = np.mean(real_rms_all, axis=0) if real_rms_all else rms_current(cur_r)
no_rms   = rms_current(cur_n) if cur_n is not None else [0]*6
aas_rms  = rms_current(cur_a) if cur_a is not None else [0]*6

x = np.arange(6)
w = 0.25
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.bar(x - w,   real_rms, w, label="Real UR3",      color=C_REAL,   alpha=0.85, edgecolor="white")
ax.bar(x,       no_rms,   w, label="Sim (no AAS)",  color=C_NO_AAS, alpha=0.85, edgecolor="white")
ax.bar(x + w,   aas_rms,  w, label="Sim (AAS)",     color=C_AAS,    alpha=0.85, edgecolor="white")
ax.set_xticks(x)
ax.set_xticklabels(joint_labels, fontsize=10)
ax.set_ylabel("RMS current (A)", fontsize=11)
ax.set_title("RMS joint current by pipeline", fontsize=12, fontweight="bold")
ax.legend(fontsize=10, framealpha=0.4)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
save(fig, "fig8_rms_current_bar.pdf")

conn.close()
print(f"\nAll figures saved to: {os.path.abspath(OUT_DIR)}")
print("Upload these four PDF files to Overleaf under Projekt/Figures/7_Evaluation/")
