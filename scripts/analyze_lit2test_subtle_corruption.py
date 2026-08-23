#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/lit2test_targeted_subtle_corruption_20x3x2_sham'
ANALYSIS=ROOT/'analysis'
DIMS=('grounding','decisive_metric','falsifiability')
SCORE_DIMS=('grounding','hypothesis_specificity','minimality_feasibility','decisive_metric','falsifiability')
UNITS={'grounding':('G-partial','G-misattributed'),'decisive_metric':('M-proxy','M-aggregation'),'falsifiability':('F-null','F-wrong-axis')}

def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def read_jsonl(path): return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def boot(values,seed,stat:Callable[[np.ndarray],float]=lambda x:float(np.mean(x))):
    a=np.asarray(values,dtype=float); rng=np.random.default_rng(seed); idx=rng.integers(0,len(a),size=(10000,len(a))); est=np.asarray([stat(a[i]) for i in idx]); return [float(x) for x in np.quantile(est,[.025,.975])]
def summary(values,seed):
    return {'n':len(values),'mean':float(statistics.mean(values)),'mean_ci95':boot(values,seed),'median':float(statistics.median(values)),'median_ci95':boot(values,seed+1,lambda x:float(np.median(x))),'values':[float(x) for x in values]}
def side(item,which): return item['score_a'] if which=='A' else item['score_b']
def role_side(task,role): return 'A' if task['role_a']==role else 'B'
def score_outcome(a,b): return 'original' if a>b else 'edited' if a<b else 'tie'
def overall_outcome(winner,task):
    if winner=='tie': return 'tie'
    return 'original' if (task['role_a'] if winner=='A' else task['role_b'])=='x' else 'edited'

