"""Independent numpy witness. No quantisation_roundtrip/K1 imports.

All shapes of each level are cached directly from the immutable original spool.
Bounding-box lower bounds prune nearest search only after obtaining a finite
upper bound; no radius/window/tall selection is used. Same-level all-type search
includes every outline; interiors are evaluated per class-2 polygon.
"""
import argparse, csv, json, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, 'parser')
from kiwiw.spool import SpoolReader
from kiwiw.mesh import CellGrid

ROOT = Path('output/scratch-3-07')
DUMP = Path('output/scratch-3-03/dump')
GROUP = ('level','ix','iy','code','p0','p1','p2','p3','p4','p5','p6','shape')
MD = np.dtype([('off','i8'),('n','i4'),('type','i4'),('cls','i4'),
               ('hx','i4'),('hy','i4'),('rec','i4'),('xmin','f8'),('xmax','f8'),
               ('ymin','f8'),('ymax','f8')])
NEAR = .500001

def raw(level, lon, lat):
    g=CellGrid.from_reference(int(level))
    wlo=g.disc_lon_span/2-180
    x=(np.mod(np.asarray(lon)-g.disc_lon_lo-wlo,360)+wlo)/g.cell_lon*4096
    y=(np.asarray(lat)-g.disc_lat_lo)/g.cell_lat*4096
    return x,y

def dump(kind):
    doc=json.loads((DUMP/'dump_manifest.json').read_text())
    ts={'f64':'<f8','i32':'<i4','u16':'<u2','u8':'u1'}
    dt=np.dtype([(f['name'],ts[f['type']]) for f in doc['fields']],align=True)
    assert dt.itemsize==144
    return np.memmap(DUMP/doc['kinds'][kind]['file'],dtype=dt,mode='r')

def cache(level):
    dest=ROOT/f'all_spool_L{level}'
    if (dest/'done.json').exists(): return
    dest.mkdir(exist_ok=True)
    rd=SpoolReader('output/extract_timing/spool'); idx=rd._load_idx(level)
    nv=ns=0; start=time.monotonic()
    with (dest/'xy.bin').open('wb') as fxy,(dest/'meta.bin').open('wb') as fm:
        for a in range(0,idx.n,512):
            parts=list(rd.iter_cell_columns(level,a,min(a+512,idx.n)))
            parts=[p for p in parts if len(p[2]['b_type'])]
            if not parts: continue
            cols=[p[2] for p in parts]
            lens=np.concatenate([c['b_nstored'] for c in cols])
            x,y=raw(level,np.concatenate([c['c_lon'] for c in cols]),np.concatenate([c['c_lat'] for c in cols]))
            xy=np.column_stack((x,y)); xy.tofile(fxy)
            m=np.zeros(len(lens),MD); off=np.r_[0,np.cumsum(lens)[:-1]]
            m['off']=off+nv; m['n']=lens
            m['type']=np.concatenate([c['b_type'] for c in cols]); m['cls']=np.concatenate([c['b_class'] for c in cols])
            per=[len(c['b_type']) for c in cols]
            m['hx']=np.repeat([p[0] for p in parts],per); m['hy']=np.repeat([p[1] for p in parts],per)
            m['rec']=np.concatenate([np.arange(n) for n in per])
            for name,ar,op in [('xmin',x,np.minimum),('xmax',x,np.maximum),('ymin',y,np.minimum),('ymax',y,np.maximum)]:
                m[name]=np.nan
                nz=lens>0
                if nz.any(): m[name][nz]=op.reduceat(ar,off[nz])
            m.tofile(fm); nv+=len(x); ns+=len(m)
            if a%16384==0: print('CACHE',level,a,idx.n,ns,nv,flush=True)
    rd.close()
    (dest/'done.json').write_text(json.dumps({'level':level,'cells':idx.n,'shapes':ns,'vertices':nv,'wall_s':time.monotonic()-start},indent=2))
    print('CACHE DONE',level,ns,nv,flush=True)

