"""Plan 36 P2: classify PDMDH bytes outside BMT address fields (small preads only).

Usage: pdmdh_fields.py JSON_ARGS OUT, JSON_ARGS = [[name, old_disc, new_disc, [offsets...]], ...].
Run under run_heavy_python.py; reads only the PDMDH and the BMT-addressed PMR blocks."""
import json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / 'parser'))
from kiwiw import volume  # noqa
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record  # noqa

def pdmdh(path):
    fd = os.open(path, os.O_RDONLY)
    head = os.pread(fd, volume.DATAVOL_SIZE + volume.MHT_SIZE, 0)
    hdr = volume.parse_volume_header(head[:volume.DATAVOL_SIZE])
    mht = volume.parse_management_header_table(head[volume.DATAVOL_SIZE:])
    ss, ls = hdr.sector_size, hdr.logical_sector_size
    e = mht.entries[0]
    buf = os.pread(fd, e.size * ls, volume.getsector(e.dsa, ss, ls))
    pd = volume.parse_pdmdh_full(buf)
    levels = {m.level: m for m in pd.levels}
    blocks = {}
    for t in pd.bmt_tables:
        bs = pd.blocksets[t.blockset_ordinal]
        for bi, be in enumerate(t.entries):
            o = t.offset + bi * pd.bmr_size * 2
            rec = None
            if be.dsa != 0xFFFFFFFF and be.size:
                b = os.pread(fd, be.size * ls, volume.getsector(be.dsa, ss, ls))
                root = parse_parcel_mgmt_record(b, levels[bs.level])
                rec = len(b) - len(root.tail_raw)
            blocks[o] = dict(key=f'L{bs.level} {bs.blockset_index}/{bi}', entry_offset=o,
                             entry_len=pd.bmr_size * 2, size_sectors=be.size, record_bytes=rec)
    os.close(fd)
    return buf, blocks

out = {}
for name, old, new, offs in json.loads(sys.argv[1]):
    ob, oblk = pdmdh(old); nb, nblk = pdmdh(new)
    rows = []
    for off in offs:
        eo = max(k for k in oblk if k <= off)
        rows.append(dict(offset=off, field_offset_in_entry=off - eo, old_byte=ob[off], new_byte=nb[off],
                         old=oblk[eo], new=nblk[eo]))
    changed_size = [dict(old=oblk[k], new=nblk[k]) for k in oblk if oblk[k]['size_sectors'] != nblk[k]['size_sectors']]
    out[name] = dict(outside_bytes=rows, bmt_entries_size_changed=changed_size)
Path(sys.argv[2]).write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(out, indent=1))
