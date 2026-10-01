/* K1 background kinds (plan 04, Phase 2, brief 2-04): `background`, `background_boundary`
 * and `interior_cover`, with the arithmetic of `tools/quantisation_roundtrip.py`
 * (`_check_block`'s background half, `Region.outline_distance`, `Region.inside`).
 *
 * The spool side is the band's `k1_shapes` (local ring shapes + tall shapes, see `_k1.h`).
 * Outline distance: the typed vertex set (floor buckets, the four cells below-left of the
 * query, Chebyshev) and, above TOL + EPS, the nearest same-type segment (`_cheb_seg`) within
 * SEARCH (else infinity). Segment lookup is an index of 64-raw buckets per type, so only
 * segments whose bounding box grown by SEARCH reaches the query bucket are measured; any
 * segment nearer than SEARCH is among them, so the minimum is the oracle's. `inside` is the
 * even-odd scan-line test with the half-open edge rule vlo <= c < vhi, crossings paired per
 * shape in sorted order, a query being inside iff some interval has ia <= a + TOL and
 * ib >= a - TOL (the oracle's float-key trick computes exactly this, to ~1e-4 for very large
 * batches; here the comparison is exact). Build flags: -O2 -ffp-contract=off. */
#define _GNU_SOURCE
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "_k1.h"

#define OFF24 ((int64_t)1 << 24)
#define MASK26 (((int64_t)1 << 26) - 1)
#define NEAR (K1_TOL + K1_EPS)
#define BUCKET_MARGIN (K1_SEARCH + 0.01)

typedef struct { int64_t key; int32_t id; } ki;
typedef struct { int64_t key; double x, y; } vert;
typedef struct { int32_t shape; double au; } cross_t;
typedef struct { double ia, ib; } intv;

static int in_range(int64_t x, int64_t y) {
    return x >= -OFF24 && x < MASK26 - OFF24 && y >= -OFF24 && y < MASK26 - OFF24;
}
static int64_t pack2(int64_t x, int64_t y) { return ((x + OFF24) << 26) | (y + OFF24); }
static int64_t tkey(int32_t t) { return (int64_t)((uint64_t)(int64_t)t << 52); }
static int64_t fl_div(int64_t a, int64_t b) { int64_t q = a / b; return (a % b != 0 && ((a < 0) != (b < 0))) ? q - 1 : q; }

static int cmp_vert(const void *a, const void *b) {
    int64_t x = ((const vert *)a)->key, y = ((const vert *)b)->key;
    return x < y ? -1 : x > y;
}
static int cmp_ki(const void *a, const void *b) {
    const ki *x = (const ki *)a, *y = (const ki *)b;
    return x->key < y->key ? -1 : x->key > y->key ? 1 : (x->id > y->id) - (x->id < y->id);
}
static int cmp_cross(const void *a, const void *b) {
    const cross_t *x = (const cross_t *)a, *y = (const cross_t *)b;
    if (x->shape != y->shape) return x->shape < y->shape ? -1 : 1;
    return x->au < y->au ? -1 : x->au > y->au;
}
static int cmp_intv(const void *a, const void *b) {
    double x = ((const intv *)a)->ia, y = ((const intv *)b)->ia;
    return x < y ? -1 : x > y;
}

typedef struct {
    vert *v; int64_t nv;                       /* typed vertex set, sorted by key */
    double *x1, *y1, *x2, *y2; int32_t *st, *ss; uint8_t *sc;   /* edges: ends, type, shape, class */
    int64_t ns;
    ki *sk; int64_t nsk; int sk_built;         /* 2-D bucket index of all edges */
    ki *ek[2]; int64_t nek[2]; int ek_built[2];/* 1-D v-bucket index of class-2 edges */
} bgx;

static int ki_push(ki **v, int64_t *n, int64_t *cap, int64_t key, int32_t id) {
    if (*n == *cap) {
        int64_t nc = *cap ? *cap * 2 : 4096;
        ki *q = (ki *)realloc(*v, (size_t)nc * sizeof(ki));
        if (!q) return -4;
        *v = q; *cap = nc;
    }
    (*v)[*n].key = key; (*v)[*n].id = id; (*n)++;
    return 0;
}

/* vertices and edges of the shapes (Shapes.segments: closing edge for class 2 only; an edge
 * from a vertex to itself is dropped) */
