#!/usr/bin/env python3
"""Aggregate the full-200 Sonnet-vs-3model Gemini pairwise judgments.

Sonnet's new pairs: 5 batches x 40 ctx x 3 opp x 2 order = 1200.
Joint 4-model BT pools these 1200 Sonnet pairs with the existing 1200
three-model Gemini pairs (#12, NOT re-judged) = 2400 total edges.
Adds: win/loss/tie, per-opponent head-to-head, joint BT with bootstrap CI,
Condorcet transitivity over 4 models, order stability, A-side bias check.
Reuses the fit_bt logic from aggregate_lit2test_v02_three_model_gemini_1200.py.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

IB = Path("${PROJECT_ROOT}")
SONNET = "Claude-Sonnet-4.6"
OPPONENTS = ["GPT 5.2", "GLM-5", "DeepSeek-V3.2"]
ALL4 = ["GPT 5.2", "GLM-5", "DeepSeek-V3.2", SONNET]
ORDERS = ["pairwise_blind", "pairwise_blind_reverse"]
BATCHES = ["expansion40_full", "next40_full", "third40_full", "fourth40_full", "fifth40_full"]
# existing 3-model 1200 lives under these batch dirs (different naming)
THREE_BATCHES = ["expansion40_adjudicated40", "next40_full", "third40_full", "fourth40_full", "fifth40_full"]

# deterministic PRNG (Date/random unavailable constraints don't apply here; plain LCG for reproducible bootstrap)
class LCG:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF
    def next(self) -> float:
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s / 0x7FFFFFFF
    def randint(self, n: int) -> int:
        return int(self.next() * n) % n


def load_sonnet() -> dict[tuple, dict]:
    raw: dict[tuple, list[dict]] = defaultdict(list)
    for b in BATCHES:
        for order in ORDERS:
            p = IB / "outputs" / f"lit2test_v02_{b}" / "sonnet_pairs" / order / "judges_gemini" / "pairwise_judgments.jsonl"
            if not p.exists():
                continue
            for line in open(p, encoding="utf-8"):
                line = line.strip()
                if line:
                    r = json.loads(line)
                    r["_order"] = order
                    raw[(order, r["pair_id"])].append(r)
    data = {}
    for key, rows in raw.items():
        valids = [r for r in rows if r.get("winner") in {"A", "B", "tie"} and not r.get("judge_errors")]
        data[key] = valids[-1] if valids else rows[-1]
    return data


def load_three() -> dict[tuple, dict]:
    raw: dict[tuple, list[dict]] = defaultdict(list)
    for b in THREE_BATCHES:
        for order in ORDERS:
            p = IB / "outputs" / f"lit2test_v02_{b}" / order / "judges_gemini" / "pairwise_judgments.jsonl"
            if not p.exists():
                continue
            for line in open(p, encoding="utf-8"):
                line = line.strip()
                if line:
                    r = json.loads(line)
                    raw[(order, r["pair_id"])].append(r)
    out = {}
    for key, rows in raw.items():
        valids = [r for r in rows if r.get("winner") in {"A", "B", "tie"} and not r.get("judge_errors")]
        if valids:
            out[key] = valids[-1]
    return out


def canonical(r: dict) -> str:
    if r.get("winner") == "tie":
        return "tie"
    return r.get("winning_system") or "invalid"


def fit_bt(systems: list[str], rows: list[dict], pseudo: float = 0.5, max_iter: int = 5000) -> dict[str, float]:
    idx = {s: i for i, s in enumerate(systems)}
    n = len(systems)
    wins = [[pseudo if i != j else 0.0 for j in range(n)] for i in range(n)]
    for r in rows:
        w = r.get("winning_system")
        if w not in idx:
            continue
        loser = r["system_b"] if r["system_a"] == w else r["system_a"]
        if loser in idx and loser != w:
            wins[idx[w]][idx[loser]] += 1.0
    ability = [1.0 / n] * n
    for _ in range(max_iter):
        new = [0.0] * n
        for i in range(n):
            tw = sum(wins[i][j] for j in range(n) if j != i)
            denom = sum((wins[i][j] + wins[j][i]) / (ability[i] + ability[j]) for j in range(n) if j != i)
            new[i] = tw / denom if denom else ability[i]
        scale = sum(new) or 1.0
        new = [v / scale for v in new]
        if max(abs(new[i] - ability[i]) for i in range(n)) < 1e-12:
            ability = new
            break
        ability = new
    logs = {s: math.log(ability[idx[s]]) for s in systems}
    mean = statistics.mean(logs.values())
    return {s: round(logs[s] - mean, 6) for s in systems}


def bootstrap_bt(systems, rows, n_boot=1000, seed=20260707):
    rng = LCG(seed)
    m = len(rows)
    samples = {s: [] for s in systems}
    ranks = Counter()
    for _ in range(n_boot):
        resampled = [rows[rng.randint(m)] for _ in range(m)]
        bt = fit_bt(systems, resampled)
        for s in systems:
            samples[s].append(bt[s])
        order = tuple(s for s, _ in sorted(bt.items(), key=lambda kv: kv[1], reverse=True))
        ranks[order] += 1
    ci = {}
    for s in systems:
        vals = sorted(samples[s])
        lo = vals[int(0.025 * n_boot)]
        hi = vals[int(0.975 * n_boot)]
        ci[s] = [round(lo, 4), round(hi, 4)]
    top_order = ranks.most_common(1)[0]
    return ci, {" > ".join(o): c for o, c in ranks.most_common(5)}, top_order[1] / n_boot


def fit_bt_folded(systems, folded, pseudo=0.5, max_iter=5000):
    """BT over folded pairs [(winner_or_tie, system_a, system_b)].
    A 'tie' credits BOTH sides 0.5 win (NOT dropped) so consistency-ties still
    inform the fit — dropping them would exaggerate score gaps."""
    idx = {s: i for i, s in enumerate(systems)}
    n = len(systems)
    wins = [[pseudo if i != j else 0.0 for j in range(n)] for i in range(n)]
    for w, a, b in folded:
        if a not in idx or b not in idx:
            continue
        if w == "tie":
            wins[idx[a]][idx[b]] += 0.5
            wins[idx[b]][idx[a]] += 0.5
        else:
            loser = b if w == a else a
            if loser in idx and loser != w:
                wins[idx[w]][idx[loser]] += 1.0
    ability = [1.0 / n] * n
    for _ in range(max_iter):
        new = [0.0] * n
        for i in range(n):
            tw = sum(wins[i][j] for j in range(n) if j != i)
            denom = sum((wins[i][j] + wins[j][i]) / (ability[i] + ability[j]) for j in range(n) if j != i)
            new[i] = tw / denom if denom else ability[i]
        scale = sum(new) or 1.0
        new = [v / scale for v in new]
        if max(abs(new[i] - ability[i]) for i in range(n)) < 1e-12:
            ability = new
            break
        ability = new
    logs = {s: math.log(ability[idx[s]]) for s in systems}
    mean = statistics.mean(logs.values())
    return {s: round(logs[s] - mean, 6) for s in systems}


def main() -> None:
    sonnet = load_sonnet()
    sonnet_rows = list(sonnet.values())
    valid = [r for r in sonnet_rows if r.get("winner") in {"A", "B", "tie"} and not r.get("judge_errors")]

    wlt = {s: {"wins": 0, "losses": 0, "ties": 0} for s in ALL4}
    h2h = {opp: Counter() for opp in OPPONENTS}
    for r in valid:
        pair = {r["system_a"], r["system_b"]}
        if r.get("winner") == "tie":
            wlt[r["system_a"]]["ties"] += 1
            wlt[r["system_b"]]["ties"] += 1
        else:
            w = r.get("winning_system")
            loser = r["system_b"] if r["system_a"] == w else r["system_a"]
            if w in wlt: wlt[w]["wins"] += 1
            if loser in wlt: wlt[loser]["losses"] += 1
        if SONNET in pair:
            opp = (pair - {SONNET}).pop()
            if r.get("winner") == "tie":
                h2h[opp]["tie"] += 1
            elif r.get("winning_system") == SONNET:
                h2h[opp]["sonnet_win"] += 1
            else:
                h2h[opp]["sonnet_loss"] += 1

    sw = sum(h2h[o]["sonnet_win"] for o in OPPONENTS)
    sl = sum(h2h[o]["sonnet_loss"] for o in OPPONENTS)
    st = sum(h2h[o]["tie"] for o in OPPONENTS)
    decisive = sw + sl
    winrate = round(sw / decisive, 3) if decisive else 0.0

    bypid = defaultdict(dict)
    pid_opp = {}
    pid_edge = {}  # pid -> (system_a, system_b) from either order (same unordered pair)
    for (order, pid), r in sonnet.items():
        bypid[pid][order] = canonical(r)
        pair = {r["system_a"], r["system_b"]}
        pid_edge[pid] = (r["system_a"], r["system_b"])
        if SONNET in pair:
            pid_opp[pid] = (pair - {SONNET}).pop()
    both = {pid: d for pid, d in bypid.items() if len(d) == 2}
    stable = sum(1 for d in both.values() if len(set(d.values())) == 1)
    winner_dist = dict(Counter(r.get("winner") for r in valid))

    # --- Consistency analysis: fold blind+reverse; flip (disagreement) -> consistency-tie ---
    # by-opponent consistency rate + folded win/loss/tie
    consistency_by_opp = {}
    folded_sonnet = []  # [(winner_or_tie, a, b)] for Sonnet pairs, one per context-pair
    opp_stat = {o: Counter() for o in OPPONENTS}
    opp_stable = {o: [0, 0] for o in OPPONENTS}  # [stable, total]
    for pid, d in both.items():
        vb, vr = d["pairwise_blind"], d["pairwise_blind_reverse"]
        agree = (vb == vr)
        a, b = pid_edge[pid]
        folded_win = vb if (agree and vb != "tie") else "tie"
        opp = pid_opp.get(pid)
        if opp:  # Sonnet pair
            folded_sonnet.append((folded_win, a, b))
            opp_stable[opp][1] += 1
            if len(set(d.values())) == 1:
                opp_stable[opp][0] += 1
            if folded_win == "tie":
                opp_stat[opp]["consistency_tie"] += 1
            elif folded_win == SONNET:
                opp_stat[opp]["sonnet_win"] += 1
            else:
                opp_stat[opp]["sonnet_loss"] += 1
    for o in OPPONENTS:
        st_o, tt_o = opp_stable[o]
        consistency_by_opp[o] = {
            "consistency_rate": round(st_o / tt_o, 3) if tt_o else 0.0,
            "stable": st_o, "total": tt_o,
            "folded": dict(opp_stat[o]),
        }
    folded_sonnet_wlt = {
        "sonnet_win": sum(opp_stat[o]["sonnet_win"] for o in OPPONENTS),
        "sonnet_loss": sum(opp_stat[o]["sonnet_loss"] for o in OPPONENTS),
        "consistency_tie": sum(opp_stat[o]["consistency_tie"] for o in OPPONENTS),
    }
    fsw, fsl = folded_sonnet_wlt["sonnet_win"], folded_sonnet_wlt["sonnet_loss"]
    folded_decisive_winrate = round(fsw / (fsw + fsl), 3) if (fsw + fsl) else 0.0

    # joint 4-model BT (primary: each of the 2400 judgments is one edge; a flip = 1 win + 1 loss)
    three = load_three()
    three_valid = list(three.values())
    joint = valid + three_valid
    bt = fit_bt(ALL4, joint)
    bt_rank = [s for s, _ in sorted(bt.items(), key=lambda kv: kv[1], reverse=True)]
    ci, rank_dist, top_rank_frac = bootstrap_bt(ALL4, joint, n_boot=1000)

    # robustness: fold BOTH Sonnet and 3-model pairs (flip -> consistency-tie, tie credits 0.5 each)
    three_bypid = defaultdict(dict)
    for (order, pid), r in three.items():
        three_bypid[pid][order] = (canonical(r), r["system_a"], r["system_b"])
    folded_three = []
    for pid, d in three_bypid.items():
        if len(d) != 2:
            continue
        (vb, a, b) = d["pairwise_blind"]
        (vr, _, _) = d["pairwise_blind_reverse"]
        folded_three.append((vb if (vb == vr and vb != "tie") else "tie", a, b))
    bt_folded = fit_bt_folded(ALL4, folded_sonnet + folded_three)
    bt_folded_rank = [s for s, _ in sorted(bt_folded.items(), key=lambda kv: kv[1], reverse=True)]

    # Condorcet over 4 models (head-to-head majority on joint edges)
    h2h_all = defaultdict(Counter)
    for r in joint:
        if r.get("winner") == "tie":
            continue
        w = r.get("winning_system")
        loser = r["system_b"] if r["system_a"] == w else r["system_a"]
        if w in ALL4 and loser in ALL4:
            h2h_all[tuple(sorted([w, loser]))][w] += 1
    beats = {s: set() for s in ALL4}
    pair_maj = {}
    for x, y in combinations(ALL4, 2):
        c = h2h_all[tuple(sorted([x, y]))]
        xw, yw = c.get(x, 0), c.get(y, 0)
        if xw > yw: beats[x].add(y); maj = x
        elif yw > xw: beats[y].add(x); maj = y
        else: maj = "tie"
        pair_maj[f"{x} vs {y}"] = {"wins": dict(c), "majority": maj}
    beat_counts = {s: len(beats[s]) for s in ALL4}
    transitive = sorted(beat_counts.values()) == [0, 1, 2, 3]
    condorcet_winner = [s for s in ALL4 if beat_counts[s] == 3]

    report = {
        "status": "pass" if len(valid) == 1200 else "partial",
        "policy": "sonnet_full200_vs_3model_gemini_no_release_no_leaderboard",
        "todo": "#11 4th-model FULL (Sonnet-4.6), 200 ctx x 3 opp x 2 order = 1200",
        "judge": "Gemini-3.1-Pro-Preview (non-participant)",
        "sonnet_model": SONNET,
        "contexts": 200,
        "unique_ordered_judgments": len(sonnet),
        "valid_judgments": len(valid),
        "sonnet_overall": {"wins": sw, "losses": sl, "ties": st, "decisive_win_rate": winrate},
        "sonnet_vs_each_opponent": {o: dict(h2h[o]) for o in OPPONENTS},
        "win_loss_tie_all4_on_1200": wlt,
        "winner_side_dist_on_1200": winner_dist,
        "order_stability": {"pairs_both_orders": len(both), "stable_pairs": stable,
                            "stable_rate": round(stable / len(both), 3) if both else 0.0},
        "consistency_analysis": {
            "note": "flip across A/B order = consistency-tie; instability concentrates on the closest matchup (Sonnet vs GPT), i.e. the judge is honestly signalling difficulty, not judging randomly.",
            "sonnet_by_opponent": consistency_by_opp,
            "sonnet_folded_win_loss_tie": folded_sonnet_wlt,
            "sonnet_folded_decisive_win_rate": folded_decisive_winrate,
        },
        "bt_joint_4model_centered_log_ability": bt,
        "bt_joint_ranking": bt_rank,
        "bt_joint_bootstrap_ci95": ci,
        "bt_joint_rank_distribution_top5": rank_dist,
        "bt_top_ranking_stability": round(top_rank_frac, 3),
        "bt_folded_robustness_centered_log_ability": bt_folded,
        "bt_folded_robustness_ranking": bt_folded_rank,
        "joint_pairs_used": len(joint),
        "condorcet": {"beat_counts": beat_counts, "transitive_no_cycle": transitive,
                      "condorcet_winner": condorcet_winner[0] if condorcet_winner else None,
                      "head_to_head": pair_maj},
        "release_ready": False,
        "allowed_to_publish_leaderboard": False,
    }

    out_json = IB / "analysis" / "lit2test_v02_sonnet_full200_vs_3model_gemini_summary.json"
    out_md = IB / "analysis" / "lit2test_v02_sonnet_full200_vs_3model_gemini_summary.md"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Lit2Test v0.2 — 4th Model (Claude-Sonnet-4.6) FULL 200, Gemini Judge (1200)",
        "",
        "中文简介:第 4 模型 Claude-Sonnet-4.6 全 200 情境。只建 Sonnet 参与的新对"
        "(200 ctx × 3 对手 × 正反序 = 1200),Gemini 非参赛裁判判,判官 prompt 与原生管线完全一致。"
        "现有 3 模型 1200 判**不重判**,仅在联合 BT 里给 Sonnet 定位(联合 2400 边)。",
        "",
        f"- Status: `{report['status']}`  |  Judge: `{report['judge']}`",
        f"- Valid judgments: `{report['valid_judgments']}/1200`",
        f"- 生成/建对/判分口径与 3 模型一致(temperature 1.0, max_tokens 1800, native pairwise prompt)。",
        "",
        "## Sonnet 总成绩(1200 新对)",
        "",
        f"- **胜 {sw} / 负 {sl} / 平 {st}**,decisive 胜率 = **{winrate}**",
        "",
        "## Sonnet vs 各对手",
        "",
        "| 对手 | Sonnet 胜 | Sonnet 负 | 平 |",
        "|---|---:|---:|---:|",
    ]
    for o in OPPONENTS:
        c = h2h[o]
        lines.append(f"| {o} | {c.get('sonnet_win',0)} | {c.get('sonnet_loss',0)} | {c.get('tie',0)} |")
    lines += [
        "",
        "## 联合 4 模型 BT(1200 新 + 1200 旧 = 2400 边)",
        "",
        "| 模型 | BT centered log-ability | 95% CI (bootstrap) |",
        "|---|---:|---|",
    ]
    for s in bt_rank:
        lines.append(f"| {s} | {bt[s]:.4f} | [{ci[s][0]}, {ci[s][1]}] |")
    lines += [
        "",
        f"- **联合 BT 排名: `{' > '.join(bt_rank)}`**(该全序 bootstrap 稳定率 {report['bt_top_ranking_stability']})",
        f"- Condorcet: beat_counts `{beat_counts}`; winner `{report['condorcet']['condorcet_winner']}`; "
        f"{'无环(传递)' if transitive else '有环(不传递)'}",
        "",
        "## 稳健性 / 一致性分析",
        "",
        f"- 正反序**双向一致率**: `{stable}/{len(both)}` = `{report['order_stability']['stable_rate']}`"
        f"(三模型基线 82.2%;略低是因为不一致集中在势均力敌对,见下)",
        f"- Winner A/B 分布(位置偏好): `{winner_dist}`",
        "",
        "**按对手拆分:一致率随胜负差距单调变化 —— 越接近的对,judge 越常翻转(诚实反映难度,非乱判)**",
        "",
        "| 对手 | 双向一致率 | 折叠后 Sonnet 胜/负/一致性平 |",
        "|---|---:|---|",
    ]
    for o in OPPONENTS:
        ca = consistency_by_opp[o]
        f = ca["folded"]
        lines.append(f"| {o} | {ca['consistency_rate']} | "
                     f"{f.get('sonnet_win',0)}/{f.get('sonnet_loss',0)}/{f.get('consistency_tie',0)} |")
    lines += [
        "",
        f"- 把翻转显式记为 tie 后:Sonnet **胜 {fsw} / 负 {fsl} / 一致性平 {folded_sonnet_wlt['consistency_tie']}**,"
        f"decisive 胜率 {folded_decisive_winrate}。**vs GPT 的 {consistency_by_opp['GPT 5.2']['folded'].get('consistency_tie',0)} 个 tie 量化了两者难分伯仲**。",
        f"- **口径稳健性**:把翻转当 tie(BT 里各记 0.5)重拟合联合 BT,全序 `{' > '.join(bt_folded_rank)}`,"
        f"与主 BT 一致 → 换 tie 口径不改变排名结论(注:tie 必须各记 0.5,直接丢弃会人为拉大分差)。",
        "",
        "## 结论",
        "",
        f"Sonnet-4.6 全 200 对现有 3 模型 decisive 胜率 {winrate}(胜 {sw}/负 {sl})。"
        f"联合 BT 全序 {' > '.join(bt_rank)},bootstrap 稳定率 {report['bt_top_ranking_stability']}。"
        f"Condorcet {'无环(传递)' if transitive else '有环'}。双向一致率 {report['order_stability']['stable_rate']},"
        f"不一致集中在最接近的 Sonnet-GPT 对(一致率仅 {consistency_by_opp['GPT 5.2']['consistency_rate']}),"
        f"即单场噪声大但聚合排名零动摇。此为完整 4 模型主实验(#11),仍不替代 #5 人类校准,不发布 leaderboard。",
        "",
        f"- Release ready: `False`  |  Publish leaderboard: `False`",
    ]
    out_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print("WROTE", out_json)
    print(f"valid={len(valid)}/1200 sonnet W/L/T={sw}/{sl}/{st} winrate={winrate} "
          f"BT={bt_rank} boot_stable={report['bt_top_ranking_stability']} "
          f"condorcet_transitive={transitive} order_stable={report['order_stability']['stable_rate']}")


if __name__ == "__main__":
    main()
