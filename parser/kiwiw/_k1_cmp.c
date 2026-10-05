/* K1 `completeness` (plan 04, Phase 2, brief 2-05): for each (cell, type) that a spool polygon's
 * interior demonstrably meets, at least one decoded polygon piece (three or more vertices) of
 * that type exists in that cell. The arithmetic is `_required_cells` and the `present` set of
 * `_check_block` in `tools/quantisation_roundtrip.py`:
 *   (a) a polygon inside one cell rectangle whose ring, rounded to the raw lattice, has
 *       non-zero area;
 *   (b) a polygon crossing cells, a vertex at least one raw unit inside the cell;
 *   (c) the cell centre inside a polygon of the type (`Region.inside`, via the 2-04 index).
 * Missing pairs fail only if some demanding shape has an EO in-cell face
 * surviving its multiplier's densify, rint, dedup/spike and area contract.
 * Demand branches and checked-pair counts remain unchanged.
 * Cells are the block rectangle's decoded-leaf cells and spool cells (rows clipped to the band).
 * Samples are (cell, type) in (iy, ix, type) order; the accumulator keeps the first N. */
#define _GNU_SOURCE
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "_k1.h"

typedef struct { int32_t iy, ix, t; int64_t shape; } trip;
typedef struct { int32_t iy, ix; } cellk;
typedef struct { trip *v; int64_t n, cap; } trips;

static int cmp_trip(const void *a, const void *b) {
    const trip *x = (const trip *)a, *y = (const trip *)b;
    if (x->iy != y->iy) return x->iy < y->iy ? -1 : 1;
    if (x->ix != y->ix) return x->ix < y->ix ? -1 : 1;
    return (x->t > y->t) - (x->t < y->t);
}
static int cmp_cell(const void *a, const void *b) {
    return cmp_trip(&(trip){((const cellk *)a)->iy, ((const cellk *)a)->ix, 0},
                    &(trip){((const cellk *)b)->iy, ((const cellk *)b)->ix, 0});
}
static int cmp_i32(const void *a, const void *b) {
    int32_t x = *(const int32_t *)a, y = *(const int32_t *)b;
    return (x > y) - (x < y);
}

static int tpush(trips *s, int32_t ix, int32_t iy, int32_t t, int64_t shape) {
    if (s->n == s->cap) {
        int64_t nc = s->cap ? s->cap * 2 : 256;
        trip *q = (trip *)realloc(s->v, (size_t)nc * sizeof(trip));
        if (!q) return -4;
        s->v = q; s->cap = nc;
    }
    s->v[s->n].iy = iy; s->v[s->n].ix = ix; s->v[s->n].t = t; s->v[s->n].shape = shape; s->n++;
    return 0;
}

static int64_t tfind(const trip *v, int64_t n, trip k) {      /* index of k, or -1 */
    int64_t lo = 0, hi = n;
    while (lo < hi) { int64_t m = lo + (hi - lo) / 2; if (cmp_trip(&v[m], &k) < 0) lo = m + 1; else hi = m; }
    return lo < n && cmp_trip(&v[lo], &k) == 0 ? lo : -1;
}
static int in_cells(const cellk *cl, int64_t n, int64_t ix, int64_t iy) {
    if (ix < INT32_MIN || ix > INT32_MAX || iy < INT32_MIN || iy > INT32_MAX) return 0;
    trip k = {(int32_t)iy, (int32_t)ix, 0};
    int64_t lo = 0, hi = n;
    while (lo < hi) {
        int64_t m = lo + (hi - lo) / 2;
        trip t = {cl[m].iy, cl[m].ix, 0};
        if (cmp_trip(&t, &k) < 0) lo = m + 1; else hi = m;
    }
    return lo < n && cl[lo].iy == k.iy && cl[lo].ix == k.ix;
}

static int fin_cell(double v) { return isfinite(v) && fabs(v) < 2e9; }

/* Independent EO arrangement and wire footprint. No encoder calls.
 * Original binary64 coordinates are lifted losslessly to per-axis dyadic
 * int64 grids; determinants and crossing parameters are exact __int128.
 * Conversion to floating coordinates happens after exact contact tests,
 * for clipping / densification / rint arithmetic. Unsupported
 * grid extents fail closed, rather than approximate a topology predicate. */