static int bgx_build(bgx *G, const k1_shapes *H) {
    memset(G, 0, sizeof *G);
    G->v = (vert *)malloc((size_t)(H->ncoord + 1) * sizeof(vert));
    int64_t ne = H->ncoord + 1;
    G->x1 = (double *)malloc((size_t)ne * 8); G->y1 = (double *)malloc((size_t)ne * 8);
    G->x2 = (double *)malloc((size_t)ne * 8); G->y2 = (double *)malloc((size_t)ne * 8);
    G->st = (int32_t *)malloc((size_t)ne * 4); G->ss = (int32_t *)malloc((size_t)ne * 4);
    G->sc = (uint8_t *)malloc((size_t)ne);
    if (!G->v || !G->x1 || !G->y1 || !G->x2 || !G->y2 || !G->st || !G->ss || !G->sc) return -4;
    for (int64_t s = 0; s < H->n; s++) {
        int64_t a = H->off[s], n = H->off[s + 1] - a;
        int64_t tk = tkey(H->type[s]);
        for (int64_t i = 0; i < n; i++) {
            double fx = floor(H->x[a + i]), fy = floor(H->y[a + i]);
            if (fx >= -(double)OFF24 && fx < (double)(MASK26 - OFF24) &&
                fy >= -(double)OFF24 && fy < (double)(MASK26 - OFF24)) {
                G->v[G->nv].key = tk | pack2((int64_t)fx, (int64_t)fy);
                G->v[G->nv].x = H->x[a + i]; G->v[G->nv].y = H->y[a + i];
                G->nv++;
            }
            int64_t b = i + 1 < n ? a + i + 1 : (H->cls[s] == 2 ? a : -1);
            if (b < 0 || b == a + i) continue;
            G->x1[G->ns] = H->x[a + i]; G->y1[G->ns] = H->y[a + i];
            G->x2[G->ns] = H->x[b]; G->y2[G->ns] = H->y[b];
            G->st[G->ns] = H->type[s]; G->ss[G->ns] = (int32_t)s; G->sc[G->ns] = H->cls[s] == 2;
            G->ns++;
        }
    }
    qsort(G->v, (size_t)G->nv, sizeof(vert), cmp_vert);
    return 0;
}

static void bgx_free(bgx *G) {
    free(G->v); free(G->x1); free(G->y1); free(G->x2); free(G->y2); free(G->st); free(G->ss);
    free(G->sc); free(G->sk); free(G->ek[0]); free(G->ek[1]);
}

/* nearest same-type vertex, Chebyshev, over the floor buckets (X-1..X, Y-1..Y) */
static double vert_nearest(const bgx *G, int64_t X, int64_t Y, int32_t t) {
    double best = INFINITY;
    for (int dx = -1; dx <= 0; dx++)
        for (int dy = -1; dy <= 0; dy++) {
            int64_t qx = X + dx, qy = Y + dy;
            if (!in_range(qx, qy)) continue;
            int64_t key = tkey(t) | pack2(qx, qy), lo = 0, hi = G->nv;
            while (lo < hi) { int64_t m = lo + (hi - lo) / 2; if (G->v[m].key < key) lo = m + 1; else hi = m; }
            for (int64_t i = lo; i < G->nv && G->v[i].key == key; i++) {
                double ax = fabs(G->v[i].x - (double)X), ay = fabs(G->v[i].y - (double)Y);
                double d = ax > ay ? ax : ay;
                if (d < best) best = d;
            }
        }
    return best;
}

/* every edge is listed in each typed 64-raw bucket within SEARCH of it (per x slab, the y
 * extent of the edge inside the slab) */
