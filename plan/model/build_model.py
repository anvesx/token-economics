#!/usr/bin/env python3
"""Merge skeleton + cards + reqs -> model.json, run the schema gate, write the viewer HTML."""
import json, glob, re, sys, os
from collections import Counter
import skeleton as S, meta as M
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'drill_template.html')
OUT_HTML = os.path.join(ROOT, 'plan', 'token-economics-lld.html')
errs = []
def err(m): errs.append(m)

cards, reqs = {}, []
for f in sorted(glob.glob('cards/*.json')): cards.update(json.load(open(f)))
for f in sorted(glob.glob('reqs/*.json')): reqs += json.load(open(f))

# refs from corpus headers
def corpus_ref(sid):
    side, n = sid.split(':'); d = 'research' if side == 'A' else 'research-cli-agents'
    p = os.path.join(ROOT, d, 'corpus', f'{n}.txt')
    if not os.path.exists(p): return None
    t = u = ''
    for ln in open(p, errors='ignore').read().split('\n')[:4]:
        if ln.startswith('TITLE:'): t = ln[6:].strip()
        if ln.startswith('URL:'): u = ln[4:].strip()
    return {'cite': f'{sid} {t}'[:150], 'url': u or '#', 'topic': 'API-side research' if side == 'A' else 'CLI-agent research'}
refs, refidx = [], {}
def R(sid):
    if sid not in refidx:
        r = corpus_ref(sid)
        if not r: err(f'bad source id {sid}'); return None
        refidx[sid] = len(refs); refs.append(r)
    return refidx[sid]

comps = {}
for cid, (label, sub, kind) in S.C.items():
    stage = group = None
    for st, gid, gt, mem in S.GROUPS:
        if cid in mem: stage, group = st, gid
    c = cards.get(cid)
    if not c: err(f'no card for {cid}'); c = {}
    for k in ('inn','out','store','fail','req','dumb','line'):
        if not c.get(k): err(f'{cid}: missing {k}')
    if not c.get('src'): err(f'{cid}: card without a source')
    d = dict(label=label, sub=sub, kind=kind, stage=stage, group=group,
             inn=c.get('inn',''), out=c.get('out',''), store=c.get('store',''), fail=c.get('fail',''),
             req=c.get('req','') + ('  Sources: ' + ', '.join(c.get('src', [])) if c.get('src') else ''),
             prop=c.get('prop',''), hard=c.get('hard',''), line=c.get('line',''), dumb=c.get('dumb',''))
    dp = c.get('deep')
    if dp:
        dp = dict(dp)
        dp['refs'] = [i for i in (R(s) for s in c.get('src', [])) if i is not None]
        for p in dp.get('papers', []): p['ref'] = R(p['ref'])
        for p in dp.get('repos', []): p['ref'] = R(p['ref'])
        dp['papers'] = [p for p in dp.get('papers', []) if p['ref'] is not None]
        dp['repos'] = [p for p in dp.get('repos', []) if p['ref'] is not None]
        d['deep'] = dp
    else: err(f'{cid}: no deep card')
    comps[cid] = d