typedef struct { double x, y; } rpt;
typedef struct { rpt *v; int64_t n, cap; } rpts;
typedef unsigned __int128 ru128;
typedef struct { int64_t edge, id; ru128 p, q; } rcut;
typedef struct { int64_t a, b, dx, dy; int used, canceled, odd; } rhalf;

static int rpoint(rpts *p, rpt v) {
    if (p->n == p->cap) {
        int64_t nc = p->cap ? p->cap * 2 : 32;
        rpt *v2 = realloc(p->v, (size_t)nc * sizeof(rpt));
        if (!v2) return -4;
        p->v = v2; p->cap = nc;
    }
    p->v[p->n++] = v; return 0;
}
static int rdbl_cmp(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}
static int rcentre(const k1_shapes *h, int64_t s, trip k) {
    int64_t a = h->off[s], n = h->off[s + 1] - a, nc = 0;
    double *cr = malloc((size_t)n * sizeof(double));
    if (!cr) return -4;
    double x = ((double)k.ix + .5) * K1_RAW, y = ((double)k.iy + .5) * K1_RAW;
    for (int64_t i = 0; i < n; i++) {
        int64_t j = (i + 1) % n;
        double ax = h->x[a+i], ay = h->y[a+i], bx = h->x[a+j], by = h->y[a+j];
        if (fmin(ay, by) <= y && y < fmax(ay, by)) cr[nc++] = ax + (y-ay)*(bx-ax)/(by-ay);
    }
    qsort(cr, (size_t)nc, sizeof(double), rdbl_cmp);
    int ok = 0;
    for (int64_t i = 0; i+1 < nc; i += 2)
        if (cr[i] <= x + K1_TOL && cr[i+1] >= x - K1_TOL) { ok = 1; break; }
    free(cr); return ok;
}
static int rwire(rpts p, int32_t mc) {
    rpts q = {0}; int rc = 0;
    double lim = 127.0 * mc - 1.0;
    for (int64_t i = 0; i < p.n && rc == 0; i++) {
        rpt a = p.v[i], b = p.v[(i+1)%p.n];
        double dx = b.x-a.x, dy = b.y-a.y, mx = fmax(fabs(dx), fabs(dy));
        double kf = mx > lim ? ceil(mx/lim) : 1;
        if (!(kf < 1e7)) { rc = -3; break; }
        int64_t k = (int64_t)kf;
        for (int64_t j = 0; j < k && rc == 0; j++) {
            double t = (double)j/(double)k;
            rpt v = {rint(j ? a.x+dx*t : a.x), rint(j ? a.y+dy*t : a.y)};
            if (!q.n || v.x != q.v[q.n-1].x || v.y != q.v[q.n-1].y) rc = rpoint(&q, v);
        }
    }
    while (q.n > 1 && q.v[q.n-1].x == q.v[0].x && q.v[q.n-1].y == q.v[0].y) q.n--;
    for (int64_t i = 0; q.n >= 3 && i < q.n;) {
        rpt a = q.v[(i+q.n-1)%q.n], b = q.v[(i+1)%q.n];
        if (a.x != b.x || a.y != b.y) { i++; continue; }
        memmove(q.v+i, q.v+i+1, (size_t)(q.n-i-1)*sizeof(rpt)); q.n--;
        int64_t j = i < q.n ? i : 0;
        memmove(q.v+j, q.v+j+1, (size_t)(q.n-j-1)*sizeof(rpt)); q.n--; i = 0;
    }
    __int128 area = 0;
    for (int64_t i = 0; i < q.n; i++) {
        rpt a = q.v[i], b = q.v[(i+1)%q.n];
        area += (__int128)(int64_t)a.x*(int64_t)b.y - (__int128)(int64_t)b.x*(int64_t)a.y;
    }
    int ok = q.n >= 3 && area != 0; free(q.v); return rc ? rc : ok;
}
static int rclip_wire(const rpt *p, int64_t n, trip k, int32_t mc) {
    rpts cur = {0}; int rc = 0;
    for (int64_t i = 0; i < n && rc == 0; i++) rc = rpoint(&cur, p[i]);
    for (int side = 0; side < 4 && rc == 0; side++) {
        rpts out = {0}; int axis = side / 2, lower = !(side % 2);
        double bound = ((double)(axis ? k.iy : k.ix) + !lower) * K1_RAW;
        for (int64_t i = 0; i < cur.n && rc == 0; i++) {
            rpt a = cur.v[i], b = cur.v[(i+1)%cur.n];
            double av = axis ? a.y : a.x, bv = axis ? b.y : b.x;
            int ia = lower ? av >= bound : av <= bound, ib = lower ? bv >= bound : bv <= bound;
            if (ia) rc = rpoint(&out, a);
            if (ia != ib && rc == 0) {
                double t = (bound-av)/(bv-av);
                rpt v = axis ? (rpt){a.x+t*(b.x-a.x), bound} : (rpt){bound, a.y+t*(b.y-a.y)};
                rc = rpoint(&out, v);
            }
        }
        free(cur.v); cur = out;
    }
    if (rc == 0) rc = rwire(cur, mc);
    free(cur.v); return rc;
}
static int rgrid(const double *v, int64_t n, int64_t *iv) {
    int scale = 1024;
    for (int64_t i = 0; i < n; i++) {
        if (!isfinite(v[i])) return -3;
        if (!v[i]) continue;
        int e; double f = frexp(fabs(v[i]), &e);
        uint64_t m = (uint64_t)ldexp(f, 53);
        int z = __builtin_ctzll(m), s = e - 53 + z;
        if (s < scale) scale = s;
    }
    if (scale == 1024) scale = 0;
    for (int64_t i = 0; i < n; i++) {
        double d = ldexp(v[i], -scale);
        if (!isfinite(d) || fabs(d) >= 0x1p60) return -3;
        iv[i] = (int64_t)d;
    }
    return 0;
}
/* Compare positive rational parameters without overflowing cross-products. */
static int rratio(ru128 a, ru128 b, ru128 c, ru128 d) {
    int sign = 1;
    for (;;) {
        ru128 x = a/b, y = c/d;
        if (x != y) return sign * (x < y ? -1 : 1);
        a %= b; c %= d;
        if (!a || !c) return sign * ((a > 0) - (c > 0));
        ru128 t = a; a = b; b = t; t = c; c = d; d = t; sign = -sign;
    }
}
static int rcut_cmp(const void *a, const void *b) {
    const rcut *x = a, *y = b;
    if (x->edge != y->edge) return x->edge < y->edge ? -1 : 1;
    return rratio(x->p, x->q, y->p, y->q);
}
static int rcut_push(rcut **v, int64_t *n, int64_t *cap, rcut c) {
    if (*n == *cap) {
        int64_t nc = *cap ? *cap * 2 : 64;
        rcut *q = realloc(*v, (size_t)nc*sizeof(rcut));
        if (!q) return -4;
        *v = q; *cap = nc;
    }
    (*v)[(*n)++] = c; return 0;
}
static __int128 rcross(int64_t ax, int64_t ay, int64_t bx, int64_t by) {
    return (__int128)ax*by - (__int128)ay*bx;
}
/* Split segments inherit exact source-grid directions. Positive per-axis
 * scaling preserves angular order, so no rounded intersection predicates. */
