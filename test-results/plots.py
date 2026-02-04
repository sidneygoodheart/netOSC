import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
import numpy as np

# -----------------------------
# Global style (PlantUML-like)
# -----------------------------
plt.rcParams.update({
    "font.size": 18,
    "font.family": "sans-serif",
    "axes.linewidth": 1.5,
    "axes.labelsize": 18,
    "axes.titlesize": 18,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16,
    "figure.dpi": 300,
})

# -----------------------------
# Dataset configuration
# -----------------------------
rates = [10, 25, 50, 100, 250, 500]

local_files = {r: Path(f"local{r}.csv") for r in rates}
netosc_files = {r: Path(f"netOSC{r}.csv") for r in rates}

def load_rtt_ms(path):
    df = pd.read_csv(path)
    return df["rtt_seconds"] * 1000.0  # seconds → milliseconds

# -----------------------------
# Load all data
# -----------------------------
local_data = {r: load_rtt_ms(p) for r, p in local_files.items()}
netosc_data = {r: load_rtt_ms(p) for r, p in netosc_files.items()}

# ============================================================
# FIGURE 1 — RTT DISTRIBUTIONS (BOXPLOTS)
# ============================================================
fig1, ax1 = plt.subplots(figsize=(14, 6))

positions_local = np.arange(len(rates)) * 2.0
positions_net = positions_local + 0.7

ax1.boxplot(
    [local_data[r] for r in rates],
    positions=positions_local,
    widths=0.5,
    patch_artist=False,
    showfliers=True,
    medianprops=dict(linewidth=2),
    boxprops=dict(linestyle="-", linewidth=1.5),
    whiskerprops=dict(linestyle="-", linewidth=1.5),
    capprops=dict(linestyle="-", linewidth=1.5),
)

ax1.boxplot(
    [netosc_data[r] for r in rates],
    positions=positions_net,
    widths=0.5,
    patch_artist=False,
    showfliers=True,
    medianprops=dict(linewidth=2),
    boxprops=dict(linestyle="--", linewidth=1.5),
    whiskerprops=dict(linestyle="--", linewidth=1.5),
    capprops=dict(linestyle="--", linewidth=1.5),
)

legend_elements = [
    Line2D([0], [0], color="black", linewidth=1.5, linestyle="-",
           label="Local"),
    Line2D([0], [0], color="black", linewidth=1.5, linestyle="--",
           label="netOSC"),
]

ax1.set_yscale("log")
ax1.set_ylabel("RTT [ms]")
ax1.set_xlabel("Message rate [msg/s]")

ax1.set_xticks(positions_local + 0.35)
ax1.set_xticklabels(rates)

ax1.legend(
    handles=legend_elements,
    loc="upper left",
    frameon=False
)


ax1.grid(True, axis="y", linestyle=":", linewidth=0.8)

fig1.tight_layout()
fig1.savefig("rtt_boxplots.svg")

# ============================================================
# FIGURE 2 — PERCENTILES VS MESSAGE RATE
# ============================================================
def percentiles(data_dict):
    p50 = [np.percentile(data_dict[r], 50) for r in rates]
    p95 = [np.percentile(data_dict[r], 95) for r in rates]
    p99 = [np.percentile(data_dict[r], 99) for r in rates]
    return p50, p95, p99

local_p50, local_p95, local_p99 = percentiles(local_data)
net_p50, net_p95, net_p99 = percentiles(netosc_data)

fig2, ax2 = plt.subplots(figsize=(14, 6))

ax2.plot(rates, local_p50, marker="o", linestyle="-", label="Local P50")
ax2.plot(rates, local_p95, marker="s", linestyle="--", label="Local P95")
ax2.plot(rates, local_p99, marker="^", linestyle=":", label="Local P99")

ax2.plot(rates, net_p50, marker="o", linestyle="-", label="netOSC P50")
ax2.plot(rates, net_p95, marker="s", linestyle="--", label="netOSC P95")
ax2.plot(rates, net_p99, marker="^", linestyle=":", label="netOSC P99")

ax2.set_xscale("log")
ax2.set_yscale("log")

ax2.set_xlabel("Message rate [msg/s]")
ax2.set_ylabel("RTT [ms]")

ax2.grid(True, which="both", linestyle=":", linewidth=0.8)
ax2.legend(frameon=False, ncol=2)

fig2.tight_layout()
fig2.savefig("rtt_percentiles.svg")

plt.close("all")
