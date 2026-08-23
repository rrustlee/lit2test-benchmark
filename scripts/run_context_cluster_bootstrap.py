import json
import math
import random
from collections import defaultdict, Counter
from pathlib import Path

SEED = 20260729
N_REPLICATES = 10000
MODELS = ["GPT 5.2", "Claude-Sonnet-4.6", "GLM-5", "DeepSeek-V3.2"]

DATA_PATH = Path(__file__).resolve().parent.parent / "results/main/corrected_folded_pairs.jsonl"
PAIR_RESULTS_PATH = Path(__file__).resolve().parent.parent / "results/main/lit2test_corrected_gemini_main_results.json"
OUT_PATH = Path(__file__).resolve().parent / "cluster_bootstrap_rerun.json"


def load_data():
    with open(DATA_PATH) as f:
        return [json.loads(line) for line in f]


def build_context_groups(records):
    groups = defaultdict(list)
    for r in records:
        groups[r["context_id"]].append(r)
    return groups


def pairs_to_wins(pairs):
    wins = defaultdict(float)
    for p in pairs:
        m1, m2 = p["model_pair"]
        w = p["folded_winner"]
        if w == "consistency_tie":
            wins[(m1, m2)] += 0.5
            wins[(m2, m1)] += 0.5
        else:
            wins[(w, m1 if w == m2 else m2)] += 1.0
    return wins


def fit_bt(wins, n_iter=200):
    s = {m: 1.0 for m in MODELS}
    for _ in range(n_iter):
        new_s = {}
        for m in MODELS:
            w = sum(wins.get((m, o), 0) for o in MODELS if o != m)
            d = sum((wins.get((m, o), 0) + wins.get((o, m), 0)) / (s[m] + s[o])
                    for o in MODELS if o != m)
            new_s[m] = w / d if d > 0 else 1e-6
        geo = 1.0
        for v in new_s.values():
            geo *= v
        geo = geo ** (1.0 / len(MODELS))
        s = {m: v / geo for m, v in new_s.items()}
    logs = {m: math.log(v) for m, v in s.items()}
    mean_log = sum(logs.values()) / len(logs)
    return {m: v - mean_log for m, v in logs.items()}


def rank_models(abilities):
    sorted_m = sorted(MODELS, key=lambda m: -abilities[m])
    ranks = {}
    for i, m in enumerate(sorted_m):
        ranks[m] = i + 1
    return ranks, " > ".join(sorted_m)


def run_bootstrap(context_groups, n_replicates, seed):
    rng = random.Random(seed)
    context_ids = sorted(context_groups.keys())
    n_ctx = len(context_ids)

    all_abilities = []
    all_ranks = []
    ranking_counter = Counter()

    for _ in range(n_replicates):
        sampled_ids = rng.choices(context_ids, k=n_ctx)
        sampled_pairs = []
        for cid in sampled_ids:
            sampled_pairs.extend(context_groups[cid])
        wins = pairs_to_wins(sampled_pairs)
        abilities = fit_bt(wins)
        ranks, ranking_str = rank_models(abilities)
        all_abilities.append(abilities)
        all_ranks.append(ranks)
        ranking_counter[ranking_str] += 1

    ci95 = {}
    for m in MODELS:
        vals = sorted(a[m] for a in all_abilities)
        lo = vals[int(n_replicates * 0.025)]
        hi = vals[int(n_replicates * 0.975)]
        ci95[m] = [lo, hi]

    rank_dist = {}
    for m in MODELS:
        dist = Counter(r[m] for r in all_ranks)
        rank_dist[m] = {f"rank{k}": dist.get(k, 0) for k in range(1, len(MODELS) + 1)}

    modal_ranking = ranking_counter.most_common(1)[0]
    modal_ranking_str = modal_ranking[0]
    modal_ranking_frac = modal_ranking[1] / n_replicates

    top5 = {k: v for k, v in ranking_counter.most_common(5)}

    return ci95, rank_dist, modal_ranking_str, modal_ranking_frac, top5


def main():
    records = load_data()
    context_groups = build_context_groups(records)
    assert len(context_groups) == 200, f"Expected 200 contexts, got {len(context_groups)}"
    for cid, pairs in context_groups.items():
        assert len(pairs) == 6, f"Context {cid} has {len(pairs)} pairs, expected 6"

    print(f"Loaded {len(records)} pairs, {len(context_groups)} contexts")
    print(f"Running {N_REPLICATES} context-cluster bootstrap replicates (seed={SEED})...")

    ci95_cluster, rank_dist, modal_ranking, modal_frac, top5 = run_bootstrap(
        context_groups, N_REPLICATES, SEED)

    with open(PAIR_RESULTS_PATH) as f:
        pair_results = json.load(f)
    ci95_pair = pair_results["corrected"]["bt_case_bootstrap"]["ci95_centered_log_ability"]
    pair_modal_frac = pair_results["corrected"]["bt_case_bootstrap"]["modal_ranking_fraction"]

    ci_comparison = {}
    for m in MODELS:
        pw = ci95_pair[m][1] - ci95_pair[m][0]
        cw = ci95_cluster[m][1] - ci95_cluster[m][0]
        ci_comparison[m] = {
            "pair_ci_width": round(pw, 6),
            "cluster_ci_width": round(cw, 6),
            "cluster_wider_pct": round((cw / pw - 1) * 100, 1)
        }

    result = {
        "method": "Context-cluster bootstrap: resample 200 context_ids with replacement, "
                  "include all 6 pairs per context. Bradley-Terry MM with ties=0.5/0.5. "
                  "Centered log-abilities.",
        "seed": SEED,
        "n_replicates": N_REPLICATES,
        "n_contexts": len(context_groups),
        "n_pairs": len(records),
        "pairs_per_context": 6,
        "ci95_centered_log_ability": {
            "cluster_bootstrap": {m: [round(v, 6) for v in ci95_cluster[m]] for m in MODELS},
            "pair_bootstrap_reference": {m: [round(v, 6) for v in ci95_pair[m]] for m in MODELS}
        },
        "rank_distribution": rank_dist,
        "ranking_distribution_top5": top5,
        "modal_full_ranking": modal_ranking,
        "modal_ranking_fraction": {
            "cluster_bootstrap": round(modal_frac, 4),
            "pair_bootstrap_reference": pair_modal_frac
        },
        "pair_vs_cluster_ci_width_ratio": ci_comparison
    }

    with open(OUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Results written to {OUT_PATH}")

    print("\n=== Summary ===")
    print(f"Modal ranking (cluster):  {modal_ranking}")
    print(f"Modal ranking fraction:   cluster={modal_frac:.4f}  pair={pair_modal_frac}")
    print(f"\nCI width comparison (cluster vs pair):")
    for m in MODELS:
        c = ci_comparison[m]
        print(f"  {m:25s}: pair={c['pair_ci_width']:.4f}  cluster={c['cluster_ci_width']:.4f}  "
              f"wider by {c['cluster_wider_pct']:+.1f}%")


if __name__ == "__main__":
    main()
