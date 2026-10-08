/* Plan 46: tracked background producer-scan shim.
 * Built against a pinned _cenc.c (-O2 -ffp-contract=off -fPIC).
 * Exposes clip (kw__bg_shape) plus ring-closure / longest-edge / crossing stats
 * used to rebuild residual_crossing_verified / s02_producer_verified predicates.
 */
#include "CENC_PATH"
#include <math.h>
#include <stdint.h>
#include <string.h>

/* Clip a ring in raw cell units into `rect`. Returns size (<0 decline). */
int64_t bg_ps_clip(const double *lat, const double *lon, int64_t n,
                   int64_t tc, const double *b4, const double *rect, double cr,
                   uint8_t *out, int64_t room, int64_t *nrec) {
    return kw__bg_shape(lat, lon, n, 1, 1, tc, 0, b4, rect, cr, out, room, nrec);
}

/* Ring geometry predicates on an explicit lat/lon ring (degrees).
 * out[0]=explicitly_closed (first==last within eps)
 * out[1]=closing_edge_index (= n-2 when closed polyline of n verts incl repeat)
 * out[2]=longest_edge_index
 * out[3]=closing_is_longest (0/1)
 * out[4]=proper_nonadjacent_crossing_count on closing edge
 * Returns 0 ok, -1 if n<4.
 */
static int _seg_intersect(double ax, double ay, double bx, double by,
                          double cx, double cy, double dx, double dy) {
    /* Proper intersection (not just touching at endpoint). Orientation method. */
    double d1x = bx - ax, d1y = by - ay, d2x = dx - cx, d2y = dy - cy;
    double cross = d1x * d2y - d1y * d2x;
    if (fabs(cross) < 1e-18) return 0; /* parallel */
    double t = ((cx - ax) * d2y - (cy - ay) * d2x) / cross;
    double u = ((cx - ax) * d1y - (cy - ay) * d1x) / cross;
    return (t > 1e-12 && t < 1.0 - 1e-12 && u > 1e-12 && u < 1.0 - 1e-12);
}

int64_t bg_ps_ring_stats2(const double *lat, const double *lon, int64_t n,
                          double sx, double sy, int64_t *out5);
/* Degrees variant (kept for tests / diagnostics): unit scale. */
int64_t bg_ps_ring_stats(const double *lat, const double *lon, int64_t n,
                         int64_t *out5) {
    return bg_ps_ring_stats2(lat, lon, n, 1.0, 1.0, out5);
}
/* Plan 46 RC6: edge lengths in the build's raw lattice units (kw_bounds: x = lon*cr/dlon,
 * y = lat*cr/dlat); sx = cr/dlon, sy = cr/dlat. Closure and proper crossings are invariant
 * under per-axis scaling; only "closing edge = longest edge" depends on the units. */
int64_t bg_ps_ring_stats2(const double *lat, const double *lon, int64_t n,
                          double sx, double sy, int64_t *out5) {
    if (n < 4 || out5 == 0) return -1;
    memset(out5, 0, 5 * sizeof(int64_t));
    const double eps = 1e-12;
    int closed = (fabs(lat[0] - lat[n - 1]) < eps && fabs(lon[0] - lon[n - 1]) < eps);
    out5[0] = closed ? 1 : 0;
    if (!closed) return 0;
    /* edges 0..n-2 connect i -> i+1; closing edge is n-2 (last→first duplicate) */
    int64_t nedge = n - 1;
    int64_t longest = 0;
    double longest_len = -1.0;
    for (int64_t i = 0; i < nedge; i++) {
        double dx = (lon[i + 1] - lon[i]) * sx;
        double dy = (lat[i + 1] - lat[i]) * sy;
        double len = dx * dx + dy * dy;
        if (len > longest_len) { longest_len = len; longest = i; }
    }
    int64_t closing = nedge - 1; /* edge between n-2 and n-1 (==0) */
    out5[1] = closing;
    out5[2] = longest;
    out5[3] = (closing == longest) ? 1 : 0;
    /* count proper crossings of closing edge against non-adjacent edges */
    int64_t crosses = 0;
    double ax = lon[closing], ay = lat[closing];
    double bx = lon[0], by = lat[0]; /* closing ends at first vert */
    /* closing edge is between verts (n-2) and (n-1); n-1 coincides with 0 */
    ax = lon[n - 2]; ay = lat[n - 2];
    bx = lon[n - 1]; by = lat[n - 1];
    for (int64_t i = 0; i < nedge; i++) {
        if (i == closing) continue;
        /* adjacent edges share a vertex with closing — skip */
        if (i == closing - 1 || i == 0 /* first edge adjacent at vert 0 */) continue;
        if (i == (nedge - 2) && closing == nedge - 1) continue; /* already closing-1 */
        double cx = lon[i], cy = lat[i];
        double dx = lon[i + 1], dy = lat[i + 1];
        if (_seg_intersect(ax, ay, bx, by, cx, cy, dx, dy)) crosses++;
    }
    out5[4] = crosses;
    return 0;
}