stages = []
for sid, n, role, title, blurb in S.STAGES:
    groups = [dict(id=g, title=t, members=mem, line=M.GT[g][0], dumb=M.GT[g][1]) for st, g, t, mem in S.GROUPS if st == sid]
    mem = [m for g in groups for m in g['members']]
    nodes = [dict(id=m, base=m, c=i % 4, r=i // 4, ghost=False) for i, m in enumerate(mem)]
    ms = set(mem); edges = []; gh = {}
    def gid(x):
        k = 'g:%s/%s' % (comps[x]['stage'], comps[x]['group'])
        if k not in gh:
            gh[k] = dict(id=k, gk=[comps[x]['stage'], comps[x]['group']], ghost=True, c=4, r=len(gh))
        return k
    seen = set()
    for a, b, l, k, d_ in S.E:
        if a not in ms and b not in ms: continue
        na = a if a in ms else gid(a); nb = b if b in ms else gid(b)
        if (na, nb, l) in seen: continue
        seen.add((na, nb, l)); edges.append(dict(a=na, b=nb, ra=a, rb=b, l=l, k=k, d=d_))
    nodes += list(gh.values())
    stages.append(dict(id=sid, n=n, role=role, title=title, blurb=blurb, nodes=nodes, edges=edges, frames=[], groups=groups))

import layout
import json as _j, os as _o
_cf = 'layout_cache.json'
_cache = _j.load(open(_cf)) if _o.path.exists(_cf) else {}
for st_ in stages:
    key = st_['id']; sig = _j.dumps([(n['id'], n['ghost']) for n in st_['nodes']] + [(e['a'], e['b'], e['l']) for e in st_['edges']])
    c_ = _cache.get(key)
    if c_ and c_['sig'] == sig and c_['h'] == 0 and c_['x'] == 0:
        for n in st_['nodes']: n['c'], n['r'] = c_['pos'][n['id']]
        continue
    for seed in range(1, 9):
        res = layout.anneal(st_, comps, iters=2500, seed=seed)
        if res[1] == 0 and res[2] == 0: break
    print('layout', key, 'seed', seed, 'hits', res[1], 'x', res[2])
    _cache[key] = dict(sig=sig, h=res[1], x=res[2], pos={n['id']: [n['c'], n['r']] for n in st_['nodes']})
_j.dump(_cache, open(_cf, 'w'))

# ---- schema gate
ids = set(comps)
for a, b, *_ in S.E:
    if a not in ids or b not in ids: err(f'dangling edge {a}->{b}')
deg = Counter()
for a, b, *_ in S.E: deg[a] += 1; deg[b] += 1
for c in ids:
    if deg[c] == 0: err(f'orphan component {c}')
inm = Counter(m for _, _, _, mem in S.GROUPS for m in mem)
for c in ids:
    if inm[c] != 1: err(f'{c} in {inm[c]} groups')
rq_ids = [r['id'] for r in reqs]
if len(rq_ids) != len(set(rq_ids)): err('duplicate requirement ids')
covered = set()
for r in reqs:
    for c in r['comps']:
        if c not in ids: err(f"{r['id']}: unknown comp {c}")
        covered.add(c)
    for s in r['src']:
        if corpus_ref(s) is None: err(f"{r['id']}: bad src {s}")
    if r['label'] == 'sourced' and not r['src']: err(f"{r['id']}: sourced with no src")
for c in ids - covered: err(f'component {c} has no requirement row')
for cid, c in comps.items():
    for rid in re.findall(r'RQ-[A-D]-\d+', c['req']):
        if rid not in rq_ids: err(f'{cid} cites missing {rid}')

xc = [dict(id=x['id'], title=x['title'], blurb=x['blurb'], intro=x['intro'], sections=x['sections']) for x in M.XC]
kinds = {k: dict(fill=f, stroke=s, name=n) for k, (f, s, n) in S.KINDS.items()}
D = dict(stages=stages, comps=comps, kinds=kinds, xc=xc, refs=refs)
if errs:
    print('SCHEMA GATE FAILED', len(errs));
    for e in errs[:60]: print(' -', e)
    if '--force' not in sys.argv: sys.exit(1)
json.dump(D, open('model.json', 'w'), indent=1)
json.dump(reqs, open('../requirements.json', 'w'), indent=1)
html = open(TPL).read()
html = html.replace('ST Engineering Supplier Resilience - Drill-down LLD', 'Token Economics Cost Control Plane - Drill-down LLD')
html = html.replace('<div class="crumbs" style="margin-top:2px"><a href="st-eng-solution-lld-l8.html">Full single-page diagram →</a></div>', '')
html = html.replace('One signal, from arrival to decision', 'One request, from harness to backend and back to the ledger')
html = html.replace('Read-only and federated: models extract and explain, numbers come only from calculators and the simulator, and buyers execute in SAP. Pick a stage to go one level down.',
  'Token Economics sits between harnesses and backends. The gateway is the source of truth; hooks and telemetry only add detail. Pick a stage to go one level down.')
html = html.replace('Supporting stages, used by the flow above', 'Supporting stages')
html = html.replace('papers, docs and repositories behind the algorithms.', 'sources behind the cards.')
html = html.replace('const D = __DATA__;', 'const D = ' + json.dumps(D, ensure_ascii=False) + ';')
open(OUT_HTML, 'w').write(html)
n_e = sum(len(s['edges']) for s in stages)
print(f"OK stages={len(stages)} groups={len(S.GROUPS)} comps={len(comps)} edges={n_e} reqs={len(reqs)} refs={len(refs)} html={os.path.getsize(OUT_HTML)//1024}KB")