def construction_stats(out):
    dirs=[(0,out)]
    for d in sorted(out.glob('reserve_round_*'),key=lambda p:int(p.name.rsplit('_',1)[1])):
        c=d/'construction'
        if (c/'edit_candidates.jsonl').exists(): dirs.append((int(d.name.rsplit('_',1)[1]),c))
    all_rows=[]; blocks=defaultdict(list)
    for round_id,d in dirs:
        for r in read_jsonl(d/'edit_candidates.jsonl'):
            x=dict(r); x['_round']=round_id; all_rows.append(x); blocks[(round_id,r['case_id'],r['unit'])].append(x)
    by_unit={}
    for unit in [u for pair in UNITS.values() for u in pair]+[f'sham-{d}' for d in DIMS]:
        b=[v for k,v in blocks.items() if k[2]==unit]; passed=[v for v in b if any(r.get('selected') for r in v)]
        by_unit[unit]={'blocks_generated':len(b),'candidate_attempts':sum(len({r['attempt'] for r in v}) for v in b),'passed_blocks':len(passed),'revised_blocks':sum(next(r['attempt'] for r in v if r.get('selected'))>1 for v in passed),'rejected_blocks':len(b)-len(passed),'first_pass_acceptance_rate':sum(any(r.get('selected') and r['attempt']==1 for r in v) for v in b)/len(b) if b else None,'mean_attempts':float(statistics.mean(len({r['attempt'] for r in v}) for v in b)) if b else None}
    semantic_records=[r for r in all_rows if len(r.get('semantic') or [])==2]
    agreements=sum(bool(r['semantic'][0].get('pass'))==bool(r['semantic'][1].get('pass')) for r in semantic_records)
    tie_breaks=sum('tie_break' in r for r in semantic_records)
    natural_fail=Counter()
    for r in all_rows:
        n=r.get('naturalness') or {}
        for v in n.get('validators',[]):
            if not v.get('pass'):
                reason=(v.get('result') or {}).get('reason') or v.get('error') or 'unknown'; natural_fail[reason]+=1
    selections=[read_json(p) for p in sorted(out.glob('reserve_round_*/selection.json'))]
    final_sources=read_json(out/'protocol.json')['final_construction']['case_sources']
    return {'candidate_attempt_records':len(all_rows),'candidate_blocks':len(blocks),'by_unit':by_unit,'semantic_two_validator_records':len(semantic_records),'semantic_agreement':agreements/len(semantic_records) if semantic_records else None,'semantic_tie_breaks':tie_breaks,'naturalness_failure_reasons':dict(natural_fail.most_common()),'reserve_rounds':len(selections),'reserve_replacement_attempts':sum(len(x['replacements']) for x in selections),'final_original_cases':sum(v['round']==0 for v in final_sources.values()),'final_replaced_cases':sum(v['round']>0 for v in final_sources.values()),'final_case_source_rounds':dict(Counter(str(v['round']) for v in final_sources.values()))}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',default=str(OUT)); ap.add_argument('--date',default='20260722'); args=ap.parse_args(); out=Path(args.output_dir).resolve()
    protocol=read_json(out/'protocol.json'); completion=read_json(out/'completion_report.json')
    if not completion.get('completion_gate_360'): raise SystemExit('360-judgment completion gate not passed')
    tasks=read_jsonl(out/'audit_tasks.jsonl'); judgments=read_jsonl(out/'judgments.jsonl'); task_map={r['audit_id']:r for r in tasks}; by_j={r['audit_id']:r for r in judgments}
    if len(tasks)!=360 or len(by_j)!=360 or set(task_map)!=set(by_j): raise SystemExit('task/judgment integrity failure')
    ordered=[]
    for aid,t in task_map.items():
        j=by_j[aid]['judgment']; oside=role_side(t,'x'); eside=role_side(t,'y'); target=t['target_dimension']; item=j['dimensions'][target]; oscore=float(side(item,oside)); escore=float(side(item,eside)); diffs=[]
        for d in SCORE_DIMS:
            if d==target: continue
            it=j['dimensions'][d]; diffs.append(abs(float(side(it,oside))-float(side(it,eside))))
        ordered.append({'audit_id':aid,'case_id':t['case_id'],'pair_id':t['pair_id'],'condition':t['condition'],'unit':t['unit'],'target_dimension':target,'order':t['order'],'target_outcome':score_outcome(oscore,escore),'target_net':1 if oscore>escore else -1 if oscore<escore else 0,'target_score_difference':oscore-escore,'non_target_abs_drift':float(statistics.mean(diffs)),'overall_outcome':overall_outcome(j['overall_winner'],t)})
    group=defaultdict(list)
    for r in ordered: group[(r['case_id'],r['target_dimension'],r['condition'],r['unit'])].append(r)
    pair_case={}
    for k,rows in group.items():
        if len(rows)!=2 or {r['order'] for r in rows}!={'original','reverse'}: raise SystemExit(f'pair repeat mismatch {k}')
        pair_case[k]={'net':float(statistics.mean(r['target_net'] for r in rows)),'score_diff':float(statistics.mean(r['target_score_difference'] for r in rows)),'drift':float(statistics.mean(r['non_target_abs_drift'] for r in rows)),'target_outcomes':[r['target_outcome'] for r in rows],'overall_outcomes':[r['overall_outcome'] for r in rows]}
    case_rows=[]
    for ci in range(1,21):
        cid=f'case_{ci:03d}'
        for di,dim in enumerate(DIMS):
            subs=[pair_case[(cid,dim,'subtle',u)] for u in UNITS[dim]]; sham=pair_case[(cid,dim,'sham',f'sham-{dim}')]
            case_rows.append({'case_id':cid,'target_dimension':dim,'p_subtle':float(statistics.mean(x['net'] for x in subs)),'p_sham':sham['net'],'adjusted_preference':float(statistics.mean(x['net'] for x in subs))-sham['net'],'subtle_target_score_drop':float(statistics.mean(x['score_diff'] for x in subs)),'sham_target_score_difference':sham['score_diff'],'subtle_non_target_abs_drift':float(statistics.mean(x['drift'] for x in subs))})
    dimensions={}; seed=2026072103
    for di,dim in enumerate(DIMS):
        cases=[r for r in case_rows if r['target_dimension']==dim]; subord=[r for r in ordered if r['condition']=='subtle' and r['target_dimension']==dim]; shamord=[r for r in ordered if r['condition']=='sham' and r['target_dimension']==dim]
        adj=[r['adjusted_preference'] for r in cases]; shamdiff=[r['sham_target_score_difference'] for r in cases]; adj_summary=summary(adj,seed+di*100); sham_summary=summary(shamdiff,seed+di*100+10)
        if adj_summary['mean_ci95'][0]>0: gate='supports_contrast_controlled_local_sensitivity'
        elif adj_summary['mean']>0: gate='directional_evidence_only'
        else: gate='no_evidence_of_subtle_defect_sensitivity'
        sham_gate=sham_summary['mean_ci95'][0]>=-0.25 and sham_summary['mean_ci95'][1]<=0.25
        templates={}
        for ti,u in enumerate(UNITS[dim]):
            rows=[r for r in subord if r['unit']==u]; pcs=[pair_case[(f'case_{i:03d}',dim,'subtle',u)] for i in range(1,21)]
            templates[u]={'ordered_target_win_tie_loss':dict(Counter(r['target_outcome'] for r in rows)),'ordered_overall_win_tie_loss':dict(Counter(r['overall_outcome'] for r in rows)),'target_net_preference':summary([x['net'] for x in pcs],seed+di*100+20+ti*4),'target_score_drop':summary([x['score_diff'] for x in pcs],seed+di*100+21+ti*4),'non_target_abs_drift':summary([x['drift'] for x in pcs],seed+di*100+22+ti*4),'both_order_original_target_wins':sum(x['target_outcomes'].count('original')==2 for x in pcs),'target_order_consistent':sum(x['target_outcomes'][0]==x['target_outcomes'][1] for x in pcs),'target_direct_flips':sum(set(x['target_outcomes'])=={'original','edited'} for x in pcs)}
        heter=[pair_case[(f'case_{i:03d}',dim,'subtle',UNITS[dim][0])]['net']-pair_case[(f'case_{i:03d}',dim,'subtle',UNITS[dim][1])]['net'] for i in range(1,21)]
        dimensions[dim]={'primary_adjusted_preference':adj_summary,'interpretation_gate':gate,'subtle_target_win_tie_loss':dict(Counter(r['target_outcome'] for r in subord)),'sham_original_win_tie_loss':dict(Counter(r['target_outcome'] for r in shamord)),'sham_target_score_difference':sham_summary,'sham_equivalence_gate_pass':sham_gate,'subtle_target_score_drop':summary([r['subtle_target_score_drop'] for r in cases],seed+di*100+30),'subtle_non_target_abs_drift':summary([r['subtle_non_target_abs_drift'] for r in cases],seed+di*100+31),'template_heterogeneity_net_difference':summary(heter,seed+di*100+32),'templates':templates}
    pooled=[]
    for i in range(1,21): pooled.append(float(statistics.mean(r['adjusted_preference'] for r in case_rows if r['case_id']==f'case_{i:03d}')))
    final_sources=protocol['final_construction']['case_sources']; strong_rows=list(csv.DictReader((ROOT/'analysis/lit2test_targeted_corruption_20x3_case_level_20260721.csv').open()))
    strong={(r['case_id'],r['target_dimension']):float(r['target_score_drop']) for r in strong_rows}; attenuation={}
    retained=[c for c,v in final_sources.items() if v['round']==0]
    for di,dim in enumerate(DIMS):
        diffs=[]
        for cid in retained:
            subtle=next(r['subtle_target_score_drop'] for r in case_rows if r['case_id']==cid and r['target_dimension']==dim); diffs.append(strong[(cid,dim)]-subtle)
        attenuation[dim]=summary(diffs,seed+500+di*10)
    guesses=[]; guess_total=0
    for r in read_jsonl(out/'naturalness_validation.jsonl'):
        edited='B' if r.get('a_first') else 'A'
        vals=list(r.get('validators') or []); tb=r.get('tie_break'); vals += [tb] if tb else []
        for v in vals:
            guess=(v.get('result') or {}).get('edited_side_guess')
            if guess in ('A','B','unknown'): guess_total+=1
            if guess in ('A','B'): guesses.append(guess==edited)
    construction=construction_stats(out); construction['edited_side_guess_total']=guess_total; construction['edited_side_guess_nonunknown']=len(guesses); construction['edited_side_guess_nonunknown_rate']=len(guesses)/guess_total if guess_total else None; construction['edited_side_guess_accuracy_given_nonunknown']=sum(guesses)/len(guesses) if guesses else None
    final_sem=read_jsonl(out/'semantic_validation.jsonl'); final_nat=read_jsonl(out/'naturalness_validation.jsonl'); construction['final_semantic_agreements']=sum(bool(r['validators'][0].get('pass'))==bool(r['validators'][1].get('pass')) for r in final_sem); construction['final_semantic_agreement_rate']=construction['final_semantic_agreements']/len(final_sem); construction['final_semantic_tie_breaks']=sum(bool(r.get('tie_break')) for r in final_sem); construction['final_naturalness_tie_breaks']=sum(bool(r.get('tie_break')) for r in final_nat)
    ANALYSIS.mkdir(exist_ok=True); jp=ANALYSIS/f'lit2test_targeted_subtle_corruption_20x3x2_sham_{args.date}.json'; mp=ANALYSIS/f'lit2test_targeted_subtle_corruption_20x3x2_sham_{args.date}.md'; cp=ANALYSIS/f'lit2test_targeted_subtle_corruption_case_level_{args.date}.csv'
    protocol['status']='complete'; protocol['analysis_files']={'json':str(jp.relative_to(ROOT)),'markdown':str(mp.relative_to(ROOT)),'case_csv':str(cp.relative_to(ROOT))}; (out/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'status':'complete','protocol_id':protocol['protocol_id'],'judge_model':protocol['models']['judge'],'completion':completion,'aggregation':{'independent_unit':'base_case','base_cases':20,'bootstrap_replicates':10000,'confidence_weighting':False,'ordered_rows_as_independent_samples':False},'primary_pooled_adjusted_preference':summary(pooled,seed+900),'dimensions':dimensions,'subtle_vs_strong_attenuation_retained_original_cases_only':{'n_cases':len(retained),'case_ids':sorted(retained),'dimensions':attenuation,'note':'Replaced reserve cases are excluded because they are not paired to the v1 strong-corruption base answer.'},'construction':construction,'claim_boundary':protocol['claim_boundary'],'release_ready':False,'allowed_to_publish_leaderboard':False,'files':{'protocol_sha256':sha(out/'protocol.json'),'tasks_sha256':sha(out/'audit_tasks.jsonl'),'judgments_sha256':sha(out/'judgments.jsonl')}}
    jp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with cp.open('w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=list(case_rows[0])); w.writeheader(); w.writerows(case_rows)
    lines=['# Lit2Test Subtle Corruption + Sham Audit（20×3×2）','',f"- Status: `{report['status']}`",'- Valid judgments: `360/360`','- Independent clusters: `20 base cases`','- Primary endpoint: case-level subtle target net preference minus sham original-text net preference','- Bootstrap: `10,000` case-level replicates','', '## Primary Results','', '| Dimension | Adjusted preference mean [95% CI] | Subtle target W/T/L | Sham original W/T/L | Sham score diff mean [95% CI] | Sham equivalence | Interpretation |','|---|---:|---:|---:|---:|---:|---|']
    for dim in DIMS:
        d=dimensions[dim]; a=d['primary_adjusted_preference']; sh=d['sham_target_score_difference']; sw=d['subtle_target_win_tie_loss']; hw=d['sham_original_win_tie_loss']; lines.append(f"| `{dim}` | {a['mean']:.3f} [{a['mean_ci95'][0]:.3f}, {a['mean_ci95'][1]:.3f}] | {sw.get('original',0)}/{sw.get('tie',0)}/{sw.get('edited',0)} | {hw.get('original',0)}/{hw.get('tie',0)}/{hw.get('edited',0)} | {sh['mean']:.3f} [{sh['mean_ci95'][0]:.3f}, {sh['mean_ci95'][1]:.3f}] | {'pass' if d['sham_equivalence_gate_pass'] else 'fail'} | `{d['interpretation_gate']}` |")
    pool=report['primary_pooled_adjusted_preference']; lines += ['',f"Across dimensions, pooled adjusted preference is **{pool['mean']:.3f}** (95% CI [{pool['mean_ci95'][0]:.3f}, {pool['mean_ci95'][1]:.3f}]).",'', '## Construction Audit','',f"- Final original cases: `{construction['final_original_cases']}`; final reserve replacements: `{construction['final_replaced_cases']}`",f"- Reserve rounds: `{construction['reserve_rounds']}`; replacement attempts: `{construction['reserve_replacement_attempts']}`",f"- Candidate attempts recorded: `{construction['candidate_attempt_records']}`",f"- Final selected semantic agreement: `{construction['final_semantic_agreement_rate']:.3f}`; tie-breaks: `{construction['final_semantic_tie_breaks']}/180` (all-candidate agreement: `{construction['semantic_agreement']:.3f}`)",f"- Edited-side guess accuracy (non-unknown guesses only): `{construction['edited_side_guess_accuracy_given_nonunknown']:.3f}` over `{construction['edited_side_guess_nonunknown']}` non-unknown guesses; non-unknown rate `{construction['edited_side_guess_nonunknown_rate']:.3f}`",'', '## Claim Boundary','', '允许表述：该 contrast-controlled audit 检验 structured Gemini judge 是否对自然、局部、维度定向的 scientific defects 敏感，并用 style-matched sham 校正原文/编辑风格偏好。','', '禁止据此声称 Gemini 等于人类或客观科研质量、自动 validator 构成人类校准、schema 改善生成质量、三个维度具有独立因果效应，或结果可替代已有 human calibration。','', 'Strong-corruption attenuation 仅对仍使用原 v1 base answer 的 12 个 case 做 paired 描述；reserve replacements 不伪装成同 case 配对。']
    mp.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':'complete','json':str(jp),'markdown':str(mp),'csv':str(cp)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