static int seg_index(bgx *G) {
    if (G->sk_built) return 0;
    G->sk_built = 1;
    int64_t cap = 0, n = 0;
    ki *v = NULL;
    const double P = K1_SEG_BUCKET, M = BUCKET_MARGIN;
    for (int64_t s = 0; s < G->ns; s++) {
        double x1 = G->x1[s], y1 = G->y1[s], x2 = G->x2[s], y2 = G->y2[s];
        if (!isfinite(x1 + y1 + x2 + y2) || fabs(x1) > 1e9 || fabs(y1) > 1e9 || fabs(x2) > 1e9 || fabs(y2) > 1e9) continue;
        int64_t tk = tkey(G->st[s]);
        double sx0 = x1 < x2 ? x1 : x2, sx1 = x1 < x2 ? x2 : x1;
        double sy0 = y1 < y2 ? y1 : y2, sy1 = y1 < y2 ? y2 : y1;
        int64_t b0 = (int64_t)floor((sx0 - M) / P), b1 = (int64_t)floor((sx1 + M) / P);
        for (int64_t bx = b0; bx <= b1; bx++) {
            double xa = sx0 > (double)bx * P - M ? sx0 : (double)bx * P - M;
            double xb = sx1 < (double)(bx + 1) * P + M ? sx1 : (double)(bx + 1) * P + M;
            double ya = sy0, yb = sy1;
            if (x1 != x2) {
                double k = (y2 - y1) / (x2 - x1);
                ya = y1 + (xa - x1) * k; yb = y1 + (xb - x1) * k;
                if (ya > yb) { double t = ya; ya = yb; yb = t; }
                ya -= 0.01; yb += 0.01;
            }
            int64_t c0 = (int64_t)floor((ya - M) / P), c1 = (int64_t)floor((yb + M) / P);
            for (int64_t by = c0; by <= c1; by++) {
                if (!in_range(bx, by)) continue;
                if (ki_push(&v, &n, &cap, tk | pack2(bx, by), (int32_t)s) < 0) { free(v); return -4; }
            }
        }
    }
    qsort(v, (size_t)n, sizeof(ki), cmp_ki);
    G->sk = v; G->nsk = n;
    return 0;
}

static int64_t ki_lower(const ki *v, int64_t n, int64_t key) {
    int64_t lo = 0, hi = n;
    while (lo < hi) { int64_t m = lo + (hi - lo) / 2; if (v[m].key < key) lo = m + 1; else hi = m; }
    return lo;
}

/* _seg_distance for one point: the nearest same-type edge, infinity beyond SEARCH */
static double seg_dist(bgx *G, int64_t X, int64_t Y, int32_t t) {
    if (seg_index(G) < 0) return INFINITY;
    int64_t bx = fl_div(X, K1_SEG_BUCKET), by = fl_div(Y, K1_SEG_BUCKET);
    if (!in_range(bx, by)) return INFINITY;
    int64_t key = tkey(t) | pack2(bx, by);
    double best = INFINITY;
    for (int64_t i = ki_lower(G->sk, G->nsk, key); i < G->nsk && G->sk[i].key == key; i++) {
        int32_t s = G->sk[i].id;
        double d = k1_cheb_pt_seg((double)X, (double)Y, G->x1[s], G->y1[s], G->x2[s], G->y2[s]);
        if (d < best) best = d;
    }
    return best > K1_SEARCH ? INFINITY : best;
}

static double outline_distance(bgx *G, int64_t X, int64_t Y, int32_t t) {
    if (X == INT64_MIN || Y == INT64_MIN) return INFINITY;
    double d = vert_nearest(G, X, Y, t);
    if (d > NEAR) {
        double s = seg_dist(G, X, Y, t);
        if (s < d) d = s;
    }
    return d;
}

/* ------------------------------------------------------------------ inside() */

typedef k1_qin q_t;

static int cmp_qi(const void *a, const void *b, void *ctx) {
    const q_t *q = (const q_t *)ctx;
    const q_t *x = &q[*(const int64_t *)a], *y = &q[*(const int64_t *)b];
    if (x->orient != y->orient) return x->orient < y->orient ? -1 : 1;
    if (x->type != y->type) return x->type < y->type ? -1 : 1;
    if (x->c != y->c) return x->c < y->c ? -1 : 1;
    int64_t i = *(const int64_t *)a, j = *(const int64_t *)b;
    return (i > j) - (i < j);
}

/* class-2 edges bucketed along their v (across-the-line) extent, per orientation and type */
static int edge_index(bgx *G, int o) {
    if (G->ek_built[o]) return 0;
    G->ek_built[o] = 1;
    int64_t cap = 0, n = 0;
    ki *v = NULL;
    for (int64_t s = 0; s < G->ns; s++) {
        if (!G->sc[s]) continue;
        double v1 = o ? G->x1[s] : G->y1[s], v2 = o ? G->x2[s] : G->y2[s];
        double vlo = v1 < v2 ? v1 : v2, vhi = v1 < v2 ? v2 : v1;
        if (!(vlo < vhi) || fabs(vlo) > 1e9 || fabs(vhi) > 1e9) continue;
        int64_t tk = tkey(G->st[s]);
        for (int64_t b = (int64_t)floor(vlo / K1_SEG_BUCKET); b <= (int64_t)floor(vhi / K1_SEG_BUCKET); b++)
            if (ki_push(&v, &n, &cap, tk | (b + OFF24), (int32_t)s) < 0) { free(v); return -4; }
    }
    qsort(v, (size_t)n, sizeof(ki), cmp_ki);
    G->ek[o] = v; G->nek[o] = n;
    return 0;
}

