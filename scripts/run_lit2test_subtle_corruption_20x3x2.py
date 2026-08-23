#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json, random, re, sys, time
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/lit2test_targeted_subtle_corruption_20x3x2_sham'
BASE = ROOT / 'outputs/lit2test_targeted_corruption_20x3'
FIELDS = ('literature_gap','hypothesis','minimal_test','decisive_metric','supporting_result','falsifying_result')
TARGET_FIELD = {'grounding':'literature_gap','decisive_metric':'decisive_metric','falsifiability':'falsifying_result'}
TEMPLATES = {
 'grounding': ('G-partial','G-misattributed'),
 'decisive_metric': ('M-proxy','M-aggregation'),
 'falsifiability': ('F-null','F-wrong-axis'),
}
MODEL_EDITOR='claude-sonnet-4-6'
MODEL_V1='gpt-5.4'
MODEL_V2='deepseek-v4-pro'
MODEL_TIE='glm-5.2'
MODEL_JUDGE='gemini-3.1-pro-preview'
FORBIDDEN = ('without a baseline','not falsifiable','rerun until favorable','no limitation remains','proxy metric','corrupted answer')


def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def read_jsonl(path):
    p=Path(path)
    return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()] if p.exists() else []
def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True); Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def append_jsonl(path, row):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open('a',encoding='utf-8') as f: f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
def sha256_file(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def sha256_obj(value): return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def now(): return time.strftime('%Y-%m-%dT%H:%M:%S%z')
def toks(s): return re.findall(r"[A-Za-z0-9_]+(?:[-'][A-Za-z0-9_]+)?", s)
def extract_json(text):
    text=text.strip()
    text=re.sub(r'^```(?:json)?\s*','',text,flags=re.I); text=re.sub(r'\s*```$','',text)
    try: return json.loads(text)
    except Exception: pass
    start=text.find('{'); end=text.rfind('}')
    if start>=0 and end>start: return json.loads(text[start:end+1])
    raise ValueError('no JSON object')

def settings():
    import os
    token=os.environ.get('ANTHROPIC_AUTH_TOKEN') or os.environ.get('API_KEY')
    if not token: raise RuntimeError('ANTHROPIC_AUTH_TOKEN (or API_KEY) env var missing')
    return os.environ.get('ANTHROPIC_BASE_URL','${API_BASE_URL_ANTHROPIC}').rstrip('/'), token, {}

def call(model, prompt, max_tokens=900, temperature=0.0, anthropic=False, timeout=120):
    base, token, extra=settings()
    headers={'Authorization':f'Bearer {token}','Content-Type':'application/json',**extra}
    if anthropic:
        headers={'x-api-key':token,'anthropic-version':'2023-06-01','Content-Type':'application/json',**extra}
        payload={'model':model,'max_tokens':max_tokens,'temperature':temperature,'messages':[{'role':'user','content':prompt}]}
        path='/v1/messages'
    else:
        payload={'model':model,'max_tokens':max_tokens,'temperature':temperature,'thinking':{'type':'disabled'},'response_format':{'type':'json_object'},'messages':[{'role':'user','content':prompt}]}
        path='/v1/chat/completions'
    resp=requests.post(base+path,headers=headers,json=payload,timeout=timeout)
    if resp.status_code>=400: raise RuntimeError(f'{model} HTTP {resp.status_code}: {resp.text[:500]}')
    data=resp.json()
    if anthropic:
        text=''.join(x.get('text','') for x in data.get('content',[]) if x.get('type')=='text')
    else:
        message=data['choices'][0]['message']; text=message.get('content') or message.get('reasoning_content','')
    return text

def call_json(model, prompt, max_tokens=1400):
    last=None
    for attempt in range(1,5):
        try:
            return extract_json(call(model,prompt,max_tokens=max_tokens,temperature=0))
        except Exception as e:
            last=e
            if attempt<4: time.sleep(2*attempt)
    raise last

def call_editor_json(prompt, max_tokens=1000):
    last=None
    for attempt in range(1,4):
        try:
            return call(MODEL_EDITOR,prompt,max_tokens=max_tokens,temperature=0,anthropic=True), None
        except Exception as e:
            last=e
            if attempt<3: time.sleep(2*attempt)
    raise last

def context_digest(ctx):
    papers=[]
    for i,p in enumerate(ctx.get('papers',[]),1):
        papers.append({'index':i,'title':p.get('title'),'paper_id':p.get('paper_id'),'abstract':p.get('abstract',''),'important_result':p.get('important_result',''),'limitation':p.get('limitation','')})
    return {'field':ctx.get('field'),'open_problem':ctx.get('open_problem'),'task_instruction':ctx.get('task_instruction'),'papers':papers}

def template_instruction(template):
    return {
      'G-partial':'Keep one paper-specific premise supported by the supplied papers, but replace a second premise with a related, plausible inference that the supplied papers do not support. Preserve a real-looking cross-paper gap while making the synthesis invalid.',
      'G-misattributed':'Keep real claims from at least two supplied papers, but swap which paper made one mechanism, result, or limitation claim. The content must remain specific and plausible while the attribution is wrong.',
      'M-proxy':'Replace the mechanism-level primary readout with a common aggregate task metric. Keep a baseline, comparison direction, and approximate threshold if present, but make the metric unable to distinguish the stated mechanism from an alternative explanation.',
      'M-aggregation':'Keep the same metric family but remove or alter the key slice, tail, condition, matched-budget, denominator, or conditional comparison so an aggregate can hide the target effect. Preserve baseline and threshold where possible.',
      'F-null':'Replace the real disconfirming condition with failure to reach statistical significance, without an equivalence margin, minimum detectable effect, or adequate-power condition. Keep the wording concrete and proposal-like.',
      'F-wrong-axis':'Replace the falsifier with a concrete negative result on a secondary or auxiliary outcome, while leaving the core mechanism hypothesis able to hold.',
    }[template]

def editor_prompt(ctx, answer, template, sham=False, attempt=1):
    field=TARGET_FIELD[template] if sham else TARGET_FIELD[{'G-partial':'grounding','G-misattributed':'grounding','M-proxy':'decisive_metric','M-aggregation':'decisive_metric','F-null':'falsifiability','F-wrong-axis':'falsifiability'}[template]]
    if sham:
        instruction='Make a meaning-preserving paraphrase of a single contiguous span in the target field. Preserve every scientific entity, comparison, threshold, condition, slice, and decision rule. Do not add or remove a scientific claim.'
        schema='"sham": true, "semantic_preservation": "..."'
    else:
        instruction=template_instruction(template)
        schema='"defect_template": "'+template+'", "evidence": "...", "countermodel": "..."'
    return f'''You are the frozen editor for a scientific proposal audit. Return JSON only, no Markdown. Propose ONE local patch, not a whole-field rewrite. The patch must use exact source substrings for start_quote and end_quote and replace the inclusive contiguous span from start_quote through end_quote. start_quote and end_quote must be short boundary anchors of 3-8 words, not full-field quotations; the inclusive span between them must cover roughly 15-30% of the target field. Reuse most surrounding syntax and at least half of the removed span tokens in the replacement so the change remains local. Keep grammar and serious proposal style. The target field has {len(toks(answer[field]))} tokens and {len(answer[field])} characters. At least {max(1, int(len(toks(answer[field]))*0.15+0.999))} full-field tokens must change, while no more than {int(len(toks(answer[field]))*0.35)} may change; count this explicitly before returning. The full edited field must retain at least 70% of original tokens; changed-token fraction over the full target field must be 0.10-0.35; full-field length ratio must be 0.85-1.15. Change a span covering roughly 15-30% of the field and keep the replacement span close in token and character length to the removed span; aim for a 0.95-1.05 full-field length ratio. This is attempt {attempt}; if attempt is greater than 1, choose a materially different valid span or wording. Do not introduce a new paper, method, dataset, model name, number, named entity, rubric term, or editing cue. Forbidden cues: {', '.join(FORBIDDEN)}.

Template instruction: {instruction}

Return this schema: {{"start_quote":"exact source substring", "end_quote":"exact source substring", "replacement":"replacement span", {schema}}}

SUPPLIED CONTEXT:
{json.dumps(context_digest(ctx),ensure_ascii=False)}

FULL ANSWER:
{json.dumps(answer,ensure_ascii=False)}

TARGET FIELD ({field}):
{answer[field]}'''

def naturalness_prompt(clean, edited, seed):
    a_first=seed%2==0
    A=clean if a_first else edited; B=edited if a_first else clean
    return f'''You are a blind construction-audit validator. You do not know which answer was edited, the target field, or the defect template. Treat A and B as anonymous serious research proposals from a real model. Return JSON only: {{"a_serious":true,"b_serious":true,"obvious_edit_artifact":false,"style_or_length_imbalance":false,"edited_side_guess":"A|B|unknown","reason":"..."}}. Only flag unmistakable template language, broken grammar, or severe style/length imbalance; do not judge scientific quality and do not use the side guess for selection.

Answer A:
{json.dumps(A,ensure_ascii=False)}

Answer B:
{json.dumps(B,ensure_ascii=False)}''', a_first

def semantic_prompt(ctx, clean, edited, template, sham=False):
    if sham:
        task='Check whether the edited target field is scientifically equivalent to the clean field. Set semantic_equivalent=true only if no scientific claim, entity, comparison, threshold, condition, slice, or decision rule changed.'
        schema='{"semantic_equivalent":true,"new_scientific_claim":false,"decision_rule_changed":false,"reason":"..."}'
    else:
        task=f'''Check the intended {template} intervention. Determine whether the intended defect is genuinely present, whether {template} is the primary affected dimension, whether the full proposal remains coherent, and whether the edit introduced a major unrelated defect. proposal_coherent means grammatically complete and internally readable apart from the intended target defect; do not set it false merely because the intended target-dimension defect weakens motivation or alignment. Record possible cross-dimension spillover without treating expected coupling as rejection.'''
        schema='{"defect_present":true,"primary_affected_dimension":"grounding|decisive_metric|falsifiability|other","proposal_coherent":true,"additional_major_unrelated_defect":false,"spillover_risk":"none|low|medium|high","reason":"..."}'
    return f'''You are an automated semantic validator, not a human annotator. You know the template but must not use any judge outcome or generator identity. {task}
Return JSON only with schema {schema}.

CONTEXT:
{json.dumps(context_digest(ctx),ensure_ascii=False)}

CLEAN ANSWER:
{json.dumps(clean,ensure_ascii=False)}

EDITED ANSWER:
{json.dumps(edited,ensure_ascii=False)}'''

def mechanical(clean, edited, field, patch):
    errs=[]; orig=clean[field]; repl=edited[field]
    if not all(isinstance(edited.get(f),str) and edited[f].strip() for f in FIELDS): errs.append('schema_nonempty')
    if sum(clean[f]!=edited[f] for f in FIELDS)!=1 or clean[field]==edited[field]: errs.append('not_single_target_field')
    if any(x.lower() in repl.lower() for x in FORBIDDEN): errs.append('forbidden_cue')
    ot,rt=toks(orig),toks(repl); sm=SequenceMatcher(None,ot,rt,autojunk=False); equal=sum(m.size for m in sm.get_matching_blocks());
    retention=equal/max(1,len(ot)); changed=max(len(ot),len(rt))-equal; changed_fraction=changed/max(1,len(ot)); ratio=len(repl)/max(1,len(orig))
    if retention<0.70: errs.append('token_retention')
    if not 0.10<=changed_fraction<=0.35: errs.append('changed_token_fraction')
    if not 0.85<=ratio<=1.15: errs.append('length_ratio')
    start=patch.get('start_quote',''); end=patch.get('end_quote','')
    s=orig.find(start) if start else -1; e=(s+start.find(end) if s>=0 and end in start else orig.find(end,s+len(start))) if end else -1
    if s<0 or e<0: errs.append('span_not_found')
    else:
        e+=len(end); expected=orig[:s]+patch.get('replacement','')+orig[e:]
        if expected!=repl: errs.append('patch_application_mismatch')
    def entities(x):
        words=re.findall(r"\b[A-Za-z][A-Za-z0-9-]*\b|\b\d+(?:\.\d+)?%?\b",x)
        return {w for w in words if re.search(r"\d",w) or (len(w)>1 and w.isupper()) or re.search(r"[a-z][A-Z]|[A-Z].*[A-Z]",w)}
    new_entities=entities(repl)-entities(orig)
    if new_entities: errs.append('new_named_or_numeric_entity:'+','.join(sorted(new_entities)))
    return {'status':'pass' if not errs else 'fail','errors':errs,'token_retention':retention,'changed_token_fraction':changed_fraction,'length_ratio':ratio,'original_tokens':len(ot),'edited_tokens':len(rt),'new_entities':sorted(new_entities)}

def apply_patch(clean, field, patch):
    orig=clean[field]; start=patch.get('start_quote',''); end=patch.get('end_quote',''); s=orig.find(start) if start else -1; e=(s+start.find(end) if end in start else orig.find(end,s+len(start))) if s>=0 and end else -1
    if s<0 or e<0: raise ValueError('span not found')
    e+=len(end); out=dict(clean); out[field]=orig[:s]+patch.get('replacement','')+orig[e:]; return out

def validator_ok(result, template, sham):
    if sham: return result.get('semantic_equivalent') is True and result.get('new_scientific_claim') is False and result.get('decision_rule_changed') is False
    return result.get('defect_present') is True and result.get('primary_affected_dimension')=={'G-partial':'grounding','G-misattributed':'grounding','M-proxy':'decisive_metric','M-aggregation':'decisive_metric','F-null':'falsifiability','F-wrong-axis':'falsifiability'}[template] and result.get('proposal_coherent') is True and result.get('additional_major_unrelated_defect') is False

def construct(args):
    root_out=Path(args.run_out).resolve()
    base_path=Path(args.base_file).resolve()
    root_out.mkdir(parents=True,exist_ok=True)
    all_rows=read_jsonl(base_path)[:args.limit_cases]
    if args.base_file==str(BASE/'base_answers.jsonl') and args.limit_cases==20 and len(all_rows)!=20: raise SystemExit(f'expected 20 base rows, got {len(all_rows)}')
    if args.shard_count<1 or not 0<=args.shard_index<args.shard_count: raise SystemExit('invalid shard settings')
    indexed_all=[(position,int(row['case_id'].rsplit('_',1)[1])-1,row) for position,row in enumerate(all_rows)]
    indexed_rows=[(case_index,row) for position,case_index,row in indexed_all if position % args.shard_count == args.shard_index]
    rows=[row for _,row in indexed_rows]
    if root_out==OUT and not (OUT/'base_answers.jsonl').exists():
        with (OUT/'base_answers.jsonl').open('w',encoding='utf-8') as f:
            for r in all_rows: f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
    run_out=root_out if args.shard_count==1 else root_out/'shards'/f'shard{args.shard_index}'
    candidate_path=run_out/'edit_candidates.jsonl'
    selected={}
    existing=read_jsonl(candidate_path)
    existing_by={}
    for r in existing:
        key=(r['case_id'],r['unit'])
        existing_by.setdefault(key,[]).append(r)
        if r.get('selected'): selected[key]=r
    for ri,row in indexed_rows:
        case=row['case_id']; ctx=row['context']; clean=row['answer']
        units=[(t,False) for dim in TEMPLATES.values() for t in dim]+[(f'sham-{d}',True) for d in TEMPLATES]
        for ui,(unit,sham) in enumerate(units):
            if (case,unit) in selected: continue
            template=unit[5:] if sham else unit
            dim=template if sham else next(d for d,ts in TEMPLATES.items() if template in ts)
            field=TARGET_FIELD[dim]
            passed=None
            prior_attempts={int(x.get('attempt',0)) for x in existing_by.get((case,unit),[]) if isinstance(x.get('attempt'),int)}
            if len(prior_attempts)>=3:
                print(f"{case} {unit} EXHAUSTED from prior run",flush=True)
                continue
            start_attempt=max(prior_attempts,default=0)+1
            for attempt in range(start_attempt,4):
                rec={'timestamp':now(),'case_id':case,'context_id':row['context_id'],'source_answer_sha256':row.get('source_answer_sha256',sha256_obj(clean)),'replacement_round':row.get('replacement_round',0),'unit':unit,'dimension':dim,'template':template if not sham else None,'sham':sham,'attempt':attempt,'editor_model':MODEL_EDITOR}
                try:
                    last_editor_error=None
                    for format_try in range(1,4):
                        try:
                            raw=call(MODEL_EDITOR,editor_prompt(ctx,clean,template,sham,attempt),max_tokens=1000,temperature=0,anthropic=True); patch=extract_json(raw); break
                        except Exception as e:
                            last_editor_error=e
                            if format_try<3: time.sleep(2*format_try)
                    else: raise last_editor_error
                    rec['editor_raw']=raw
                    rec['editor_format_tries']=format_try; rec['patch']=patch
                    edited=apply_patch(clean,field,patch); rec['edited_answer']=edited
                    mech=mechanical(clean,edited,field,patch); rec['mechanical']=mech
                    if mech['status']=='pass':
                        sems=[]
                        for vm in (MODEL_V1,MODEL_V2):
                            try:
                                vr=call_json(vm,semantic_prompt(ctx,clean,edited,template,sham),max_tokens=1600); sems.append({'model':vm,'result':vr,'pass':validator_ok(vr,template,sham)})
                            except Exception as e: sems.append({'model':vm,'error':str(e),'pass':False})
                        rec['semantic']=sems
                        sem_pass=[x.get('pass') is True for x in sems]
                        if len(sems)==2 and sem_pass[0] != sem_pass[1]:
                            try:
                                tr=call_json(MODEL_TIE,semantic_prompt(ctx,clean,edited,template,sham),max_tokens=1600); rec['tie_break']={'model':MODEL_TIE,'result':tr,'pass':validator_ok(tr,template,sham)}
                                semantic_pass=rec['tie_break']['pass'] is True
                            except Exception as e: rec['tie_break']={'model':MODEL_TIE,'error':str(e),'pass':False}; semantic_pass=False
                        else: semantic_pass=len(sems)==2 and all(sem_pass)
                        rec['semantic_pass']=semantic_pass
                        if semantic_pass:
                            seed=(ri*100+ui+args.seed)%100000
                            nprompt,a_first=naturalness_prompt(clean,edited,seed)
                            nvals=[]
                            for vm in (MODEL_V1,MODEL_V2):
                                try:
                                    nr=call_json(vm,nprompt,max_tokens=1000); nvals.append({'model':vm,'result':nr,'pass':nr.get('a_serious') is True and nr.get('b_serious') is True and nr.get('obvious_edit_artifact') is False and nr.get('style_or_length_imbalance') is False})
                                except Exception as e: nvals.append({'model':vm,'error':str(e),'pass':False})
                            natural_passes=[x.get("pass") is True for x in nvals]
                            rec["naturalness"]={"a_first":a_first,"validators":nvals}
                            if len(nvals)==2 and natural_passes[0] != natural_passes[1]:
                                try:
                                    nr=call_json(MODEL_TIE,nprompt,max_tokens=1000); nt={"model":MODEL_TIE,"result":nr,"pass":nr.get("a_serious") is True and nr.get("b_serious") is True and nr.get("obvious_edit_artifact") is False and nr.get("style_or_length_imbalance") is False}; rec["naturalness"]["tie_break"]=nt; rec["naturalness_pass"]=nt["pass"] is True
                                except Exception as e: rec["naturalness"]["tie_break"]={"model":MODEL_TIE,"error":str(e),"pass":False}; rec["naturalness_pass"]=False
                            else: rec["naturalness_pass"]=len(nvals)==2 and all(natural_passes)
                        else: rec['naturalness_pass']=False
                    else: rec['semantic_pass']=False; rec['naturalness_pass']=False
                    rec['selected']=rec.get('mechanical',{}).get('status')=='pass' and rec.get('semantic_pass') is True and rec.get('naturalness_pass') is True
                except Exception as e: rec['error']=str(e); rec['selected']=False
                append_jsonl(candidate_path,rec)
                if rec.get('selected'):
                    selected[(case,unit)]=rec; passed=rec; break
                print(f"{case} {unit} attempt={attempt} rejected",flush=True)
            if passed is None: print(f"{case} {unit} REJECTED after 3 attempts",flush=True)
            else: print(f"{case} {unit} PASS",flush=True)
    selected_rows=list(selected.values()); write_json(run_out/'construction_report.json',{'updated_at':now(),'shard_index':args.shard_index,'shard_count':args.shard_count,'cases':len(rows),'units_expected':len(rows)*9,'units_selected':len(selected_rows),'complete':len(selected_rows)==len(rows)*9,'models':{'editor':MODEL_EDITOR,'validators':[MODEL_V1,MODEL_V2],'tie_break':MODEL_TIE},'rejections_by_unit':sorted([f'{r[0]}/{r[1]}' for r in {(x['case_id'],x['unit']):x for x in read_jsonl(candidate_path)}.keys() if (r not in selected)] )})
    print(json.dumps({'shard':f'{args.shard_index}/{args.shard_count}','selected':len(selected_rows),'expected':len(rows)*9,'complete':len(selected_rows)==len(rows)*9},ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('command',choices=['construct']); ap.add_argument('--seed',type=int,default=2026072101); ap.add_argument('--limit-cases',type=int,default=20); ap.add_argument('--shard-count',type=int,default=1); ap.add_argument('--shard-index',type=int,default=0); ap.add_argument('--base-file',default=str(BASE/'base_answers.jsonl')); ap.add_argument('--run-out',default=str(OUT)); a=ap.parse_args(); construct(a)