static int rdircmp(const rhalf *a, const rhalf *b) {
    int upper = a->dy > 0 || (!a->dy && a->dx > 0);
    int other = b->dy > 0 || (!b->dy && b->dx > 0);
    if (upper != other) return upper ? -1 : 1;
    __int128 cross = rcross(a->dx,a->dy,b->dx,b->dy);
    return (cross < 0) - (cross > 0);
}
static int64_t rroot(int64_t *parent, int64_t v) {
    while (parent[v] != v) { parent[v] = parent[parent[v]]; v = parent[v]; }
    return v;
}
static int rcontact(rcut **cuts, int64_t *nc, int64_t *cap, int64_t edge,
                    int64_t id, int64_t ax, int64_t ay, int64_t bx, int64_t by,
                    int64_t px, int64_t py) {
    int64_t dx = bx-ax, dy = by-ay;
    if ((!dx && !dy) || rcross(px-ax, py-ay, dx, dy) ||
        px < (ax < bx ? ax : bx) || px > (ax > bx ? ax : bx) ||
        py < (ay < by ? ay : by) || py > (ay > by ? ay : by)) return 0;
    int64_t den = dx ? dx : dy, num = dx ? px-ax : py-ay;
    if (den < 0) { den = -den; num = -num; }
    return rcut_push(cuts, nc, cap, (rcut){edge, id, num, den});
}
static int rrepresent(const k1_shapes *h, int64_t s, trip cell) {
    int64_t a = h->off[s], n = h->off[s+1]-a;
    const double *x = h->x+a, *y = h->y+a;
    if (n > 1 && x[0] == x[n-1] && y[0] == y[n-1]) n--;
    if (n < 3) return 0;
    int64_t *gx = malloc((size_t)n*8), *gy = malloc((size_t)n*8), *ids = malloc((size_t)n*8);
    rpts verts = {0}; rcut *cuts = NULL; int64_t nc = 0, cap = 0; rhalf *edges = NULL; int64_t *parent = NULL;
    rpts *faces = NULL; int8_t *parity = NULL; int64_t nf = 0;
    int rc = gx && gy && ids ? 0 : -4;
    if (!rc) rc = rgrid(x, n, gx);
    if (!rc) rc = rgrid(y, n, gy);
    for (int64_t i = 0; i < n && !rc; i++) {
        ids[i] = -1;
        for (int64_t j = 0; j < verts.n; j++) if (verts.v[j].x == x[i] && verts.v[j].y == y[i]) { ids[i] = j; break; }
        if (ids[i] < 0) { ids[i] = verts.n; rc = rpoint(&verts, (rpt){x[i], y[i]}); }
    }
    for (int64_t i = 0; i < n && !rc; i++) {
        rc = rcut_push(&cuts, &nc, &cap, (rcut){i, ids[i], 0, 1});
        if (!rc) rc = rcut_push(&cuts, &nc, &cap, (rcut){i, ids[(i+1)%n], 1, 1});
    }
    int simple = verts.n == n;
    for (int64_t i = 0; i < n && !rc; i++) for (int64_t j = i+1; j < n && !rc; j++) {
        int64_t ib = (i+1)%n, jb = (j+1)%n;
        int64_t dx = gx[ib]-gx[i], dy = gy[ib]-gy[i], ex = gx[jb]-gx[j], ey = gy[jb]-gy[j];
        __int128 den = rcross(dx, dy, ex, ey), p = rcross(gx[j]-gx[i], gy[j]-gy[i], ex, ey);
        __int128 q = rcross(gx[j]-gx[i], gy[j]-gy[i], dx, dy);
        if (den < 0) { den = -den; p = -p; q = -q; }
        if (!dx && !dy) { simple = 0; continue; }
        if (!ex && !ey) { simple = 0; continue; }
        if (den == 0) {
            if (p) continue;
            int64_t ends[4] = {i, ib, j, jb};
            for (int z = 0; z < 4 && !rc; z++) {
                int64_t v = ends[z], e = z < 2 ? j : i, eb = (e+1)%n;
                int64_t old = nc;
                rc = rcontact(&cuts, &nc, &cap, e, ids[v], gx[e], gy[e], gx[eb], gy[eb], gx[v], gy[v]);
                if (nc != old && !((ib == j || jb == i) &&
                    (ids[v] == ids[e] || ids[v] == ids[eb]))) simple = 0;
            }
            continue;
        }
        if (p < 0 || p > den || q < 0 || q > den) continue;
        if (!((ib == j || jb == i) && (p == 0 || p == den) && (q == 0 || q == den))) simple = 0;
        int64_t id = p == 0 ? ids[i] : p == den ? ids[ib] : q == 0 ? ids[j] : q == den ? ids[jb] : -1;
        for (int64_t k = 0; id < 0 && k < nc; k++)
            if ((cuts[k].edge == i && !rratio(cuts[k].p, cuts[k].q, p, den)) ||
                (cuts[k].edge == j && !rratio(cuts[k].p, cuts[k].q, q, den))) { id = cuts[k].id; break; }
        if (id < 0) {
            long double t = (long double)p/(long double)den;
            id = verts.n;
            rc = rpoint(&verts, (rpt){(double)((long double)x[i]+t*((long double)x[ib]-x[i])),
                                      (double)((long double)y[i]+t*((long double)y[ib]-y[i]))});
        }
        if (!rc) rc = rcut_push(&cuts, &nc, &cap, (rcut){i, id, p, den});
        if (!rc) rc = rcut_push(&cuts, &nc, &cap, (rcut){j, id, q, den});
    }
    if (!rc && simple) {
        rpts ring = {0};
        for (int64_t i = 0; i < n && !rc; i++) rc = rpoint(&ring, (rpt){x[i],y[i]});
        if (!rc) rc = rclip_wire(ring.v, ring.n, cell, h->mult[s]);
        free(ring.v); goto done;
    }
    int64_t ne = 0;
    if (!rc) { edges = calloc((size_t)(2*nc+1), sizeof(rhalf)); if (!edges) rc = -4; }
    if (!rc) {
        parent = malloc((size_t)verts.n*sizeof(int64_t));
        if (!parent) rc = -4;
    }
    if (!rc) {
        qsort(cuts, (size_t)nc, sizeof(rcut), rcut_cmp);
        for (int64_t i = 0; i < verts.n; i++) parent[i] = i;
        /* Concurrent intersections may have been discovered through disjoint
         * edge pairs. Equal parameters identify them transitively, exactly. */
        for (int64_t i = 0; i+1 < nc; i++)
            if (cuts[i].edge == cuts[i+1].edge && !rratio(cuts[i].p,cuts[i].q,cuts[i+1].p,cuts[i+1].q))
                parent[rroot(parent,cuts[i+1].id)] = rroot(parent,cuts[i].id);
        for (int64_t i = 0; i < nc; i++) cuts[i].id = rroot(parent,cuts[i].id);
        for (int64_t i = 0; i < n; i++) ids[i] = rroot(parent,ids[i]);
        for (int64_t i = 0; i < verts.n && !rc; i++) if (rroot(parent,i) == i)
            for (int64_t j = 0; j < i; j++) if (rroot(parent,j) == j &&
                verts.v[i].x == verts.v[j].x && verts.v[i].y == verts.v[j].y) { rc = -3; break; }
    }
    for (int64_t i = 0; i+1 < nc && !rc; i++) {
        if (cuts[i].edge != cuts[i+1].edge) continue;
        int64_t u = cuts[i].id, v = cuts[i+1].id;
        if (u == v) continue;
        int64_t k;
        for (k = 0; k < ne; k += 2) if ((edges[k].a == u && edges[k].b == v) || (edges[k].a == v && edges[k].b == u)) break;
        if (k < ne) { edges[k].canceled ^= 1; edges[k+1].canceled = edges[k].canceled;
            edges[k].odd ^= 1; edges[k+1].odd = edges[k].odd; continue; }
        int64_t e = cuts[i].edge, eb = (e+1)%n, dx = gx[eb]-gx[e], dy = gy[eb]-gy[e];
        edges[ne++] = (rhalf){u, v, dx, dy, 0, 0, 1};
        edges[ne++] = (rhalf){v, u, -dx, -dy, 0, 0, 1};
    }
    if (!rc) {
        int odd = 0;
        for (int64_t i = 0; i < verts.n; i++) parent[i] = i;
        for (int64_t k = 0; k < ne; k += 2) if (edges[k].odd) {
            odd = 1; parent[rroot(parent,edges[k].a)] = rroot(parent,edges[k].b);
        }
        if (!odd) goto done; /* Empty parity must never revive the source ring. */
        /* Even edges may join boundaries through zero-width cuts, but may
         * not subdivide faces. Keep a forest, including attached hole bridges. */
        for (int64_t k = 0; k < ne; k += 2) if (!edges[k].odd) {
            int64_t u = rroot(parent,edges[k].a), v = rroot(parent,edges[k].b);
            if (u != v) { parent[u] = v; edges[k].canceled = edges[k+1].canceled = 0; }
        }
        for (int64_t k = 0; k < ne && !rc; k++) if (!edges[k].canceled)
            for (int64_t j = 0; j < k; j++) if (!edges[j].canceled && edges[k].a == edges[j].a &&
                !rdircmp(&edges[k],&edges[j])) { rc = -3; break; }
    }
    if (!rc) {
        faces = calloc((size_t)ne, sizeof(rpts)); parity = malloc((size_t)ne);
        if (!faces || !parity) rc = -4;
        else memset(parity, -1, (size_t)ne);
    }
    for (int64_t start = 0; start < ne && !rc; start++) {
        if (edges[start].used || edges[start].canceled) continue;
        rpts *face = &faces[nf++]; int64_t k = start; int closed = 0;
        while (!edges[k].used && !rc) {
            edges[k].used = nf; /* One-based left-face identity. */
            rc = rpoint(face, verts.v[edges[k].a]);
            int64_t best = -1, wrap = -1;
            for (int64_t j = 0; j < ne; j++) if (!edges[j].canceled && edges[j].a == edges[k].b) {
                if (wrap < 0 || rdircmp(&edges[wrap],&edges[j]) < 0) wrap = j;
                if (rdircmp(&edges[j],&edges[k^1]) < 0 &&
                    (best < 0 || rdircmp(&edges[best],&edges[j]) < 0)) best = j;
            }
            if (best < 0) best = wrap;
            if (best < 0) break;
            k = best; if (k == start) { closed = 1; break; }
        }
        if (!rc && !closed) rc = -3;
    }
    if (!rc) {
        /* Intersections cannot be below the lowest source vertex. Select its
         * most CCW outgoing edge by exact source-grid directions. Its left
         * face is exterior; all other labels follow by crossing edge parity. */
        int64_t low = 0, exterior = -1;
        for (int64_t i = 1; i < n; i++)
            if (gy[i] < gy[low] || (gy[i] == gy[low] && gx[i] < gx[low])) low = i;
        for (int64_t k = 0; k < ne; k++) if (!edges[k].canceled && edges[k].a == ids[low] &&
            (exterior < 0 || rdircmp(&edges[exterior],&edges[k]) < 0)) exterior = k;
        if (exterior < 0) rc = -3;
        else parity[edges[exterior].used-1] = 0;
        int changed = 1;
        while (changed && !rc) {
            changed = 0;
            for (int64_t k = 0; k < ne && !rc; k += 2) if (!edges[k].canceled) {
                int64_t a = edges[k].used-1, b = edges[k+1].used-1;
                if (parity[a] >= 0 && parity[b] >= 0) {
                    if ((parity[a]^parity[b]) != edges[k].odd) rc = -3;
                } else if (parity[a] >= 0) { parity[b] = parity[a]^edges[k].odd; changed = 1; }
                else if (parity[b] >= 0) { parity[a] = parity[b]^edges[k].odd; changed = 1; }
            }
        }
        for (int64_t i = 0; i < nf && !rc; i++) if (parity[i] < 0) rc = -3;
        for (int64_t i = 0; i < nf && !rc; i++) if (parity[i])
            rc = rclip_wire(faces[i].v, faces[i].n, cell, h->mult[s]);
    }
done:
    for (int64_t i = 0; i < nf; i++) free(faces[i].v);
    free(faces); free(parity);
    free(gx); free(gy); free(ids); free(verts.v); free(cuts); free(edges); free(parent); return rc;
}