static int inside_batch(bgx *G, q_t *q, int64_t nq) {
    if (nq == 0) return 0;
    int64_t *ord = (int64_t *)malloc((size_t)nq * sizeof(int64_t));
    if (!ord) return -4;
    for (int64_t i = 0; i < nq; i++) { ord[i] = i; q[i].ok = 0; }
#if defined(__GLIBC__)
    qsort_r(ord, (size_t)nq, sizeof(int64_t), cmp_qi, q);
#else
#error "qsort_r with the GNU argument order is required"
#endif
    cross_t *cr = NULL; intv *iv = NULL; double *pmax = NULL;
    int64_t crcap = 0, ivcap = 0, rc = 0;
    for (int64_t g0 = 0; g0 < nq && rc == 0;) {
        const q_t *h = &q[ord[g0]];
        int64_t g1 = g0;
        while (g1 < nq && q[ord[g1]].orient == h->orient && q[ord[g1]].type == h->type && q[ord[g1]].c == h->c) g1++;
        int o = h->orient;
        double c = h->c;
        if ((rc = edge_index(G, o)) < 0) break;
        int64_t ncr = 0;
        if (fabs(c) < 1e9) {
            int64_t key = tkey(h->type) | (fl_div((int64_t)floor(c), K1_SEG_BUCKET) + OFF24);
            for (int64_t i = ki_lower(G->ek[o], G->nek[o], key); i < G->nek[o] && G->ek[o][i].key == key; i++) {
                int32_t s = G->ek[o][i].id;
                double u1 = o ? G->y1[s] : G->x1[s], v1 = o ? G->x1[s] : G->y1[s];
                double u2 = o ? G->y2[s] : G->x2[s], v2 = o ? G->x2[s] : G->y2[s];
                double vlo = v1 < v2 ? v1 : v2, vhi = v1 < v2 ? v2 : v1;
                if (!(vlo <= c && c < vhi)) continue;
                if (ncr == crcap) {
                    crcap = crcap ? crcap * 2 : 256;
                    cross_t *t = (cross_t *)realloc(cr, (size_t)crcap * sizeof(cross_t));
                    if (!t) { rc = -4; break; }
                    cr = t;
                }
                cr[ncr].shape = G->ss[s];
                cr[ncr].au = u1 + (c - v1) * (u2 - u1) / (v2 - v1);
                ncr++;
            }
        }
        if (rc) break;
        qsort(cr, (size_t)ncr, sizeof(cross_t), cmp_cross);
        int64_t niv = 0;
        for (int64_t i = 0; i + 1 < ncr;) {
            if (cr[i].shape != cr[i + 1].shape) { i++; continue; }
            int64_t j = i;                              /* pair (0,1), (2,3).. of one shape */
            while (j + 1 < ncr && cr[j].shape == cr[i].shape && cr[j + 1].shape == cr[i].shape) {
                if (niv == ivcap) {
                    ivcap = ivcap ? ivcap * 2 : 256;
                    intv *t = (intv *)realloc(iv, (size_t)ivcap * sizeof(intv));
                    double *p = (double *)realloc(pmax, (size_t)ivcap * sizeof(double));
                    if (!t || !p) { if (t) iv = t; if (p) pmax = p; rc = -4; break; }
                    iv = t; pmax = p;
                }
                iv[niv].ia = cr[j].au; iv[niv].ib = cr[j + 1].au; niv++;
                j += 2;
            }
            if (rc) break;
            while (j < ncr && cr[j].shape == cr[i].shape) j++;   /* an odd last crossing is unpaired */
            i = j;
        }
        if (rc) break;
        qsort(iv, (size_t)niv, sizeof(intv), cmp_intv);
        for (int64_t i = 0; i < niv; i++) pmax[i] = (i && pmax[i - 1] > iv[i].ib) ? pmax[i - 1] : iv[i].ib;
        for (int64_t k = g0; k < g1; k++) {
            q_t *qq = &q[ord[k]];
            int64_t lo = 0, hi = niv;                    /* last interval with ia <= a + TOL */
            while (lo < hi) { int64_t m = lo + (hi - lo) / 2; if (iv[m].ia <= qq->a + K1_TOL) lo = m + 1; else hi = m; }
            qq->ok = lo > 0 && pmax[lo - 1] >= qq->a - K1_TOL;
        }
        g0 = g1;
    }
    free(ord); free(cr); free(iv); free(pmax);
    return (int)rc;
}

