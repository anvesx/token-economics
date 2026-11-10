"""Anneal node positions per stage against the same geometry chk_layout.py uses."""
import random, math
NW,NH,CP,RP,M,T=170,64,300,196,150,70
def wrap(t,mx):
    ls=[];cur=''
    for w in t.split():
        if len((cur+' '+w).strip())>mx:
            if cur: ls.append(cur)
            cur=w
        else: cur=(cur+' '+w).strip()
    if cur: ls.append(cur)
    return ls
def inter(p1,p2,p3,p4):
    def o(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    return o(p3,p4,p1)*o(p3,p4,p2)<0 and o(p1,p2,p3)*o(p1,p2,p4)<0
def segrect(a,b,r):
    x0,y0,w,h=r
    n=int(max(abs(a[0]-b[0]),abs(a[1]-b[1]))/4)+2
    for i in range(n+1):
        x=a[0]+(b[0]-a[0])*i/n;y=a[1]+(b[1]-a[1])*i/n
        if x0<x<x0+w and y0<y<y0+h: return True
    return False
def cost(nodes,edges,comps):
    P=lambda n:(M+n["c"]*CP,T+n["r"]*RP)
    gx=lambda c:M+c*CP
    N={n["id"]:n for n in nodes}
    side=lambda n,s:(lambda p:{'left':(p[0]-NW/2,p[1]),'right':(p[0]+NW/2,p[1])}[s])(P(n))
    paths=[];lane={}
    for e in edges:
        a,b=N[e["a"]],N[e["b"]];pa,pb=P(a),P(b)
        dc,dr=b["c"]-a["c"],b["r"]-a["r"]
        if dr==0:
            sa='right' if dc>0 else 'left';sb='left' if dc>0 else 'right';pts=[side(a,sa),side(b,sb)]
        elif dc==0:
            k=lane.get(a["c"],0);lane[a["c"]]=k+1;sgn=1 if k%2==0 else -1
            lx=gx(a["c"])+sgn*(NW/2+(CP-NW)/2-6+6*(k//2));s='right' if sgn>0 else 'left'
            pts=[side(a,s),(lx,pa[1]),(lx,pb[1]),side(b,s)]
        else:
            sa='right' if dc>0 else 'left';sb='left' if dc>0 else 'right'
            s0,s1=side(a,sa),side(b,sb);xmid=pb[0]-(1 if dc>0 else -1)*(NW/2+(CP-NW)/2)
            pts=[s0,(xmid,s0[1]),(xmid,s1[1]),s1]
        paths.append((e,pts))
    obs={}
    for n in nodes:
        p=P(n);rs=[(p[0]-NW/2,p[1]-NH/2,NW,NH)]
        if not n["ghost"]:
            c=comps[n["base"]];rows=sn=0
            for ln in (c.get("line") or "").split("\n"):
                rows+=min(2,len(wrap(ln,54)));sn+=1
            if rows: rs.append((p[0]-132,p[1]+NH/2+3,264,rows*11.5+sn*3+4))
        obs[n["id"]]=rs
    nh=nx=0;L=0
    for e,pts in paths:
        for i in range(len(pts)-1):
            L+=abs(pts[i][0]-pts[i+1][0])+abs(pts[i][1]-pts[i+1][1])
            for nid,rs in obs.items():
                if nid in (e["a"],e["b"]): continue
                for r in rs:
                    if segrect(pts[i],pts[i+1],r): nh+=1
    for i in range(len(paths)):
        for j in range(i+1,len(paths)):
            for u in range(len(paths[i][1])-1):
                for v in range(len(paths[j][1])-1):
                    if inter(paths[i][1][u],paths[i][1][u+1],paths[j][1][v],paths[j][1][v+1]): nx+=1
    return nh,nx,L
def total(nodes,edges,comps):
    h,x,L=cost(nodes,edges,comps); return 1000*h+30*x+L/200,h,x
def anneal(st,comps,iters=3000,seed=1):
    rnd=random.Random(seed)
    nodes,edges=st["nodes"],st["edges"]
    mem=[n for n in nodes if not n["ghost"]]; gh=[n for n in nodes if n["ghost"]]
    inb={n["id"]:0 for n in gh}; outb={n["id"]:0 for n in gh}
    for e in edges:
        if e["a"] in inb: outb[e["a"]]+=1
        if e["b"] in inb: inb[e["b"]]+=1
    for n in gh: n["c"]=0 if outb[n["id"]]>=inb[n["id"]] else 5
    R=max(3,math.ceil(len(mem)/3)+1)
    # members: cols 1..4, ghosts: col 0 or 5
    def free(cells,c0,c1):
        return [(c,r) for c in range(c0,c1+1) for r in range(R+len(gh)) if (c,r) not in cells]
    for n in mem: n["c"]=1+nodes.index(n)%4; n["r"]=nodes.index(n)//4
    used=set()
    for n in mem:
        while (n["c"],n["r"]) in used: n["r"]+=1
        used.add((n["c"],n["r"]))
    for n in gh:
        r=0
        while (n["c"],r) in used: r+=1
        n["r"]=r; used.add((n["c"],r))
    cur,h,x=total(nodes,edges,comps);best=(cur,[(n["c"],n["r"]) for n in nodes])
    T0=60.0
    for it in range(iters):
        t=T0*(1-it/iters)+0.01
        n=rnd.choice(nodes); old=(n["c"],n["r"])
        lo,hi=(1,4) if not n["ghost"] else (n["c"],n["c"])
        if rnd.random()<0.5:
            m=rnd.choice([q for q in nodes if q is not n and q["ghost"]==n["ghost"] and (n["ghost"]==False or q["c"]==n["c"])] or [None])
            if m is None: continue
            oldm=(m["c"],m["r"]); n["c"],n["r"],m["c"],m["r"]=m["c"],m["r"],n["c"],n["r"]
            if n["ghost"]==False and False: pass
            new=total(nodes,edges,comps)
            if new[0]<=cur or rnd.random()<math.exp((cur-new[0])/t): cur,h,x=new
            else: n["c"],n["r"],m["c"],m["r"]=old[0],old[1],oldm[0],oldm[1]
        else:
            occ={(q["c"],q["r"]) for q in nodes}
            c=rnd.randint(lo,hi); r=rnd.randint(0,R+len(gh))
            if (c,r) in occ: continue
            n["c"],n["r"]=c,r
            new=total(nodes,edges,comps)
            if new[0]<=cur or rnd.random()<math.exp((cur-new[0])/t): cur,h,x=new
            else: n["c"],n["r"]=old
        if cur<best[0]: best=(cur,[(q["c"],q["r"]) for q in nodes])
    for q,(c,r) in zip(nodes,best[1]): q["c"],q["r"]=c,r
    # compact empty rows
    rows=sorted({q["r"] for q in nodes}); mp={r:i for i,r in enumerate(rows)}
    for q in nodes: q["r"]=mp[q["r"]]
    return total(nodes,edges,comps)