int k1_cmp_kinds(k1_ctx *c) {
    const k1_shapes *H = c->shapes;
    const int32_t *oix, *oiy;
    int64_t nown = k1_region_cells(c->region, &oix, &oiy), nc = 0, rc = 0;
    trips req = {0}, pres = {0};
    cellk *cl = NULL;
    k1_qin *q = NULL;
    int32_t *types = NULL;
    int64_t ntypes = 0;
    const int64_t c0 = c->c0, c1 = c->c1, r0 = c->r0, r1 = c->r1;
    const double RAW = (double)K1_RAW;

    /* the decoded pieces: polygon shapes of three or more vertices, by (leaf cell, type) */
    for (int64_t i = 0; i < c->nwalk && rc == 0; i++) {
        const k1_leaf *lf = &c->leaf[i];
        const d1_walk *w = &c->walk[i];
        const d1_frame *f = lf->ok && w->frame >= 0 ? &c->frame[w->frame] : NULL;
        for (uint32_t k = 0; f && f->has_bg && k < f->bgshape_n && rc == 0; k++) {
            const d1_bgshape *sh = &c->bgshape[f->bgshape_first + k];
            if (sh->shape_class == 2 && sh->coord_n >= 3) rc = tpush(&pres, lf->ix, lf->iy, sh->type_code, -1);
        }
    }
    /* the cells: decoded-leaf cells and spool cells inside the block rectangle */
    if (rc == 0) {
        cl = (cellk *)malloc((size_t)(c->nwalk + nown + 1) * sizeof(cellk));
        if (!cl) rc = -4;
    }
    for (int64_t i = 0; rc == 0 && i < c->nwalk + nown; i++) {
        int32_t ix = i < c->nwalk ? c->leaf[i].ix : oix[i - c->nwalk];
        int32_t iy = i < c->nwalk ? c->leaf[i].iy : oiy[i - c->nwalk];
        if (ix < c0 || ix > c1 || iy < r0 || iy > r1) continue;
        cl[nc].iy = iy; cl[nc].ix = ix; nc++;
    }
    if (rc == 0 && nc > 1) {
        qsort(cl, (size_t)nc, sizeof(cellk), cmp_cell);
        int64_t m = 1;
        for (int64_t i = 1; i < nc; i++)
            if (cmp_cell(&cl[i], &cl[m - 1]) != 0) cl[m++] = cl[i];
        nc = m;
    }
    if (rc == 0 && nc > 0 && H && H->n > 0) {
        for (int64_t s = 0; s < H->n && rc == 0; s++) {
            int64_t a = H->off[s], n = H->off[s + 1] - a;
            if (H->cls[s] != 2 || n < 3) continue;
            const double *X = H->x + a, *Y = H->y + a;
            double x0 = X[0], x1 = X[0], y0 = Y[0], y1 = Y[0];
            for (int64_t j = 1; j < n; j++) {
                if (X[j] < x0) x0 = X[j];
                if (X[j] > x1) x1 = X[j];
                if (Y[j] < y0) y0 = Y[j];
                if (Y[j] > y1) y1 = Y[j];
            }
            double cx = floor((x0 + x1) / 2.0 / RAW), cy = floor((y0 + y1) / 2.0 / RAW);
            int one = x0 >= cx * RAW && x1 <= (cx + 1) * RAW && y0 >= cy * RAW && y1 <= (cy + 1) * RAW;
            int32_t t = H->type[s];
            if (one) {
                double area = 0.0;
                for (int64_t j = 0; j < n; j++) {
                    int64_t k = j + 1 < n ? j + 1 : 0;
                    area += nearbyint(X[j]) * nearbyint(Y[k]) - nearbyint(X[k]) * nearbyint(Y[j]);
                }
                if (area != 0 && fin_cell(cx) && fin_cell(cy) && in_cells(cl, nc, (int64_t)cx, (int64_t)cy))
                    rc = tpush(&req, (int32_t)cx, (int32_t)cy, t, s);
            } else {
                for (int64_t j = 0; j < n && rc == 0; j++) {
                    double kx = floor(X[j] / RAW), ky = floor(Y[j] / RAW);
                    if (!fin_cell(kx) || !fin_cell(ky)) continue;
                    double fx = X[j] - kx * RAW, fy = Y[j] - ky * RAW;
                    if (fx >= 1 && fx <= RAW - 1 && fy >= 1 && fy <= RAW - 1 &&
                        kx >= (double)c0 && kx <= (double)c1 && ky >= (double)r0 && ky <= (double)r1 &&
                        in_cells(cl, nc, (int64_t)kx, (int64_t)ky))
                        rc = tpush(&req, (int32_t)kx, (int32_t)ky, t, s);
                }
            }
        }
        /* (c) cell centres inside a polygon of each type present */
        types = (int32_t *)malloc((size_t)(H->n + 1) * 4);
        if (!types) rc = -4;
        for (int64_t s = 0; rc == 0 && s < H->n; s++)
            if (H->cls[s] == 2 && H->off[s + 1] - H->off[s] >= 3) types[ntypes++] = H->type[s];
        if (rc == 0 && ntypes > 1) {
            qsort(types, (size_t)ntypes, 4, cmp_i32);
            int64_t m = 1;
            for (int64_t i = 1; i < ntypes; i++) if (types[i] != types[m - 1]) types[m++] = types[i];
            ntypes = m;
        }
        if (rc == 0 && ntypes > 0) {
            q = (k1_qin *)malloc((size_t)(nc * ntypes) * sizeof(k1_qin));
            if (!q) rc = -4;
            for (int64_t i = 0; rc == 0 && i < nc * ntypes; i++) {
                q[i].orient = 0; q[i].type = types[i / nc];
                q[i].c = ((double)cl[i % nc].iy + 0.5) * RAW;
                q[i].a = ((double)cl[i % nc].ix + 0.5) * RAW;
                q[i].ok = 0;
            }
            if (rc == 0) rc = k1_bg_inside(c, q, nc * ntypes);
            for (int64_t i = 0; rc == 0 && i < nc * ntypes; i++)
                if (q[i].ok) rc = tpush(&req, cl[i % nc].ix, cl[i % nc].iy, q[i].type, -1);
        }
    }
    int64_t nreq = 0, nbad = 0;
    if (rc == 0) {
        qsort(req.v, (size_t)req.n, sizeof(trip), cmp_trip);
        qsort(pres.v, (size_t)pres.n, sizeof(trip), cmp_trip);
        for (int64_t i = 0; i < req.n && rc == 0; i++) {
            if (i && cmp_trip(&req.v[i], &req.v[i - 1]) == 0) continue;
            nreq++;
            if (tfind(pres.v, pres.n, req.v[i]) >= 0) continue;
            int represent = 0, centre = 0;
            int64_t end = i + 1;
            while (end < req.n && cmp_trip(&req.v[i], &req.v[end]) == 0) end++;
            for (int64_t j = i; j < end && !represent && rc == 0; j++) {
                int64_t s = req.v[j].shape;
                if (s < 0) { centre = 1; continue; }
                represent = rrepresent(H, s, req.v[i]);
                if (represent < 0) { rc = represent; represent = 0; }
            }
            /* Branch (c) keeps its indexed batched query. Resolve demanding
             * shape indices only for a missing pair, so the normal path is cheap. */
            for (int64_t s = 0; centre && !represent && rc == 0 && s < H->n; s++) {
                if (H->cls[s] != 2 || H->type[s] != req.v[i].t || H->off[s+1]-H->off[s] < 3) continue;
                int hit = rcentre(H, s, req.v[i]);
                if (hit < 0) { rc = hit; break; }
                if (hit) represent = rrepresent(H, s, req.v[i]);
                if (represent < 0) { rc = represent; represent = 0; }
            }
            if (!represent || rc < 0) continue;
            nbad++;
            k1_sample m;
            memset(&m, 0, sizeof m);
            m.lat = 0.0; m.lon = 0.0; m.err = NAN;
            m.ix = req.v[i].ix; m.iy = req.v[i].iy; m.vx = INT32_MIN; m.vy = INT32_MIN;
            m.reason = K1_R_COMPLETE; m.code = req.v[i].t;
            k1_push_sample(c->acc, K1_completeness, &m);
            K1_EMIT_DUMP(c->acc, K1_completeness, c->block->level, &m, -1, -1);
        }
        if (rc == 0) k1_add(c->acc, K1_completeness, nreq, nbad, 0.0);
    }
    free(req.v); free(pres.v); free(cl); free(q); free(types);
    return (int)rc;
}
