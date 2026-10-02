"""Read-only dump measurement and random distinct-group samples; no validity oracle."""
import json, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, 'output/scratch-3-07')
from witness import GROUP
ROOT=Path('output/scratch-3-12'); DUMP=Path('output/scratch-3-11/dump_new_ext')
MAN=json.loads((DUMP/'dump_manifest.json').read_text())
TS={'f64':'<f8','i32':'<i4','u16':'<u2','u8':'u1'}
DT=np.dtype([(f['name'],TS[f['type']]) for f in MAN['fields']],align=True)
def dump(kind):
    return np.memmap(DUMP/MAN['kinds'][kind]['file'],dtype=DT,mode='r')
def hist(a):
    v,n=np.unique(a,return_counts=True)
    return {str(x.item()):int(y) for x,y in zip(v,n)}
def ranges(a):
    a=np.asarray(a); f=np.isfinite(a)
    return {'finite':int(f.sum()),'nan':int(np.isnan(a).sum()),'inf':int(np.isinf(a).sum()),
            'quantiles':np.quantile(a[f],[0,.01,.1,.5,.9,.99,1]).tolist() if f.any() else [],
            'le_tolerance':int((a<=.500001).sum()),'gt64_finite':int(((a>64)&f).sum())}
def main():
    rng=np.random.default_rng(2026100212); stats=[]; samples=[]; start=time.monotonic()
    allgroups=(ROOT/'residual_groups.jsonl').open('w')
    for kind in MAN['kinds']:
        mm=dump(kind); assign=np.memmap(Path('output/scratch-3-11/classify_new')/f'assign_{kind}.u16',dtype='<u2',mode='r')
        residual=assign==65535
        pairs=np.unique(np.column_stack((mm['level'][residual],mm['code'][residual])),axis=0)
        for level,typ in pairs:
            for sentinel in (False,True):
                mask=residual&(mm['level']==level)&(mm['code']==typ)&((mm['src_ix']==-2147483648)==sentinel)
                ids=np.flatnonzero(mask)
                if not len(ids):continue
                r=mm[ids]; kd=np.dtype([(k,DT[k]) for k in GROUP]); keys=np.empty(len(r),kd)
                for k in GROUP:keys[k]=r[k]
                u,first,inv=np.unique(keys,return_index=True,return_inverse=True)
                # Original dump order is canonical shape/vertex order; verify first vertex.
                assert np.all(r['vert'][first]>=-1)
                choose=np.sort(rng.choice(len(u),min(200,len(u)),replace=False)); chosen=ids[first[choose]]
                q={'kind':kind,'level':int(level),'type':int(typ),'sentinel':bool(sentinel),'rows':len(ids),'groups':len(u),'sample':len(chosen),
                   'onb':hist(r['onb']),'piece_nv':ranges(r['dnv']),'piece_nv_counts':hist(r['dnv']),
                   'source_nv':ranges(r['src_nv']),'d_same_censored_64':ranges(r['d_src']),
                   'd_any_censored_2':ranges(r['d_any']),'source_maxseg':ranges(r['src_maxseg']),
                   'eo_same':hist(r['in_eo_same']),'eo_any':hist(r['in_eo_any']),'any_type':hist(r['any_type']),
                   'depth':hist(r['depth']),'frame_x_1024':int((r['vx']%1024==0).sum()),
                   'frame_y_1024':int((r['vy']%1024==0).sum()),
                   'frame_both_1024':int(((r['vx']%1024==0)&(r['vy']%1024==0)).sum()),
                   'frame_end_0_4096':int((np.isin(r['vx'],[0,4096])|np.isin(r['vy'],[0,4096])).sum()),
                   'frame_interior':int(((r['vx']>0)&(r['vx']<4096)&(r['vy']>0)&(r['vy']<4096)).sum())}
                stats.append(q)
                for i in chosen:samples.append({'kind':kind,'row_index':int(i),'stratum':[kind,int(level),int(typ),bool(sentinel)],'key':[int(mm[k][i]) for k in GROUP]})
                for j in range(len(u)):
                    i=int(ids[first[j]])
                    allgroups.write(json.dumps({'kind':kind,'row_index':i,'stratum':[kind,int(level),int(typ),bool(sentinel)],'key':[int(u[k][j]) for k in GROUP]})+'\n')
                print('STRATUM',kind,int(level),int(typ),sentinel,'rows',len(ids),'groups',len(u),'sample',len(chosen),flush=True)
    allgroups.close()
    (ROOT/'column_study.json').write_text(json.dumps({'seed':2026100212,'selection':'uniform without replacement from unique full group keys, first failing vertex','stats':stats,'wall_s':time.monotonic()-start},indent=2)+'\n')
    with (ROOT/'samples.jsonl').open('w') as f:
        for s in samples:f.write(json.dumps(s)+'\n')
    print('DONE',len(samples),round(time.monotonic()-start,2),flush=True)
if __name__=='__main__':main()
