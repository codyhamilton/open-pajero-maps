"""Plan 41 P1 candidate byte-identical fix: eo_left bbox-gap prefilter.
An edge whose bbox lies farther than 4*step (+1e-9 abs margin) from the sample
point has d > 4*step, so step = min(step, d/4) is unchanged and it is skipped."""
import sys
from pathlib import Path
p = Path(sys.argv[1]) / 'parser/kiwiw/_cenc.c'
s = p.read_text()
old = """    for (int64_t i = 0; i < n; i++) {
        int64_t j = (i + 1) % n;
        long double ux = (long double)g_fx[j] - g_fx[i], uy = (long double)g_fy[j] - g_fy[i];"""
new = """    for (int64_t i = 0; i < n; i++) {
        int64_t j = (i + 1) % n;
        /* Plan 41: an edge whose bounding box is farther than 4*step from the
         * sample point cannot lower step (its distance d > 4*step), so skip it
         * before the hypotl. The 1e-9 margin dwarfs long-double evaluation
         * error at raw-unit coordinate scale; output bytes are unchanged. */
        {
            long double lim = 4 * step + 1e-9L;
            long double x0 = g_fx[i] < g_fx[j] ? g_fx[i] : g_fx[j], x1 = g_fx[i] < g_fx[j] ? g_fx[j] : g_fx[i];
            long double y0 = g_fy[i] < g_fy[j] ? g_fy[i] : g_fy[j], y1 = g_fy[i] < g_fy[j] ? g_fy[j] : g_fy[i];
            if (x - x1 > lim || x0 - x > lim || y - y1 > lim || y0 - y > lim) continue;
        }
        long double ux = (long double)g_fx[j] - g_fx[i], uy = (long double)g_fy[j] - g_fy[i];"""
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new)
p.write_text(s)
print('patched', p)
