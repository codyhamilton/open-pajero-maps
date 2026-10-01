/* K1 `completeness` (plan 04, Phase 2, brief 2-05): for each (cell, type) that a spool polygon's
 * interior demonstrably meets, at least one decoded polygon piece (three or more vertices) of
 * that type exists in that cell. The arithmetic is `_required_cells` and the `present` set of
 * `_check_block` in `tools/quantisation_roundtrip.py`:
 *   (a) a polygon inside one cell rectangle whose ring, rounded to the raw lattice, has
 *       non-zero area;
 *   (b) a polygon crossing cells, a vertex at least one raw unit inside the cell;
 *   (c) the cell centre inside a polygon of the type (`Region.inside`, via the 2-04 index).
 * Cells are the block rectangle's decoded-leaf cells and spool cells (rows clipped to the band).
 * Samples are (cell, type) in (iy, ix, type) order; the accumulator keeps the first N. */
#define _GNU_SOURCE
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "_k1.h"

typedef struct { int32_t iy, ix, t; } trip;
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

static int tpush(trips *s, int32_t ix, int32_t iy, int32_t t) {
    if (s->n == s->cap) {
        int64_t nc = s->cap ? s->cap * 2 : 256;
        trip *q = (trip *)realloc(s->v, (size_t)nc * sizeof(trip));
        if (!q) return -4;
        s->v = q; s->cap = nc;
    }
    s->v[s->n].iy = iy; s->v[s->n].ix = ix; s->v[s->n].t = t; s->n++;
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
            if (sh->shape_class == 2 && sh->coord_n >= 3) rc = tpush(&pres, lf->ix, lf->iy, sh->type_code);
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
                    rc = tpush(&req, (int32_t)cx, (int32_t)cy, t);
            } else {
                for (int64_t j = 0; j < n && rc == 0; j++) {
                    double kx = floor(X[j] / RAW), ky = floor(Y[j] / RAW);
                    if (!fin_cell(kx) || !fin_cell(ky)) continue;
                    double fx = X[j] - kx * RAW, fy = Y[j] - ky * RAW;
                    if (fx >= 1 && fx <= RAW - 1 && fy >= 1 && fy <= RAW - 1 &&
                        kx >= (double)c0 && kx <= (double)c1 && ky >= (double)r0 && ky <= (double)r1 &&
                        in_cells(cl, nc, (int64_t)kx, (int64_t)ky))
                        rc = tpush(&req, (int32_t)kx, (int32_t)ky, t);
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
                if (q[i].ok) rc = tpush(&req, cl[i % nc].ix, cl[i % nc].iy, q[i].type);
        }
    }
    int64_t nreq = 0, nbad = 0;
    if (rc == 0) {
        qsort(req.v, (size_t)req.n, sizeof(trip), cmp_trip);
        qsort(pres.v, (size_t)pres.n, sizeof(trip), cmp_trip);
        for (int64_t i = 0; i < req.n; i++) {
            if (i && cmp_trip(&req.v[i], &req.v[i - 1]) == 0) continue;
            nreq++;
            if (tfind(pres.v, pres.n, req.v[i]) >= 0) continue;
            nbad++;
            k1_sample m;
            memset(&m, 0, sizeof m);
            m.lat = 0.0; m.lon = 0.0; m.err = NAN;
            m.ix = req.v[i].ix; m.iy = req.v[i].iy; m.vx = INT32_MIN; m.vy = INT32_MIN;
            m.reason = K1_R_COMPLETE; m.code = req.v[i].t;
            k1_push_sample(c->acc, K1_completeness, &m);
            K1_EMIT_DUMP(c->acc, K1_completeness, c->block->level, &m, -1, -1);
        }
        k1_add(c->acc, K1_completeness, nreq, nbad, 0.0);
    }
    free(req.v); free(pres.v); free(cl); free(q); free(types);
    return (int)rc;
}
