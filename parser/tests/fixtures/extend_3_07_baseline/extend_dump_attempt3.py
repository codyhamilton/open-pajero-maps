"""Join group-level producer witness to an owned extended dump for native classify.
Original bytes/fields remain unchanged; add only s02_producer_verified u8.
Unvisited and mixed-provenance groups are zero (unattributed), never a default cause.
"""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'output/scratch-3-07')
from witness import ROOT, DUMP, GROUP, dump

def main():
    side=np.load(ROOT/'side_background_boundary.npy');dest=ROOT/'dump_attempt3';dest.mkdir(exist_ok=True)
    manifest=json.loads((DUMP/'dump_manifest.json').read_text());extra={'name':'s02_producer_verified','type':'u8'};manifest['fields'].append(extra)
    old=dump('background_boundary').dtype;dt=np.dtype(old.descr+[('s02_producer_verified','u1')],align=True)
    # dtype.descr contains anonymous tail padding; construct from named fields to
    # preserve documented aligned layout and append after the original 144 bytes.
    kinds={'f64':'<f8','i32':'<i4','u16':'<u2','u8':'u1'};dt=np.dtype([(f['name'],kinds[f['type']]) for f in manifest['fields']],align=True)
    assert dt.fields['s02_producer_verified'][1]==144
    kd=np.dtype([(k,old[k]) for k in GROUP]);skey=np.empty(len(side),kd)
    for k in GROUP:skey[k]=side[k]
    order=np.argsort(skey,kind='stable');skey=skey[order];flags=(side['status'][order]==1).astype('u1');matches=0
    for kind,info in manifest['kinds'].items():
        mm=dump(kind);out=np.memmap(dest/info['file'],mode='w+',dtype=dt,shape=(len(mm),))
        count=0
        for lo in range(0,len(mm),500000):
            b=mm[lo:lo+500000];o=out[lo:lo+len(b)];o[:]=np.zeros(1,dt)
            for k in old.names:o[k]=b[k]
            if kind=='background_boundary':
                keys=np.empty(len(b),kd)
                for k in GROUP:keys[k]=b[k]
                pos=np.searchsorted(skey,keys);ok=pos<len(skey);pos=np.minimum(pos,len(skey)-1);ok &= skey[pos]==keys
                scope=(b['level']==0)&(b['code']==291)&(b['src_ix']==-2147483648)
                o['s02_producer_verified']=np.where(ok & scope,flags[pos],0);count+=int(o['s02_producer_verified'].sum())
        out.flush();info['row_size']=dt.itemsize;print('EXTENDED',kind,len(mm),'producer_verified',count,flush=True)
        if kind=='background_boundary':matches=count
    assert matches==int(side['rows'][side['status']==1].sum())
    manifest['extension']={'original_dump':str(DUMP),'side_table':str(ROOT/'side_background_boundary.npy'),'field':'s02_producer_verified','method':'exact group key join; unique actual producer with crossing longest closing edge; all unvisited/mixed/other producers zero','original_fields_unchanged':True}
    (dest/'dump_manifest.json').write_text(json.dumps(manifest,indent=2));print('DONE',dt.itemsize,matches,flush=True)

if __name__=='__main__':main()