class AllShapes:
    def __init__(self,level):
        cache(level); p=ROOT/f'all_spool_L{level}'
        self.m=np.memmap(p/'meta.bin',dtype=MD,mode='r')
        self.xy=np.memmap(p/'xy.bin',dtype='<f8',mode='r').reshape(-1,2)
        self.trees={}
    def tree(self,typ=None):
        if typ in self.trees:return self.trees[typ]
        ids=np.flatnonzero((self.m['n']>0) & (True if typ is None else self.m['type']==typ))
        starts=np.arange(0,len(ids),128)
        boxes=np.empty((len(starts),4))
        for k,(name,op) in enumerate([('xmin',np.minimum),('xmax',np.maximum),('ymin',np.minimum),('ymax',np.maximum)]):
            boxes[:,k]=op.reduceat(self.m[name][ids],starts)
        self.trees[typ]=(ids,starts,boxes)
        return self.trees[typ]
    @staticmethod
    def lower(boxes,px,py):
        return np.maximum(np.maximum(np.maximum(boxes[:,0]-px,px-boxes[:,1]),0),
                          np.maximum(np.maximum(boxes[:,2]-py,py-boxes[:,3]),0))
    def coords(self,s):
        m=self.m[s]; return self.xy[int(m['off']):int(m['off'])+int(m['n'])]
    def edges(self,s):
        xy=self.coords(s)
        if len(xy)<2: return xy,xy
        return (xy,np.roll(xy,-1,axis=0)) if self.m[s]['cls']==2 else (xy[:-1],xy[1:])
    def pip(self,s,px,py):
        a,b=self.edges(s)
        if len(a)<3 or self.m[s]['cls']!=2: return False,0
        crosses=(a[:,1]>py)!=(b[:,1]>py)
        aa=a[crosses]; bb=b[crosses]
        if not len(aa): return False,0
        xi=aa[:,0]+(py-aa[:,1])*(bb[:,0]-aa[:,0])/(bb[:,1]-aa[:,1])
        right=xi>px
        winding=int(np.sum(np.where(bb[:,1]>aa[:,1],1,-1)[right]))
        return bool(np.count_nonzero(right)%2),winding
    def inside(self,px,py,typ=None):
        ids,starts,boxes=self.tree(typ)
        nodes=np.flatnonzero(self.lower(boxes,px,py)==0)
        eo=wn=False; owners=[]; disagreement=[]
        for node in nodes:
            subset=ids[starts[node]:starts[node]+128];m=self.m[subset]
            mask=(m['cls']==2)&(m['xmin']<=px)&(m['xmax']>=px)&(m['ymin']<=py)&(m['ymax']>=py)
            for s in subset[mask]:
                e,w=self.pip(s,px,py); eo|=e; wn|=w!=0
                if e or w: owners.append(int(s))
                if e!=(w!=0): disagreement.append(int(s))
        return bool(eo),bool(wn),owners,disagreement
    def distance(self,s,px,py):
        a,b=self.edges(s)
        if not len(a): return float('inf')
        # L-infinity segment minimum occurs at an endpoint, a zero residual,
        # or equality of the two absolute residuals. Evaluate those six cases.
        z=a-np.array([px,py]); v=b-a
        d=np.minimum(np.max(np.abs(z),axis=1),np.max(np.abs(z+v),axis=1))
        for num,den in [(-z[:,0],v[:,0]),(-z[:,1],v[:,1]),
                        (z[:,1]-z[:,0],v[:,0]-v[:,1]),
                        (-z[:,0]-z[:,1],v[:,0]+v[:,1])]:
            t=np.divide(num,den,out=np.zeros_like(num),where=den!=0)
            t=np.clip(t,0,1)
            d=np.minimum(d,np.max(np.abs(z+t[:,None]*v),axis=1))
        return float(d.min())
    def nearest(self,px,py,typ=None):
        ids,starts,boxes=self.tree(typ)
        lb=self.lower(boxes,px,py);order=np.argsort(lb,kind='stable')
        best=float('inf');owner=-1
        for node in order:
            if lb[node]>best:break
            subset=ids[starts[node]:starts[node]+128];m=self.m[subset]
            bb=np.column_stack([m[k] for k in ('xmin','xmax','ymin','ymax')])
            sublb=self.lower(bb,px,py)
            for j in np.argsort(sublb,kind='stable'):
                if sublb[j]>best:break
                s=int(subset[j]);d=self.distance(s,px,py)
                if d<best:best=d;owner=s
        return best,owner
    def query(self,r,kind):
        x,y=raw(int(r['level']),r['lon'],r['lat']); x=float(np.rint(x));y=float(np.rint(y))
        t=int(r['code']);eo,wn,own,dis=self.inside(x,y,t)
        ae,aw,ao,ad=self.inside(x,y)
        ds,ss=self.nearest(x,y,t);da,sa=self.nearest(x,y)
        def ident(s):
            if s<0:return None
            m=self.m[s];return {k:int(m[k]) for k in ('hx','hy','rec','type','cls','n')}
        return {'kind':kind,'key':[int(r[k]) for k in GROUP],'vert':int(r['vert']),
                'x':x,'y':y,'eo_same':eo,'wn_same':wn,'eo_any':ae,'wn_any':aw,
                'd_same':ds,'d_any':da,'nearest_same':ident(ss),'nearest_any':ident(sa),
                'eo_owners':[ident(s) for s in own], 'parity_winding_disagree':[ident(s) for s in dis],
                'dump_onb':int(r['onb']),'dump_eo_same':int(r['in_eo_same']),
                'dump_d_src':float(r['d_src']) if np.isfinite(r['d_src']) else None,
                'valid':bool(eo if kind=='background' else ds<=NEAR)}

