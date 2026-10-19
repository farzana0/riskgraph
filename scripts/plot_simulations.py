"""Render the simulation summary figure. Requires requirements-simulation.txt."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="docs/examples/simulations.json")
    parser.add_argument("--output", default="docs/images/simulation-summary.png")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text())
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "axes.titlepad": 13,
                         "figure.facecolor": "#fafaf8", "axes.facecolor": "#fafaf8"})
    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    teal, orange, blue, purple = "#287b70", "#d66b3e", "#3777ac", "#8c629c"
    ax = axes[0, 0]
    policy = data["policy"]
    counts = [policy["harmful_proposals"]-policy["harmful_allowed"], policy["harmful_allowed"]]
    ax.barh(["Blocked", "Allowed"], counts, color=[teal, orange], height=.55)
    ax.invert_yaxis()
    ax.set_xlim(0, max(counts)*1.22)
    for i, value in enumerate(counts):
        ax.text(value+max(counts)*.025, i, f"{value:,}", va="center", fontweight="bold")
    ax.set_title("Harmful proposals in the policy stress test", loc="left")
    ax.set_xlabel(f"Count · {policy['proposals']:,} proposals sampled in total")
    ax.text(0, -.24, f"{policy['policy_disagreements']} policy disagreements; {policy['malformed_rejected']}/{policy['malformed_total']} malformed payloads rejected.", transform=ax.transAxes, fontsize=9)

    ax = axes[0, 1]
    labels = [("rare_large", "Rare large losses", orange), ("mixed_severity", "Mixed severity", blue),
              ("frequent_small", "Frequent small losses", purple), ("off_grid_severity", "Off-grid severity", teal)]
    for scenario, label, color in labels:
        rows = [r for r in data["estimator"] if r["scenario"] == scenario]
        ax.plot([r["n"] for r in rows], [100*r["binned_mean_interval_coverage"]["rate"] for r in rows],
                marker="o", markersize=4, label=label, color=color)
    ax.axhline(95, color="#777777", ls="--", lw=1)
    ax.set_xscale("log")
    ax.set_xticks([3, 10, 20, 40, 100, 200], ["3", "10", "20", "40", "100", "200"])
    ax.set_ylim(65, 103)
    ax.set_ylabel("Intervals containing true mean binned loss (%)")
    ax.set_xlabel(f"Cases per dataset · {data['estimator'][0]['repetitions']:,} datasets per point")
    ax.set_title("Bayesian interval coverage depends on workload", loc="left")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="lower right")
    ax.text(0, -.24, "Dashed: 95% reference. Credible intervals have no universal coverage guarantee.", transform=ax.transAxes, fontsize=8)

    ax = axes[1, 0]
    rows = [r for r in data["sequential"]["alarms"] if r["scenario"] in ["null_010", "elevated_015", "elevated_025", "elevated_050"]]
    rates = np.array([r["crossing"]["rate"]*100 for r in rows])
    intervals = np.array([r["crossing"]["ci95"] for r in rows])*100
    positions = np.arange(len(rows))
    ax.bar(positions, rates, color=["#8b9694", orange, teal, blue], width=.6,
           yerr=np.vstack([rates-intervals[:, 0], intervals[:, 1]-rates]), capsize=3)
    for i, rate in enumerate(rates):
        ax.text(i, rate+4, f"{rate:.1f}%", ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(positions, ["10%\n(null)", "15%", "25%", "50%"])
    ax.set_ylim(0, 115)
    ax.set_ylabel("Runs that trigger the alarm (%)")
    ax.set_xlabel("True harmful-proposal probability")
    ax.set_title("Alarm detection within 500 decisions", loc="left")
    ax.text(0, -.42, f"{rows[0]['crossing']['total']:,} trajectories per rate; error bars: 95% Monte Carlo intervals.\nThe 10% column is the false-alarm rate; remaining columns are detection rates.", transform=ax.transAxes, fontsize=8)

    ax = axes[1, 1]
    rows = [r for r in data["sequential"]["loss_bounds"] if r["scenario"] == "iid_bounded"]
    actual = np.array([r["true_mean_usd"] for r in rows])
    upper = np.array([r["final_upper_median_usd"] for r in rows])
    positions = np.arange(len(rows))
    ax.bar(positions-.17, actual, width=.34, color=teal, label="True mean")
    ax.bar(positions+.17, upper, width=.34, color="#b5c9c4", label="Median upper bound")
    ax.set_xticks(positions, ["1%", "10%", "50%"])
    ax.set_ylabel("Loss per decision (USD)")
    ax.set_xlabel("Harm probability · each positive loss is $1,000")
    ax.set_title("Valid upper bounds remain conservative", loc="left")
    ax.legend(frameon=False, fontsize=9)
    correlated = next(r for r in data["sequential"]["loss_bounds"] if r["scenario"] == "perfectly_correlated_stress")
    misses = sum(r["ever_miss"]["count"] for r in rows)
    total = sum(r["ever_miss"]["total"] for r in rows)
    ax.text(0, -.42, f"At 500 decisions: {misses:,} misses across {total:,} independent trajectories.\nPerfectly correlated stress: {100*correlated['ever_miss']['rate']:.1f}% miss rate; assumptions are violated.", transform=ax.transAxes, fontsize=8)

    fig.suptitle("RiskGraph · Synthetic simulation evaluation", x=.055, y=.99, ha="left", fontsize=19, fontweight="bold")
    fig.text(.055, .944, "Policy checks held in the sampled stress test; interval coverage varies by workload and moderate-rate alarm detection is weak.", fontsize=10, color="#46524e")
    fig.subplots_adjust(left=.075, right=.98, top=.86, bottom=.21, hspace=.7, wspace=.3)
    datasets = sum(r["repetitions"] for r in data["estimator"])
    trajectories = sum(r["ever_miss"]["total"] for r in data["sequential"]["loss_bounds"])+sum(r["crossing"]["total"] for r in data["sequential"]["alarms"])
    fig.text(.055, .025, f"Seed {data['seed']} · {datasets:,} estimator datasets · {trajectories:,} monitoring trajectories · Offline fixture results are separate from Claude performance.", fontsize=8, color="#59645f")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=170)
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