/* ------------------------------------------------------------------ the kinds */

typedef struct { q_t *q; k1_sample *m; int32_t *shape, *vert; int64_t n, cap; int dump; } qs_t;

static int qs_push(qs_t *s, int orient, int32_t type, double c, double a, const k1_sample *m,
                   int32_t shape, int32_t vert) {
    if (s->n == s->cap) {
        int64_t nc = s->cap ? s->cap * 2 : 1024;
        q_t *q = (q_t *)realloc(s->q, (size_t)nc * sizeof(q_t));
        if (!q) return -4;
        s->q = q;
        k1_sample *mm = (k1_sample *)realloc(s->m, (size_t)nc * sizeof(k1_sample));
        if (!mm) return -4;
        s->m = mm;
        if (s->dump) {                       /* identity side arrays exist only when dumping */
            int32_t *sh = (int32_t *)realloc(s->shape, (size_t)nc * sizeof(int32_t));
            if (!sh) return -4;
            s->shape = sh;
            int32_t *vt = (int32_t *)realloc(s->vert, (size_t)nc * sizeof(int32_t));
            if (!vt) return -4;
            s->vert = vt;
        }
        s->cap = nc;
    }
    s->q[s->n].orient = orient; s->q[s->n].type = type; s->q[s->n].c = c; s->q[s->n].a = a;
    s->q[s->n].ok = 0;
    s->m[s->n] = *m;
    if (s->dump) {
        s->shape[s->n] = shape;
        s->vert[s->n] = vert;
    }
    s->n++;
    return 0;
}

static int64_t to_i64(double v) { return (isfinite(v) && fabs(v) < 9.2e18) ? (int64_t)v : INT64_MIN; }
static int32_t sat32(double v) {
    if (!(v == v)) return INT32_MIN + 1;
    if (v < -2147483647.0) return INT32_MIN + 1;
    return v > 2147483647.0 ? INT32_MAX : (int32_t)v;
}

/* the band's shape index, built once and shared by the kind groups */
static int bgx_get(k1_ctx *c, bgx **out) {
    if (!c->bgx) {
        bgx *G = (bgx *)malloc(sizeof *G);
        if (!G) return -4;
        int rc = bgx_build(G, c->shapes);
        if (rc < 0) { bgx_free(G); free(G); return rc; }
        c->bgx = G;
    }
    *out = (bgx *)c->bgx;
    return 0;
}

void k1_bg_release(k1_ctx *c) {
    if (!c->bgx) return;
    bgx_free((bgx *)c->bgx);
    free(c->bgx);
    c->bgx = NULL;
}

int k1_bg_inside(k1_ctx *c, k1_qin *q, int64_t n) {
    bgx *G = NULL;
    if (n == 0) return 0;
    if (!c->shapes) { for (int64_t i = 0; i < n; i++) q[i].ok = 0; return 0; }
    int rc = bgx_get(c, &G);
    return rc < 0 ? rc : inside_batch(G, q, n);
}

