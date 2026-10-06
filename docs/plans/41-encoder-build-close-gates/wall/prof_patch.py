"""Plan 41 P1 profile instrumentation (throwaway worktrees only; output bytes unchanged).
Usage: prof_patch.py <worktree>  -- patches parser/kiwiw/_cenc.c in place."""
import sys, re
from pathlib import Path
p = Path(sys.argv[1]) / 'parser/kiwiw/_cenc.c'
s = p.read_text()
hdr = r'''
/* PLAN41-PROF */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
static double g_pf[16]; static long long g_pc_n[16]; static long long g_pf_calls; static double g_pf_n2;
static double pf_now(void){struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec + t.tv_nsec*1e-9;}
static void pf_flush(void){ const char *d = getenv("KW_PROF_DIR"); if(!d) return; char fn[512];
  snprintf(fn,sizeof fn,"%s/prof.%d.tsv",d,(int)getpid()); FILE *f=fopen(fn,"w"); if(!f) return;
  for(int k=0;k<16;k++) fprintf(f,"%d\t%.6f\t%lld\n",k,g_pf[k],g_pc_n[k]);
  fprintf(f,"calls\t%lld\nwhole_n2\t%.0f\n",g_pf_calls,g_pf_n2); fclose(f);}
__attribute__((destructor)) static void pf_fini(void){ pf_flush(); }
#define PF(k,t0) do{ double _t=pf_now(); g_pf[k]+=_t-(t0); g_pc_n[k]++; (t0)=_t; }while(0)
'''
# insert header after the last top-level #include
idx = [m.end() for m in re.finditer(r'^#include[^\n]*\n', s, re.M)][-1]
s = s[:idx] + hdr + s[idx:]
# wrap bg_shape
sig = 'static int64_t bg_shape(const uint8_t *lat, const uint8_t *lon, int64_t o, int64_t stride,\n                        int64_t nc, int closed, int64_t mc, int64_t tc, int64_t fl,\n                        const Bounds *bd, uint8_t *out, int64_t room, int64_t *nrec) {'
assert s.count(sig) == 1
impl = sig.replace('bg_shape(', 'bg_shape_impl(')
wrapper = sig + '''
    double t0 = pf_now();
    int64_t r = bg_shape_impl(lat, lon, o, stride, nc, closed, mc, tc, fl, bd, out, room, nrec);
    PF(0, t0);
    if ((++g_pf_calls & 4095) == 0) pf_flush();
    return r;
}
'''
s = s.replace(sig, 'static int64_t bg_shape_impl(const uint8_t *lat, const uint8_t *lon, int64_t o, int64_t stride,\n                        int64_t nc, int closed, int64_t mc, int64_t tc, int64_t fl,\n                        const Bounds *bd, uint8_t *out, int64_t room, int64_t *nrec);\n' + wrapper + impl)
# chains timing inside impl
s = s.replace('    int64_t m = chains(n, closed, R, &whole);\n    if (m < 0) return -1;',
              '    double tch = pf_now();\n    int64_t m = chains(n, closed, R, &whole);\n    PF(6, tch);\n    if (m < 0) return -1;', 1)
if 'static int eo_clip(' in s:
    s = s.replace('''    const double *R = e->R;
    g_es_n = g_ec_n = g_ee_n = g_ev_n = 0;''', '''    const double *R = e->R;
    double t0 = pf_now();
    g_es_n = g_ec_n = g_ee_n = g_ev_n = 0;''', 1)
    s = s.replace('''            if (eo_intersect(i,j,0,R)) { complex = 1; break; }
    if (!complex && !whole)''', '''            if (eo_intersect(i,j,0,R)) { complex = 1; break; }
    PF(1, t0);
    if (!complex && !whole)''', 1)
    s = s.replace('''    /* Repeated/touching vertices can connect distinct lobes even when pair''', '''    PF(2, t0);
    if (whole) g_pf_n2 += (double)n * n;
    /* Repeated/touching vertices can connect distinct lobes even when pair''', 1)
    s = s.replace('''    /* A legacy successor must form disjoint cycles. Reject ties and reused''', '''    PF(3, t0);
    /* A legacy successor must form disjoint cycles. Reject ties and reused''', 1)
    s = s.replace('''    if (!complex) return 0;
    for (int k = 0; k < 4; k++) {''', '''    PF(4, t0);
    if (!complex) return 0;
    for (int k = 0; k < 4; k++) {''', 1)
    s = s.replace('''        if (np >= 3 && area > 0 && eo_left(g_pc[0],g_pc[1],n))
            if (emit_piece(e,g_pc,np)) return -1;
    }
    return 1;''', '''        if (np >= 3 && area > 0 && eo_left(g_pc[0],g_pc[1],n))
            if (emit_piece(e,g_pc,np)) return -1;
    }
    PF(5, t0);
    return 1;''', 1)
    assert s.count('PF(') >= 8, s.count('PF(')
p.write_text(s)
print('patched', p, s.count('PF('))
