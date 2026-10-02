"""Exact group join into a private dump; byte146 was padding, row size stays152."""
import collections,json,shutil
import numpy as np
from study import ROOT,DUMP,MAN,DT,GROUP,dump

def main():
    dst=ROOT/'dump_ext';dst.mkdir(exist_ok=True);man=json.loads(json.dumps(MAN));man['fields'].append({'name':'residual_crossing_verified','type':'u8'})
    counts=[];kd=np.dtype([(k,DT[k]) for k in GROUP]);total=0
    for kind,info in man['kinds'].items():
        src=DUMP/info['file'];dest=dst/info['file'];shutil.copyfile(src,dest)
        mm=dump(kind);out=np.memmap(dest,dtype='u1',mode='r+',shape=(len(mm),DT.itemsize));out[:,146]=0
        if (ROOT/f'side_{kind}.npy').exists():
            side=np.load(ROOT/f'side_{kind}.npy');sk=np.empty(len(side),kd)
            for f in GROUP:sk[f]=side[f]
            order=np.argsort(sk);sk=sk[order];sf=(side['status'][order]==1).astype('u1')
        else:side=None
        assign=np.memmap(f'output/scratch-3-11/classify_new/assign_{kind}.u16',dtype='<u2',mode='r');ct=collections.Counter();groups=collections.defaultdict(set)
        for lo in range(0,len(mm),250000):
            b=mm[lo:lo+250000];keys=np.empty(len(b),kd)
            for f in GROUP:keys[f]=b[f]
            if side is not None and len(side):
                pos=np.searchsorted(sk,keys);pc=np.minimum(pos,len(sk)-1);ok=(pos<len(sk))&(sk[pc]==keys);flag=np.where(ok,sf[pc],0)
                out[lo:lo+len(b),146]=flag
            else:flag=np.zeros(len(b),'u1')
            residual=assign[lo:lo+len(b)]==65535
            for level,typ in np.unique(np.column_stack([b['level'][residual],b['code'][residual]]),axis=0):
                mask=residual&(b['level']==level)&(b['code']==typ)
                ct[int(level),int(typ),'moved']+=int((mask&(flag==1)).sum());ct[int(level),int(typ),'remaining']+=int((mask&(flag==0)).sum())
            # Every pre-existing byte except the newly populated padding byte must remain identical.
            original=np.asarray(b).view('u1').reshape(-1,DT.itemsize)
            assert np.array_equal(out[lo:lo+len(b),:146],original[:,:146])
            assert np.array_equal(out[lo:lo+len(b),147:],original[:,147:])
        out.flush();del out
        info['fields']=man['fields'];info['row_size']=DT.itemsize
        for (level,typ,what),rows in sorted(ct.items()):counts.append({'kind':kind,'level':level,'type':typ,'outcome':what,'rows':rows})
        total+=sum(n for (l,t,w),n in ct.items() if w=='moved');print('EXTENDED',kind,'moved',sum(n for (l,t,w),n in ct.items() if w=='moved'),flush=True)
    man['extension_3_12']={'source':str(DUMP),'side_tables':str(ROOT/'side_<kind>.npy'),'new_field':'residual_crossing_verified','offset':146,'row_size':152,'other_bytes_unchanged':True,'predicate':'status==1: unique exact original producer; not E1 cover; explicit closed ring; longest closing edge has proper nonadjacent crossing','first_matching_rule_preserved':True}
    (dst/'dump_manifest.json').write_text(json.dumps(man,indent=2)+'\n');(ROOT/'joined_counts.json').write_text(json.dumps({'strata':counts,'moved_spool':total},indent=2)+'\n');print('MOVED',total,flush=True)
if __name__=='__main__':main()