def sample_rows(mm,mask,n=200):
    # First failing vertex (minimum vert) of each group; enumerate's key order.
    ids=np.flatnonzero(mask)
    key=np.empty(len(ids),dtype=[(k,mm.dtype[k]) for k in GROUP])
    for k in GROUP:key[k]=mm[k][ids]
    u,inv=np.unique(key,return_inverse=True)
    order=np.lexsort((ids,mm['vert'][ids],inv))
    first=order[np.r_[True,inv[order][1:]!=inv[order][:-1]]]
    k=max(1,len(u)//n)
    offset=int(np.random.default_rng(20260930).integers(0,k))
    sel=first[offset::k][:n] if len(first)>n else first
    return ids[sel],len(u)

def run_probe():
    log=[]
    for level in (0,2,6):
        sh=AllShapes(level)
        for kind in ('background','background_boundary'):
            mm=dump(kind)
            for typ in np.unique(mm['code'][mm['level']==level]):
                mask=(mm['level']==level)&(mm['code']==typ)&(mm['src_ix']==-2147483648)
                if not mask.any():continue
                ids,ng=sample_rows(mm,mask,200)
                out=ROOT/f'sentinel_{kind}_L{level}_T{typ}.jsonl'
                counts={'rows':int(mask.sum()),'groups':ng,'sample':len(ids),'valid':0,'eo':0,'wn':0,'d_same_gt64':0,'d_any_gt64':0,'diagnostic_inside_disagreements':0}
                saved=[json.loads(line) for line in out.read_text().splitlines()] if out.exists() else []
                if len(saved)!=len(ids):saved=[]
                with out.open('w') as fh:
                    for j,i in enumerate(ids):
                        q=saved[j] if saved else sh.query(mm[i],kind);q['row_index']=int(i);fh.write(json.dumps(q)+'\n');fh.flush()
                        counts['valid']+=q['valid'];counts['eo']+=q['eo_same'];counts['wn']+=q['wn_same']
                        counts['d_same_gt64']+=q['d_same']>64;counts['d_any_gt64']+=q['d_any']>64
                        counts['diagnostic_inside_disagreements']+=q['eo_same']!=q['dump_eo_same']
                        if (j+1)%50==0:print('PROBE',kind,level,int(typ),j+1,flush=True)
                entry={'kind':kind,'level':level,'type':int(typ),**counts};log.append(entry);print(json.dumps(entry),flush=True)
        del sh
    (ROOT/'sentinel_results.json').write_text(json.dumps(log,indent=2))

def witness_rule(rid,assign_dir):
    adir=Path(assign_dir)
    rules=json.loads((adir/'rules.json').read_text())['rules']
    ri=next(i for i,r in enumerate(rules) if r['id']==rid);rule=rules[ri];kind=rule['kind']
    enum=ROOT/f'enumerate_{rid}.tsv'
    rows=list(csv.DictReader(enum.open(),delimiter='\t'))
    keys=sorted(tuple(int(r['type' if k=='code' else k]) for k in GROUP) for r in rows)
    n=len(keys);stride=max(1,n//200);offset=int(np.random.default_rng(20260930).integers(0,stride))
    selected=keys[offset::stride][:200] if n>200 else keys
    mm=dump(kind);assign=np.memmap(adir/f'assign_{kind}.u16',dtype='<u2',mode='r')
    dt=np.dtype([(k,mm.dtype[k]) for k in GROUP]);wanted=np.zeros(len(selected),dt)
    for j,key in enumerate(selected):
        for k,v in zip(GROUP,key):wanted[k][j]=v
    found={}
    for lo in range(0,len(mm),500000):
        a=np.flatnonzero(assign[lo:lo+500000]==ri)+lo
        if not len(a):continue
        ks=np.empty(len(a),dt)
        for k in GROUP:ks[k]=mm[k][a]
        a=a[np.isin(ks,wanted)]
        for i in a:
            key=tuple(int(mm[i][k]) for k in GROUP)
            if key not in found or (mm[i]['vert'],i)<(mm[found[key]]['vert'],found[key]):found[key]=int(i)
    assert len(found)==len(selected),(len(found),len(selected))
    outputs=[];shapes={}
    for key in selected:
        i=found[key];lev=key[0]
        if lev not in shapes:shapes[lev]=AllShapes(lev)
        q=shapes[lev].query(mm[i],kind);q['row_index']=i;outputs.append(q)
        if len(outputs)%50==0:print('WITNESS',rid,len(outputs),flush=True)
    valid=sum(q['valid'] for q in outputs);expected=rule['cause']=='checker'
    agree=sum(q['valid']==expected for q in outputs)
    result={'rule_id':rid,'cause':rule['cause'],'kind':kind,'groups':n,'sample':len(outputs),
            'valid':valid,'invalid':len(outputs)-valid,'agreement':agree,
            'passes':agree==len(outputs),'seed':20260930,'stride':stride,'offset':offset,
            'criterion':'same-type even-odd interior' if kind=='background' else 'same-type outline Chebyshev distance <= 0.500001 raw',
            'all_shapes_by_level':{str(l):len(s.m) for l,s in shapes.items()},
            'enumeration':str(enum),'assignment':str(adir),'points':'row-specific lat/lon converted to global raw and rounded to nearest integer, matching the verdict query point'}
    with (ROOT/f'witness_{rid}.jsonl').open('w') as fh:
        for q in outputs:fh.write(json.dumps(q)+'\n')
    (ROOT/f'witness_{rid}.txt').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('rule',nargs='?',default='sentinel')
    ap.add_argument('--assign',default=str(ROOT/'classify_bg'));args=ap.parse_args()
    if args.rule=='sentinel':
        if not (ROOT/'sentinel_results.json').exists():run_probe()
    else:witness_rule(args.rule,args.assign)