int k1_bg_kinds(k1_ctx *c) {
    const k1_shapes *H = c->shapes;
    int64_t nv = 0;
    for (int64_t i = 0; i < c->nwalk; i++) {
        const d1_walk *w = &c->walk[i];
        const d1_frame *f = c->leaf[i].ok && w->frame >= 0 ? &c->frame[w->frame] : NULL;
        if (f && f->has_bg) nv++;
    }
    if (nv == 0 || !H) return 0;                       /* nothing decoded to check */
    bgx *G = NULL;
    qs_t Q = {0};
    Q.dump = c->acc->dump != NULL;
    int rc = bgx_get(c, &G);
    int64_t nb = 0, nb_bad = 0, onb_n = 0, onb_bad = 0, ncov = 0, cov_bad = 0;
    double nb_worst = 0.0, onb_worst = 0.0;
    for (int64_t i = 0; i < c->nwalk && rc == 0; i++) {
        const k1_leaf *lf = &c->leaf[i];
        const d1_walk *w = &c->walk[i];
        const d1_frame *f = lf->ok && w->frame >= 0 ? &c->frame[w->frame] : NULL;
        if (!f) continue;
        for (uint32_t k = 0; f->has_bg && k < f->bgshape_n && rc == 0; k++) {
            const d1_bgshape *sh = &c->bgshape[f->bgshape_first + k];
            if (sh->coord_n == 0) continue;
            int allb = 1;
            double sum = 0.0;
            for (uint32_t v = 0; v < sh->coord_n && rc == 0; v++) {
                const d1_bgcoord *cd = &c->bgcoord[sh->coord_first + v];
                const d1_bgcoord *nx = &c->bgcoord[sh->coord_first + (v + 1 < sh->coord_n ? v + 1 : 0)];
                double fx, fy;
                k1_frame_raw(lf, cd->lat, cd->lon, &fx, &fy);
                /* X, Y: the lattice position rounded (not the frame's) */
                int64_t X = to_i64(nearbyint(k1_gx(&c->lat, cd->lon)));
                int64_t Y = to_i64(nearbyint(k1_gy(&c->lat, cd->lat)));
                int64_t XN = to_i64(nearbyint(k1_gx(&c->lat, nx->lon)));
                int64_t YN = to_i64(nearbyint(k1_gy(&c->lat, nx->lat)));
                int onh = Y == lf->y0 || Y == lf->y1, onv = X == lf->x0 || X == lf->x1, onb = onh || onv;
                if (!onb) allb = 0;
                sum += (double)X * (double)YN - (double)XN * (double)Y;
                double d = outline_distance(G, X, Y, sh->type_code);
                int near = d <= NEAR;
                k1_sample m = k1_make_sample(c->walk + i, lf, cd->lat, cd->lon, sat32(nearbyint(fx)),
                                             sat32(nearbyint(fy)), onb ? K1_R_BG_BOUNDARY : K1_R_BG,
                                             sh->type_code, d);
                if (!onb) {
                    nb++;
                    if (!near) {
                        nb_bad++;
                        k1_push_sample(c->acc, K1_background, &m);
                        K1_EMIT_DUMP(c->acc, K1_background, c->block->level, &m,
                                     (int32_t)k, (int32_t)v);
                    } else if (d > nb_worst) nb_worst = d;
                } else {
                    onb_n++;
                    if (near) { if (d > onb_worst) onb_worst = d; }
                    else rc = qs_push(&Q, onh ? 0 : 1, sh->type_code, onh ? (double)Y : (double)X,
                                      onh ? (double)X : (double)Y, &m, (int32_t)k, (int32_t)v);
                }
            }
            if (sh->shape_class == 2 && allb) {
                double area = fabs(sum) / 2.0;
                double rect = (double)((lf->x1 - lf->x0) * (lf->y1 - lf->y0));
                if (fabs(area - rect) < 0.5) {
                    k1_sample m = k1_make_sample(c->walk + i, lf, 0.0, 0.0, INT32_MIN, INT32_MIN,
                                                 K1_R_COVER, sh->type_code, NAN);
                    ncov++;
                    rc = qs_push(&Q, 0, sh->type_code, ((double)lf->y0 + (double)lf->y1) / 2.0,
                                 ((double)lf->x0 + (double)lf->x1) / 2.0, &m, (int32_t)k, -1);
                    Q.m[Q.n - 1].reason = K1_R_COVER;
                }
            }
        }
    }
    if (rc == 0) rc = inside_batch(G, Q.q, Q.n);
    if (rc == 0) {
        for (int64_t i = 0; i < Q.n; i++) {
            int cover = Q.m[i].reason == K1_R_COVER;
            if (Q.q[i].ok) continue;
            if (cover) {
                cov_bad++;
                k1_push_sample(c->acc, K1_interior_cover, &Q.m[i]);
                K1_EMIT_DUMP(c->acc, K1_interior_cover, c->block->level, &Q.m[i],
                             Q.shape[i], Q.vert[i]);
            } else {
                onb_bad++;
                k1_push_sample(c->acc, K1_background_boundary, &Q.m[i]);
                K1_EMIT_DUMP(c->acc, K1_background_boundary, c->block->level, &Q.m[i],
                             Q.shape[i], Q.vert[i]);
            }
        }
        k1_add(c->acc, K1_background, nb, nb_bad, nb_worst);
        k1_add(c->acc, K1_background_boundary, onb_n, onb_bad, onb_worst);
        k1_add(c->acc, K1_interior_cover, ncov, cov_bad, 0.0);
    }
    free(Q.q); free(Q.m); free(Q.shape); free(Q.vert);
    return rc;
}
