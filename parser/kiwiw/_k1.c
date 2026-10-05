/* K1 -- the C checker core (plan 04, Phase 2, brief 2-03). Layouts and the
 * contract are in `_k1.h`; the arithmetic mirrors `tools/quantisation_roundtrip.py`
 * operation for operation (build flags -O2 -ffp-contract=off: no fused ops). */
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "_k1.h"

/* ------------------------------------------------------------------ layout */

typedef struct { const char *name, *kind; int off; } k1_fspec;
#define K1_SPEC(S, T, N) {#N, #T, (int)offsetof(S, N)},
#define K1_SPECS(NAME, S) static const k1_fspec kspec_##NAME[] = { K1_F_##NAME(K1_SPEC, S) };
K1_SPECS(KIND, k1_kind) K1_SPECS(SAMPLE, k1_sample) K1_SPECS(DUMP, k1_dump)
static const struct { const char *name; int size, nf; const k1_fspec *f; } KT[K1_NTABLES] = {
    {"kind", sizeof(k1_kind), sizeof(kspec_KIND) / sizeof(kspec_KIND[0]), kspec_KIND},
    {"sample", sizeof(k1_sample), sizeof(kspec_SAMPLE) / sizeof(kspec_SAMPLE[0]), kspec_SAMPLE},
    {"dump", sizeof(k1_dump), sizeof(kspec_DUMP) / sizeof(kspec_DUMP[0]), kspec_DUMP},
};
int kw_k1_ntables(void) { return K1_NTABLES; }
const char *kw_k1_table_name(int t) { return t >= 0 && t < K1_NTABLES ? KT[t].name : NULL; }
int kw_k1_row_size(int t) { return t >= 0 && t < K1_NTABLES ? KT[t].size : -1; }
int kw_k1_nfields(int t) { return t >= 0 && t < K1_NTABLES ? KT[t].nf : -1; }
const char *kw_k1_field_name(int t, int i) { return KT[t].f[i].name; }
const char *kw_k1_field_kind(int t, int i) { return KT[t].f[i].kind; }
int kw_k1_field_off(int t, int i) { return KT[t].f[i].off; }
int kw_k1_sample_n(void) { return K1_SAMPLE; }
int kw_k1_tallrow_size(void) { return sizeof(k1_tallrow); }
int kw_k1_tallrow_mult_off(void) { return offsetof(k1_tallrow, mult); }

#define K1_STR(n) #n,
static const char *const N_KINDS[] = { K1_KINDS(K1_STR) };
static const char *const N_EXPL[] = { K1_EXPLAINED(K1_STR) };
static const char *const N_COLS[] = { K1_COLS(K1_STR) };
static const char *const N_STATS[] = { K1_STATS(K1_STR) };
int kw_k1_count(int w) { return w == 0 ? K1_NKINDS : w == 1 ? K1_NEXPLAINED : w == 2 ? K1_NCOLS : w == 3 ? K1_NSTATS : -1; }
const char *kw_k1_name(int w, int i) {
    if (i < 0 || i >= kw_k1_count(w)) return NULL;
    return w == 0 ? N_KINDS[i] : w == 1 ? N_EXPL[i] : w == 2 ? N_COLS[i] : N_STATS[i];
}

/* -------------------------------------------------------------- accumulator */

void k1_add(k1_acc *a, int kind, int64_t checked, int64_t failing, double worst) {
    k1_kind *k = &a->kind[kind];
    k->checked += (uint64_t)checked;
    k->failing += (uint64_t)failing;
    if (isfinite(worst) && worst > k->worst) k->worst = worst;
}

static int dcmp(double a, double b) {          /* NaN sorts last and equals NaN: a total order */
    if (isnan(a)) return isnan(b) ? 0 : 1;
    if (isnan(b)) return -1;
    return a < b ? -1 : a > b ? 1 : 0;
}
static int icmp(int64_t a, int64_t b) { return a < b ? -1 : a > b ? 1 : 0; }

/* the total sample order: cell row, cell column, leaf path (lexicographic), vertex raw,
 * reason, code, then lat, lon, err so equal keys mean equal rows */
int k1_sample_cmp(const k1_sample *a, const k1_sample *b) {
    int c;
    if ((c = icmp(a->iy, b->iy)) || (c = icmp(a->ix, b->ix))) return c;
    const k1_u16 *pa = &a->p0, *pb = &b->p0;     /* p0..p6 are consecutive */
    int n = a->depth < b->depth ? a->depth : b->depth;
    for (int i = 0; i < n; i++) if ((c = icmp(pa[i], pb[i]))) return c;
    if ((c = icmp(a->depth, b->depth)) || (c = icmp(a->vx, b->vx)) || (c = icmp(a->vy, b->vy)) ||
        (c = icmp(a->reason, b->reason)) || (c = icmp(a->code, b->code)) ||
        (c = dcmp(a->lat, b->lat)) || (c = dcmp(a->lon, b->lon)))
        return c;
    return dcmp(a->err, b->err);
}

void k1_push_sample(k1_acc *a, int kind, const k1_sample *s) {
    k1_kind *k = &a->kind[kind];
    k1_sample *v = a->smp + (size_t)kind * K1_SAMPLE;
    int n = (int)k->nsamples, i = n;
    if (n == K1_SAMPLE && k1_sample_cmp(s, &v[n - 1]) >= 0) return;
    if (n < K1_SAMPLE) k->nsamples = (k1_u32)++n; else i = n - 1;
    while (i > 0 && k1_sample_cmp(s, &v[i - 1]) < 0) { v[i] = v[i - 1]; i--; }
    v[i] = *s;
}

/* One dump row per failing item (brief 3-02). `K1_F_DUMP` begins with the exact
 * `K1_F_SAMPLE` fields in the same order, so the sample copies in directly; the
 * sink keeps counting past `cap` so the caller learns the rows it needs. The 3-03
 * diagnostic columns are set to their sentinels here; `k1_diag_fill` overwrites them
 * for the three background-family kinds. Returns the row, or NULL when not written. */
k1_dump *k1_emit_dump(k1_acc *a, int kind, int level, const k1_sample *s, int32_t shape,
                      int32_t vert) {
    k1_dumpsink *d = a->dump;
    int64_t i = d->n++;
    if (i >= d->cap) { d->overflow = 1; return NULL; }
    k1_dump *r = &d->rows[i];
    memset(r, 0, sizeof *r);              /* zero the struct padding too: files must cmp */
    memcpy(r, s, sizeof(k1_sample));
    r->kind = (k1_u8)kind;
    r->level = (k1_u8)level;
    r->shape = shape;
    r->vert = vert;
    r->onb = 0;
    r->d_any = NAN;
    r->any_type = -1;
    r->in_eo_same = r->in_wn_same = r->in_eo_any = 0;
    r->src_ix = INT32_MIN; r->src_iy = INT32_MIN; r->src_rec = -1; r->src_tall = 0;
    r->src_nv = -1; r->src_maxseg = NAN; r->d_src = NAN;
    r->dcls = -1; r->dnv = -1;
    return r;
}

/* ----------------------------------------------------------------- numerics */

static double np_mod(double a, double b) {          /* numpy float mod */
    double m = fmod(a, b);
    if (m != 0.0) { if ((b < 0) != (m < 0)) m += b; } else m = copysign(0.0, b);
    return m;
}
static double lon_span(double lo, double hi) { double s = hi - lo; return s < 0 ? s + 360.0 : s; }
static double dlon_of(const k1_lat *L, double lon) {
    double d = lon - L->lon0;
    return np_mod(d - L->wlo, 360.0) + L->wlo;
}
static double gx(const k1_lat *L, double lon) { return dlon_of(L, lon) / L->cell_lon * (double)K1_RAW; }
static double gy(const k1_lat *L, double lat) { return (lat - L->lat0) / L->cell_lat * (double)K1_RAW; }
static int64_t to_i64(double v) {                  /* numpy astype(int64) of a rint'ed float */
    return (isfinite(v) && fabs(v) < 9.2e18) ? (int64_t)v : INT64_MIN;
}
static int32_t sat32(double v) {
    if (!(v == v)) return INT32_MIN + 1;
    if (v < -2147483647.0) return INT32_MIN + 1;
    return v > 2147483647.0 ? INT32_MAX : (int32_t)v;
}
static int64_t fldiv(int64_t a, int64_t b) { int64_t q = a / b; return (a % b != 0 && ((a < 0) != (b < 0))) ? q - 1 : q; }

typedef struct { double lat_lo, lat_hi, lon_lo, lon_hi; } bnds;
/* walk.py _block_base_bounds (same as `_d1.c`'s static copy) */
static bnds block_bounds(const d1_block *B) {
    double ls = lon_span(B->cov_lon_lo, B->cov_lon_hi), las = B->cov_lat_hi - B->cov_lat_lo;
    double mx = ls / (double)B->grid_nx, my = las / (double)B->grid_ny;
    int64_t npc_lng = 1 + B->npg0, npc_lat = 1 + B->npl0;
    int64_t nbl_lng = 1 + B->n_blocks_lng, nbl_lat = 1 + B->n_blocks_lat;
    int64_t bix = ((int64_t)B->bsx * nbl_lng + B->blx) * npc_lng;
    int64_t biy = ((int64_t)B->bsy * nbl_lat + B->bly) * npc_lat;
    double blon = B->cov_lon_lo + (double)bix * mx, blat = B->cov_lat_lo + (double)biy * my;
    bnds r = {blat, blat + (double)npc_lat * my, blon, blon + (double)npc_lng * mx};
    return r;
}
static double rnd(double v) { return nearbyint(v); }  /* python round(): half to even */

/* ------------------------------------------------------------------- spool */

typedef struct {
    const uint8_t *idx, *data;
    int64_t idx_len, data_len, n;
    int ncols;
    int want[96];
    const int32_t *esz, *ckey;
} k1_spool;

typedef struct { const uint8_t *c[K1_NCOLS]; int64_t n[9]; } k1_cell;

static double rd_f64(const uint8_t *p, int64_t i) { double v; memcpy(&v, p + 8 * i, 8); return v; }
static int32_t rd_i32(const uint8_t *p, int64_t i) { int32_t v; memcpy(&v, p + 4 * i, 4); return v; }
static uint64_t rd_u64(const uint8_t *p, int64_t i) { uint64_t v; memcpy(&v, p + 8 * i, 8); return v; }

static int spool_open(k1_spool *S, const uint8_t *idx, int64_t il, const uint8_t *data,
                      int64_t dl, const int32_t *colmap, const int32_t *esz,
                      const int32_t *ckey, int64_t ncols) {
    if (!idx || il < 48 || ncols < 1 || ncols > 96 || memcmp(idx, "KWSPIDX1", 8) != 0) return -3;
    S->n = (int64_t)rd_u64(idx, 1);
    if (S->n < 0 || il < 48 + 24 * S->n) return -3;
    S->idx = idx; S->idx_len = il; S->data = data; S->data_len = dl;
    S->ncols = (int)ncols; S->esz = esz; S->ckey = ckey;
    for (int i = 0; i < ncols; i++) S->want[i] = -1;
    for (int k = 0; k < K1_NCOLS; k++) {
        if (colmap[k] < 0 || colmap[k] >= ncols) return -1;
        S->want[colmap[k]] = k;
    }
    return 0;
}
static int32_t sp_ix(const k1_spool *S, int64_t i) { return rd_i32(S->idx + 48, i); }
static int32_t sp_iy(const k1_spool *S, int64_t i) { return rd_i32(S->idx + 48 + 4 * S->n, i); }
static int64_t lower_iy(const k1_spool *S, int64_t v) {   /* np.searchsorted(iy, v, "left") */
    int64_t lo = 0, hi = S->n;
    while (lo < hi) { int64_t m = lo + (hi - lo) / 2; if (sp_iy(S, m) < v) lo = m + 1; else hi = m; }
    return lo;
}
static int parse_cell(const k1_spool *S, int64_t i, k1_cell *c) {
    uint64_t off = rd_u64(S->idx + 48 + 8 * S->n, i), len = rd_u64(S->idx + 48 + 16 * S->n, i);
    if (off > (uint64_t)S->data_len || len > (uint64_t)S->data_len - off || len < 72) return -3;
    const uint8_t *r = S->data + off;
    uint64_t cnt[9], pos = 72;
    for (int k = 0; k < 9; k++) { cnt[k] = rd_u64(r, k); c->n[k] = (int64_t)cnt[k]; }
    memset(c->c, 0, sizeof c->c);
    for (int col = 0; col < S->ncols; col++) {
        if (S->ckey[col] < 0 || S->ckey[col] >= 9) return -3;
        uint64_t n = cnt[S->ckey[col]];
        if (n > len) return -3;
        uint64_t sz = n * (uint64_t)S->esz[col];
        if (pos + sz > len) return -3;
        if (S->want[col] >= 0) c->c[S->want[col]] = r + pos;
        pos += sz + (8 - sz % 8) % 8;
    }
    return pos > len ? -3 : 0;
}

/* ------------------------------------------------------------------ region */

typedef struct { double x, y; int64_t key; } k1_pt;
typedef struct { k1_pt *p; int64_t n, cap; } k1_pts;
typedef struct { double x1, y1, x2, y2; } k1_seg;
typedef struct { int64_t key; int32_t seg; } k1_sk;

struct k1_region {
    k1_pts nodes, rpts, names, names_y;
    k1_shapes shp;
    int32_t *oix, *oiy; int64_t nown, ownmax;   /* spool cells inside the block rectangle */
    k1_seg *seg; int64_t nseg, segcap;
    k1_sk *sk; int64_t nsk; int sk_built;
    int64_t ncells;
};

#define OFF24 ((int64_t)1 << 24)
#define MASK26 (((int64_t)1 << 26) - 1)
static int in_range(int64_t x, int64_t y) {
    return x >= -OFF24 && x < MASK26 - OFF24 && y >= -OFF24 && y < MASK26 - OFF24;
}
static int64_t pack(int64_t x, int64_t y) { return ((x + OFF24) << 26) | (y + OFF24); }

static int pts_push(k1_pts *s, double x, double y) {
    if (s->n == s->cap) {
        int64_t nc = s->cap ? s->cap * 2 : 1024;
        k1_pt *q = (k1_pt *)realloc(s->p, (size_t)nc * sizeof(k1_pt));
        if (!q) return -4;
        s->p = q; s->cap = nc;
    }
    s->p[s->n].x = x; s->p[s->n].y = y; s->p[s->n].key = 0; s->n++;
    return 0;
}
static int cmp_key(const void *a, const void *b) {
    int64_t x = ((const k1_pt *)a)->key, y = ((const k1_pt *)b)->key;
    return x < y ? -1 : x > y;
}
static int cmp_y(const void *a, const void *b) {
    double x = ((const k1_pt *)a)->y, y = ((const k1_pt *)b)->y;
    return x < y ? -1 : x > y;
}
/* PointSet: floor-bucketed, points outside the key range dropped, sorted by key */
static void pts_key(k1_pts *s) {
    int64_t m = 0;
    for (int64_t i = 0; i < s->n; i++) {
        double fx = floor(s->p[i].x), fy = floor(s->p[i].y);
        if (!(fx >= -(double)OFF24 && fx < (double)(MASK26 - OFF24) &&
              fy >= -(double)OFF24 && fy < (double)(MASK26 - OFF24))) continue;
        s->p[m] = s->p[i];
        s->p[m].key = pack((int64_t)fx, (int64_t)fy);
        m++;
    }
    s->n = m;
    qsort(s->p, (size_t)m, sizeof(k1_pt), cmp_key);
}
static double nearest(const k1_pts *s, int64_t X, int64_t Y) {
    double best = INFINITY;
    for (int dx = -1; dx <= 0; dx++)
        for (int dy = -1; dy <= 0; dy++) {
            int64_t qx = X + dx, qy = Y + dy;
            if (!in_range(qx, qy)) continue;
            int64_t key = pack(qx, qy), lo = 0, hi = s->n;
            while (lo < hi) { int64_t m = lo + (hi - lo) / 2; if (s->p[m].key < key) lo = m + 1; else hi = m; }
            for (int64_t i = lo; i < s->n && s->p[i].key == key; i++) {
                double ax = fabs(s->p[i].x - (double)X), ay = fabs(s->p[i].y - (double)Y);
                double d = ax > ay ? ax : ay;
                if (d < best) best = d;
            }
        }
    return best;
}

/* _cheb_seg for one point and one segment */
static double cheb_seg(double px, double py, const k1_seg *g) {
    double ax = g->x1 - px, ay = g->y1 - py, bx = g->x2 - g->x1, by = g->y2 - g->y1;
    double best = fabs(ax) > fabs(ay) ? fabs(ax) : fabs(ay);
    double c = fabs(ax + bx) > fabs(ay + by) ? fabs(ax + bx) : fabs(ay + by);
    if (c < best) best = c;
    const double num[4] = {-ax, -ay, ay - ax, -(ax + ay)}, den[4] = {bx, by, bx - by, bx + by};
    for (int k = 0; k < 4; k++) {
        double t = num[k] / den[k];
        if (!isfinite(t)) t = 0.0;
        t = t < 0.0 ? 0.0 : t > 1.0 ? 1.0 : t;
        double u = fabs(ax + bx * t), v = fabs(ay + by * t);
        c = u > v ? u : v;
        if (c < best) best = c;
    }
    return best;
}

double k1_cheb_pt_seg(double px, double py, double x1, double y1, double x2, double y2) {
    k1_seg g = {x1, y1, x2, y2};
    return cheb_seg(px, py, &g);
}

static int seg_push(struct k1_region *R, double x1, double y1, double x2, double y2) {
    if (R->nseg == R->segcap) {
        int64_t nc = R->segcap ? R->segcap * 2 : 1024;
        k1_seg *q = (k1_seg *)realloc(R->seg, (size_t)nc * sizeof(k1_seg));
        if (!q) return -4;
        R->seg = q; R->segcap = nc;
    }
    k1_seg g = {x1, y1, x2, y2};
    R->seg[R->nseg++] = g;
    return 0;
}

static int cmp_sk(const void *a, const void *b) {
    const k1_sk *x = (const k1_sk *)a, *y = (const k1_sk *)b;
    return x->key < y->key ? -1 : x->key > y->key ? 1 : (x->seg > y->seg) - (x->seg < y->seg);
}

/* Bucket index of the road segments (64-raw buckets): a segment is listed in every bucket
 * within one raw unit of it (per x slab, the y extent of the segment inside the slab). */
static int seg_index(struct k1_region *R) {
    if (R->sk_built) return 0;
    R->sk_built = 1;
    int64_t cap = 0, n = 0;
    k1_sk *v = NULL;
    const double P = K1_SEG_BUCKET;
    for (int64_t s = 0; s < R->nseg; s++) {
        const k1_seg *g = &R->seg[s];
        if (!isfinite(g->x1 + g->y1 + g->x2 + g->y2)) continue;
        double sx0 = g->x1 < g->x2 ? g->x1 : g->x2, sx1 = g->x1 < g->x2 ? g->x2 : g->x1;
        double sy0 = g->y1 < g->y2 ? g->y1 : g->y2, sy1 = g->y1 < g->y2 ? g->y2 : g->y1;
        int64_t b0 = (int64_t)floor((sx0 - 1.0) / P), b1 = (int64_t)floor((sx1 + 1.0) / P);
        if (b1 - b0 > (1 << 20)) continue;
        for (int64_t bx = b0; bx <= b1; bx++) {
            double xa = sx0 > (double)bx * P - 1.0 ? sx0 : (double)bx * P - 1.0;
            double xb = sx1 < (double)(bx + 1) * P + 1.0 ? sx1 : (double)(bx + 1) * P + 1.0;
            double ya = sy0, yb = sy1;
            if (g->x1 != g->x2) {
                double k = (g->y2 - g->y1) / (g->x2 - g->x1);
                ya = g->y1 + (xa - g->x1) * k; yb = g->y1 + (xb - g->x1) * k;
                if (ya > yb) { double t = ya; ya = yb; yb = t; }
            }
            int64_t c0 = (int64_t)floor((ya - 1.0) / P), c1 = (int64_t)floor((yb + 1.0) / P);
            if (c1 - c0 > (1 << 20)) continue;
            for (int64_t by = c0; by <= c1; by++) {
                if (n == cap) {
                    cap = cap ? cap * 2 : 4096;
                    k1_sk *q = (k1_sk *)realloc(v, (size_t)cap * sizeof(k1_sk));
                    if (!q) { free(v); return -4; }
                    v = q;
                }
                v[n].key = pack(bx, by); v[n].seg = (int32_t)s; n++;
            }
        }
    }
    qsort(v, (size_t)n, sizeof(k1_sk), cmp_sk);
    R->sk = v; R->nsk = n;
    return 0;
}

/* road_distance(X, Y) <= TOL + EPS */
static int road_hit(struct k1_region *R, int64_t X, int64_t Y) {
    if (seg_index(R) < 0) return 0;
    int64_t key = pack(fldiv(X, K1_SEG_BUCKET), fldiv(Y, K1_SEG_BUCKET)), lo = 0, hi = R->nsk;
    while (lo < hi) { int64_t m = lo + (hi - lo) / 2; if (R->sk[m].key < key) lo = m + 1; else hi = m; }
    for (int64_t i = lo; i < R->nsk && R->sk[i].key == key; i++)
        if (cheb_seg((double)X, (double)Y, &R->seg[R->sk[i].seg]) <= K1_TOL + K1_EPS) return 1;
    return 0;
}

static void region_free(struct k1_region *R) {
    free(R->nodes.p); free(R->rpts.p); free(R->names.p); free(R->names_y.p);
    free(R->seg); free(R->sk);
    free(R->shp.mult); free(R->shp.type); free(R->shp.cls); free(R->shp.tall); free(R->shp.off);
    free(R->shp.hx); free(R->shp.hy); free(R->shp.rec);
    free(R->shp.x); free(R->shp.y); free(R->oix); free(R->oiy);
}

int64_t k1_region_cells(const struct k1_region *R, const int32_t **ix, const int32_t **iy) {
    *ix = R->oix; *iy = R->oiy;
    return R->nown;
}

/* ---- the band's background shapes */

static int shp_begin(k1_shapes *h, int32_t type, int32_t cls, int tall, int32_t hx, int32_t hy,
                     int32_t rec, int32_t mult) {
    if (h->n + 1 >= h->ncap || !h->off) {
        int64_t nc = h->ncap ? h->ncap * 2 : 64;
        int32_t *t = (int32_t *)realloc(h->type, (size_t)nc * 4);
        if (!t) return -4;
        h->type = t;
        int32_t *c = (int32_t *)realloc(h->cls, (size_t)nc * 4);
        if (!c) return -4;
        h->cls = c;
        int32_t *mu = (int32_t *)realloc(h->mult, (size_t)nc * 4);
        if (!mu) return -4;
        h->mult = mu;
        uint8_t *tl = (uint8_t *)realloc(h->tall, (size_t)nc);
        if (!tl) return -4;
        h->tall = tl;
        int32_t *ax = (int32_t *)realloc(h->hx, (size_t)nc * 4);
        if (!ax) return -4;
        h->hx = ax;
        int32_t *ay = (int32_t *)realloc(h->hy, (size_t)nc * 4);
        if (!ay) return -4;
        h->hy = ay;
        int32_t *ar = (int32_t *)realloc(h->rec, (size_t)nc * 4);
        if (!ar) return -4;
        h->rec = ar;
        int64_t *o = (int64_t *)realloc(h->off, (size_t)(nc + 1) * 8);
        if (!o) return -4;
        h->off = o;
        h->ncap = nc;
        if (h->n == 0) h->off[0] = 0;
    }
    h->type[h->n] = type; h->cls[h->n] = cls; h->tall[h->n] = (uint8_t)tall;
    h->hx[h->n] = hx; h->hy[h->n] = hy; h->rec[h->n] = rec; h->mult[h->n] = mult < 1 ? 1 : mult;
    h->n++;
    h->off[h->n] = h->off[h->n - 1];
    return 0;
}
static int shp_xy(k1_shapes *h, double x, double y) {
    if (h->ncoord == h->ccap) {
        int64_t nc = h->ccap ? h->ccap * 2 : 1024;
        double *a = (double *)realloc(h->x, (size_t)nc * 8);
        if (!a) return -4;
        h->x = a;
        double *b = (double *)realloc(h->y, (size_t)nc * 8);
        if (!b) return -4;
        h->y = b;
        h->ccap = nc;
    }
    h->x[h->ncoord] = x; h->y[h->ncoord] = y; h->ncoord++;
    h->off[h->n] = h->ncoord;
    return 0;
}

/* Region(...): the tall shapes meeting the block rectangle grown by SEARCH + 1 join the local
 * ones, and (only then) the local shapes that are tall themselves are dropped. */
static int shp_add_tall(k1_shapes *h, const k1_tallset *T, int64_t c0, int64_t c1, int64_t r0,
                        int64_t r1) {
    if (!T || T->n <= 0) return 0;
    double bx0 = (double)c0 * K1_RAW - K1_SEARCH - 1, bx1 = (double)(c1 + 1) * K1_RAW + K1_SEARCH + 1;
    double by0 = (double)r0 * K1_RAW - K1_SEARCH - 1, by1 = (double)(r1 + 1) * K1_RAW + K1_SEARCH + 1;
    int any = 0;
    for (int64_t t = 0; t < T->n && !any; t++) {
        const double *b = T->bb + 4 * t;
        any = b[1] >= bx0 && b[0] <= bx1 && b[3] >= by0 && b[2] <= by1;
    }
    if (!any) return 0;
    int64_t m = 0, mc = 0;
    for (int64_t s = 0; s < h->n; s++) {
        if (h->tall[s]) continue;
        int64_t a = h->off[s], n = h->off[s + 1] - a;
        h->mult[m] = h->mult[s]; h->type[m] = h->type[s]; h->cls[m] = h->cls[s]; h->tall[m] = 0;
        h->hx[m] = h->hx[s]; h->hy[m] = h->hy[s]; h->rec[m] = h->rec[s];
        if (mc != a) { memmove(h->x + mc, h->x + a, (size_t)n * 8); memmove(h->y + mc, h->y + a, (size_t)n * 8); }
        h->off[m] = mc;
        mc += n; m++;
    }
    h->n = m; h->ncoord = mc;
    if (h->off) h->off[m] = mc;
    for (int64_t t = 0; t < T->n; t++) {
        const double *b = T->bb + 4 * t;
        if (!(b[1] >= bx0 && b[0] <= bx1 && b[3] >= by0 && b[2] <= by1)) continue;
        int rc = shp_begin(h, T->rows[t].type, T->rows[t].cls, 1, T->rows[t].hx, T->rows[t].hy,
                           T->rows[t].rec, T->rows[t].mult);
        for (int64_t j = T->off[t]; rc == 0 && j < T->off[t + 1]; j++) rc = shp_xy(h, T->xy[2 * j], T->xy[2 * j + 1]);
        if (rc) return rc;
    }
    return 0;
}

/* the spool content of a block band: cells iy in [r0-1, r1+1], ix in [c0-1, c1+1] */
static int region_build(struct k1_region *R, const k1_spool *S, const k1_lat *L, int64_t c0,
                        int64_t c1, int64_t r0, int64_t r1) {
    memset(R, 0, sizeof *R);
    int rc = 0;
    int64_t a = lower_iy(S, r0 - 1), b = lower_iy(S, r1 + 2);
    for (int64_t i = a; i < b && rc == 0; i++) {
        int32_t ix = sp_ix(S, i);
        if (ix < c0 - 1 || ix > c1 + 1) continue;
        k1_cell C;
        if ((rc = parse_cell(S, i, &C)) < 0) break;
        R->ncells++;
        if (ix >= c0 && ix <= c1 && sp_iy(S, i) >= r0 && sp_iy(S, i) <= r1) {
            if (R->nown == R->ownmax) {
                int64_t nc = R->ownmax ? R->ownmax * 2 : 256;
                int32_t *a1 = (int32_t *)realloc(R->oix, (size_t)nc * 4);
                if (!a1) { rc = -4; break; }
                R->oix = a1;
                int32_t *a2 = (int32_t *)realloc(R->oiy, (size_t)nc * 4);
                if (!a2) { rc = -4; break; }
                R->oiy = a2; R->ownmax = nc;
            }
            R->oix[R->nown] = ix; R->oiy[R->nown] = sp_iy(S, i); R->nown++;
        }
        int64_t nr = C.n[0], nn = C.n[1], np = C.n[2], nm = C.n[5];
        for (int64_t j = 0; j < np && rc == 0; j++)
            rc = pts_push(&R->rpts, gx(L, rd_f64(C.c[K1_p_lon], j)), gy(L, rd_f64(C.c[K1_p_lat], j)));
        for (int64_t j = 0; j < nn && rc == 0; j++) {
            double x = gx(L, rd_f64(C.c[K1_n_lon], j)), y = gy(L, rd_f64(C.c[K1_n_lat], j));
            if ((rc = pts_push(&R->nodes, x, y)) == 0) rc = pts_push(&R->rpts, x, y);
        }
        for (int64_t j = 0; j < nm && rc == 0; j++)
            if ((C.c[K1_s_present][j] & 3) == 3)
                rc = pts_push(&R->names, gx(L, rd_f64(C.c[K1_s_lon], j)), gy(L, rd_f64(C.c[K1_s_lat], j)));
        /* background shapes (global raw floats); `tall` against the home cell */
        int64_t co = 0, nb = C.n[3];
        for (int64_t j = 0; j < nb && rc == 0; j++) {
            int64_t n = rd_i32(C.c[K1_b_nstored], j);
            if (n <= 0) continue;
            int64_t hx = ix, hy = sp_iy(S, i);
            double mnx = INFINITY, mxx = -INFINITY, mny = INFINITY, mxy = -INFINITY;
            for (int64_t v = 0; v < n; v++) {
                double x = gx(L, rd_f64(C.c[K1_c_lon], co + v)), y = gy(L, rd_f64(C.c[K1_c_lat], co + v));
                if (x < mnx) mnx = x;
                if (x > mxx) mxx = x;
                if (y < mny) mny = y;
                if (y > mxy) mxy = y;
            }
            int local = mnx >= (double)((hx - 1) * K1_RAW + 1) && mxx <= (double)((hx + 2) * K1_RAW - 1) &&
                        mny >= (double)((hy - 1) * K1_RAW + 1) && mxy <= (double)((hy + 2) * K1_RAW - 1);
            rc = shp_begin(&R->shp, rd_i32(C.c[K1_b_type], j), rd_i32(C.c[K1_b_class], j), !local,
                           hx, hy, (int32_t)j, rd_i32(C.c[K1_b_mult], j));
            for (int64_t v = 0; v < n && rc == 0; v++)
                rc = shp_xy(&R->shp, gx(L, rd_f64(C.c[K1_c_lon], co + v)), gy(L, rd_f64(C.c[K1_c_lat], co + v)));
            co += n;
        }
        /* road polylines: a road's points, else its stored nodes; no segment leaves a road's last point */
        int64_t po = 0, no = 0;
        for (int64_t r = 0; r < nr && rc == 0; r++) {
            int64_t npts = rd_i32(C.c[K1_r_npts], r), ns = rd_i32(C.c[K1_r_nstored], r);
            int use_p = npts > 0;
            int64_t n = use_p ? npts : ns, st = use_p ? po : no;
            const uint8_t *clat = use_p ? C.c[K1_p_lat] : C.c[K1_n_lat];
            const uint8_t *clon = use_p ? C.c[K1_p_lon] : C.c[K1_n_lon];
            for (int64_t j = 0; j + 1 < n && rc == 0; j++)
                rc = seg_push(R, gx(L, rd_f64(clon, st + j)), gy(L, rd_f64(clat, st + j)),
                              gx(L, rd_f64(clon, st + j + 1)), gy(L, rd_f64(clat, st + j + 1)));
            if (npts > 0) po += npts;
            if (ns > 0) no += ns;
        }
    }
    if (rc) return rc;
    /* name_xy: every name sorted by y (stable), before the key-range filter */
    R->names_y.p = (k1_pt *)malloc((size_t)(R->names.n + 1) * sizeof(k1_pt));
    if (!R->names_y.p) return -4;
    memcpy(R->names_y.p, R->names.p, (size_t)R->names.n * sizeof(k1_pt));
    R->names_y.n = R->names.n;
    for (int64_t i = 0; i < R->names_y.n; i++) R->names_y.p[i].key = i;   /* stable tie-break */
    qsort(R->names_y.p, (size_t)R->names_y.n, sizeof(k1_pt), cmp_y);
    pts_key(&R->nodes); pts_key(&R->rpts); pts_key(&R->names);
    return 0;
}

/* ------------------------------------------------------------------- items */

typedef struct { int64_t n, bad; double worst; } k1_agg;

typedef struct {
    k1_acc *acc;
    const k1_lat *lat;
    struct k1_region *R;
    const d1_walk *w;
    const k1_leaf *lf;
    int level;
    int64_t rescues;
    k1_agg range, step;
} k1_run;

double k1_gx(const k1_lat *L, double lon) { return gx(L, lon); }
double k1_gy(const k1_lat *L, double lat) { return gy(L, lat); }

void k1_frame_raw(const k1_leaf *lf, double lat, double lon, double *fx, double *fy) {
    double dl = np_mod(lon - lf->flo + 180.0, 360.0) - 180.0;
    *fx = dl / lf->fwo * lf->rng;
    *fy = (lat - lf->fla) / lf->fwa * lf->rng;
}

k1_sample k1_make_sample(const d1_walk *w, const k1_leaf *lf, double lat, double lon,
                             int32_t vx, int32_t vy, int reason, int code, double err) {
    k1_sample s;
    memset(&s, 0, sizeof s);
    s.lat = lat; s.lon = lon; s.err = err;
    s.ix = lf->ix; s.iy = lf->iy; s.vx = vx; s.vy = vy; s.reason = reason; s.code = code;
    s.p0 = w->p0; s.p1 = w->p1; s.p2 = w->p2; s.p3 = w->p3; s.p4 = w->p4; s.p5 = w->p5;
    s.p6 = w->p6; s.depth = w->depth;
    return s;
}

/* one decoded vertex through the range check (nodes, points, names, background vertices) */
static void range_item(k1_run *u, double lat, double lon) {
    double fx, fy;
    k1_frame_raw(u->lf, lat, lon, &fx, &fy);
    double rx = rnd(fx), ry = rnd(fy), rng = u->lf->rng;
    int nonint = fabs(fx - rx) > K1_INT_EPS || fabs(fy - ry) > K1_INT_EPS;
    int out = rx < 0 || ry < 0 || rx > rng || ry > rng || rng <= 0;
    u->range.n++;
    if (nonint || out) {
        u->range.bad++;
        k1_sample s = k1_make_sample(u->w, u->lf, lat, lon, sat32(rx), sat32(ry), K1_R_RANGE, 0, NAN);
        k1_push_sample(u->acc, K1_range, &s);
    }
}

/* kind: 0 road_node, 1 road_point, 2 name_anchor */
static void point_item(k1_run *u, int which, k1_agg *g, const k1_pts *set, double lat, double lon) {
    const k1_leaf *lf = u->lf;
    double x = gx(u->lat, lon), y = gy(u->lat, lat);
    int64_t X = to_i64(rnd(x)), Y = to_i64(rnd(y));
    double d = (X == INT64_MIN || Y == INT64_MIN) ? INFINITY : nearest(set, X, Y);
    int bad = !(d <= K1_TOL + K1_EPS);
    g->n++;
    if (bad && X != INT64_MIN && Y != INT64_MIN) {
        int sub = (lf->x1 - lf->x0) < K1_RAW || (lf->y1 - lf->y0) < K1_RAW;
        int ok = 0, name = -1;
        if (which < 2) {
            int edge = llabs(X - lf->x0) == 0 || llabs(X - lf->x1) == 0 ||
                       llabs(Y - lf->y0) == 0 || llabs(Y - lf->y1) == 0;
            if ((sub || edge) && road_hit(u->R, X, Y)) {
                ok = 1;
                name = which == 0 ? (sub ? K1_road_node_subcell_on_polyline : K1_road_node_on_leaf_edge)
                                  : (sub ? K1_road_point_subcell_on_polyline : K1_road_point_on_leaf_edge);
            }
        } else if (sub) {
            double ax0 = (double)lf->x0, ax1 = (double)lf->x1, ay0 = (double)lf->y0, ay1 = (double)lf->y1;
            double w = ax1 - ax0, h = ay1 - ay0;
            const k1_pts *ny = &u->R->names_y;
            int64_t lo = 0, hi = ny->n;
            while (lo < hi) { int64_t m = lo + (hi - lo) / 2; if (ny->p[m].y < ay0 - h) lo = m + 1; else hi = m; }
            for (int64_t i = lo; i < ny->n && ny->p[i].y <= ay1 + h && !ok; i++) {
                double cx = ny->p[i].x, cy = ny->p[i].y;
                if (!(cx >= ax0 - w && cx <= ax1 + w)) continue;
                if (cx >= ax0 && cx <= ax1 && cy >= ay0 && cy <= ay1) continue;
                double lx = ax0 + 0.01 * w, hx = ax1 - 0.01 * w, ly = ay0 + 0.01 * h, hy = ay1 - 0.01 * h;
                double px = cx < lx ? lx : cx, py = cy < ly ? ly : cy;
                px = px > hx ? hx : px; py = py > hy ? hy : py;
                if (fabs(px - (double)X) <= K1_TOL + K1_EPS && fabs(py - (double)Y) <= K1_TOL + K1_EPS) ok = 1;
            }
            if (ok) name = K1_name_anchor_halo;
        }
        if (ok) { u->acc->expl[name]++; u->rescues++; bad = 0; }
    }
    if (bad) {
        double fx, fy;
        g->bad++;
        k1_frame_raw(lf, lat, lon, &fx, &fy);
        k1_sample s = k1_make_sample(u->w, lf, lat, lon, sat32(rnd(fx)), sat32(rnd(fy)),
                                  K1_R_NO_SPOOL, 0, d);
        k1_push_sample(u->acc, K1_road_node + which, &s);
        if (which == 2 && u->acc->dump)
            k1_emit_dump(u->acc, K1_name_anchor, u->level, &s, -1, -1);
    } else if (d > g->worst) g->worst = d;     /* rescued items carry d = inf, as in the oracle */
}

/* ---------------------------------------------------------------- the band */

#define D1_NOUT (D1_T_WALK + 1)

static int d1_decode(const uint8_t *region, int64_t rl, const void *block, int64_t rlo, int64_t rhi,
                     void **buf, int64_t *caps, int64_t *dstats, int64_t *retries) {
    for (int t = 1; t < D1_NOUT; t++) caps[t] = (t == D1_T_NODE || t == D1_T_POINT || t == D1_T_BGCOORD) ? 1 << 16 : 1 << 12;
    caps[0] = 0;
    for (;;) {
        for (int t = 1; t < D1_NOUT; t++) {
            free(buf[t]);
            buf[t] = calloc((size_t)caps[t], (size_t)kw_d1_row_size(t));
            if (!buf[t]) return -4;
        }
        memset(dstats, 0, D1_NSTATS * sizeof(int64_t));
        int64_t rc = kw_d1_blocks(region, rl, block, 1, rlo, rhi, buf, caps, dstats);
        if (rc < 0) return -2;
        if (rc == 0) return 0;
        (*retries)++;
        for (int t = 1; t < D1_NOUT; t++) if (dstats[t] > caps[t]) caps[t] = dstats[t] + dstats[t] / 4;
    }
}

int64_t kw_k1_band(const uint8_t *region, int64_t region_len, const void *block,
                   int64_t rlo, int64_t rhi, const uint8_t *idx, int64_t idx_len,
                   const uint8_t *data, int64_t data_len, const int32_t *colmap,
                   const int32_t *esz, const int32_t *ckey, int64_t ncols,
                   void *kinds, void *samples, int64_t *expl, int64_t *stats,
                   const k1_tallrow *trows, const double *txy, const int64_t *toff,
                   const double *tbb, int64_t ntall,
                   k1_dump *dump_rows, int64_t dump_cap, int64_t *dump_need) {
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    if (!region || !block || !kinds || !samples || !expl || !stats) return -1;
    const d1_block *B = (const d1_block *)block;
    k1_dumpsink ds = {dump_rows, dump_cap, 0, 0};
    k1_acc acc = {(k1_kind *)kinds, (k1_sample *)samples, expl, stats,
                  dump_rows ? &ds : NULL};
    k1_spool S;
    int64_t rc = spool_open(&S, idx, idx_len, data, data_len, colmap, esz, ckey, ncols);
    if (rc < 0) return rc;

    void *buf[D1_NOUT] = {0};
    int64_t caps[D1_NOUT], dstats[D1_NSTATS], retries = 0;
    k1_leaf *leaf = NULL;
    struct k1_region R;
    k1_ctx *ctxp = NULL;
    memset(&R, 0, sizeof R);
    rc = d1_decode(region, region_len, B, rlo, rhi, buf, caps, dstats, &retries);
    if (rc < 0) goto done;
    {
        const d1_walk *walk = (const d1_walk *)buf[D1_T_WALK];
        const d1_frame *frame = (const d1_frame *)buf[D1_T_FRAME];
        const d1_link *link = (const d1_link *)buf[D1_T_LINK];
        const d1_node *node = (const d1_node *)buf[D1_T_NODE];
        const d1_point *point = (const d1_point *)buf[D1_T_POINT];
        const d1_bgshape *bgs = (const d1_bgshape *)buf[D1_T_BGSHAPE];
        const d1_bgcoord *bgc = (const d1_bgcoord *)buf[D1_T_BGCOORD];
        const d1_nrec *nrec = (const d1_nrec *)buf[D1_T_NREC];
        int64_t nw = dstats[D1_T_WALK];
        k1_lat lat = {B->lat0, B->lon0, B->cell_lat, B->cell_lon, B->wlo};

        /* the block's cell rectangle (key_cells), clipped to the band */
        bnds bb = block_bounds(B);
        int64_t c0 = (int64_t)rnd(dlon_of(&lat, bb.lon_lo) / lat.cell_lon);
        int64_t r0 = (int64_t)rnd((bb.lat_lo - lat.lat0) / lat.cell_lat);
        int64_t c1 = c0 + (int64_t)rnd(lon_span(bb.lon_lo, bb.lon_hi) / lat.cell_lon) - 1;
        int64_t r1 = r0 + (int64_t)rnd((bb.lat_hi - bb.lat_lo) / lat.cell_lat) - 1;
        if (r0 < rlo) r0 = rlo;
        if (r1 > rhi) r1 = rhi;
        if ((rc = region_build(&R, &S, &lat, c0, c1, r0, r1)) < 0) goto done;
        {
            k1_tallset T = {trows, txy, toff, tbb, ntall};
            if ((rc = shp_add_tall(&R.shp, ntall > 0 && trows && txy && toff && tbb ? &T : NULL,
                                   c0, c1, r0, r1)) < 0) goto done;
        }

        leaf = (k1_leaf *)calloc((size_t)(nw > 0 ? nw : 1), sizeof(k1_leaf));
        if (!leaf) { rc = -4; goto done; }
        k1_run u;
        memset(&u, 0, sizeof u);
        u.acc = &acc; u.lat = &lat; u.R = &R; u.level = B->level;
        k1_agg ag[3] = {{0}};
        int64_t items = 0;
        for (int64_t i = 0; i < nw; i++) {
            const d1_walk *w = &walk[i];
            k1_leaf *lf = &leaf[i];
            double bx0 = gx(&lat, w->lon_lo), by0 = gy(&lat, w->lat_lo);
            double bw = lon_span(w->lon_lo, w->lon_hi) / lat.cell_lon * (double)K1_RAW;
            double bh = (w->lat_hi - w->lat_lo) / lat.cell_lat * (double)K1_RAW;
            lf->x0 = to_i64(rnd(bx0)); lf->y0 = to_i64(rnd(by0));
            lf->x1 = to_i64(rnd(bx0 + bw)); lf->y1 = to_i64(rnd(by0 + bh));
            lf->ix = (int32_t)fldiv(fldiv(lf->x0 + lf->x1, 2), K1_RAW);
            lf->iy = (int32_t)fldiv(fldiv(lf->y0 + lf->y1, 2), K1_RAW);
            lf->flo = w->flon_lo; lf->fla = w->flat_lo;
            lf->fwo = lon_span(w->flon_lo, w->flon_hi); lf->fwa = w->flat_hi - w->flat_lo;
            lf->rng = (double)w->frame_range;
            const d1_frame *f = w->frame >= 0 ? &frame[w->frame] : NULL;
            lf->ok = w->status == 0 && f && f->status == 0;
            if (!lf->ok) {
                acc.kind[K1_range].failing++;
                int code = f ? f->status : 100 + w->err;
                if (w->status == 1) code = 100 + w->err;
                k1_sample s = k1_make_sample(w, lf, 0.0, 0.0, INT32_MIN, INT32_MIN, K1_R_NO_DECODE, code, NAN);
                k1_push_sample(&acc, K1_range, &s);
                continue;
            }
            u.w = w; u.lf = lf;
            /* D1 sets a section's `_first` only when the section exists, so a frame without it
             * has `_n` = the running total: guard each loop on has_road / has_name / has_bg */
            for (uint32_t li = 0; f->has_road && li < f->link_n; li++) {
                const d1_link *lk = &link[f->link_first + li];
                uint32_t j = 0;
                for (uint32_t k = 0; k < lk->n_points; k++) {
                    const d1_point *q = &point[lk->point_first + k];
                    if (j < lk->n_nodes && q->lat == node[lk->node_first + j].lat &&
                        q->lon == node[lk->node_first + j].lon) { j++; continue; }
                    range_item(&u, q->lat, q->lon);
                    point_item(&u, 1, &ag[1], &R.rpts, q->lat, q->lon);
                }
                for (uint32_t k = 0; k < lk->n_nodes; k++) {
                    const d1_node *nd = &node[lk->node_first + k];
                    range_item(&u, nd->lat, nd->lon);
                    point_item(&u, 0, &ag[0], &R.nodes, nd->lat, nd->lon);
                }
            }
            for (uint32_t k = 0; f->has_name && k < f->nrec_n; k++) {
                const d1_nrec *nr = &nrec[f->nrec_first + k];
                if (!nr->has_latlon) continue;
                range_item(&u, nr->lat, nr->lon);
                point_item(&u, 2, &ag[2], &R.names, nr->lat, nr->lon);
            }
            for (uint32_t k = 0; f->has_bg && k < f->bgshape_n; k++) {
                const d1_bgshape *sh = &bgs[f->bgshape_first + k];
                if (sh->coord_n == 0) continue;
                int64_t m = sh->mult_const ? sh->mult_const : 1, px = 0, py = 0;
                for (uint32_t v = 0; v < sh->coord_n; v++) {
                    const d1_bgcoord *c = &bgc[sh->coord_first + v];
                    range_item(&u, c->lat, c->lon);
                    double fx, fy;
                    k1_frame_raw(lf, c->lat, c->lon, &fx, &fy);
                    int64_t rfx = to_i64(rnd(fx)), rfy = to_i64(rnd(fy));
                    if (v > 0) {
                        int64_t dx = (int64_t)((uint64_t)rfx - (uint64_t)px), dy = (int64_t)((uint64_t)rfy - (uint64_t)py);
                        u.step.n++;
                        if (dx % m != 0 || dy % m != 0 || dx > 127 * m || dx < -127 * m ||
                            dy > 127 * m || dy < -127 * m || dx == INT64_MIN || dy == INT64_MIN) {
                            u.step.bad++;
                            k1_sample s = k1_make_sample(w, lf, c->lat, c->lon, sat32((double)rfx), sat32((double)rfy),
                                                      K1_R_STEP, 0, NAN);
                            k1_push_sample(&acc, K1_step, &s);
                        }
                    }
                    px = rfx; py = rfy;
                }
            }
        }
        items = u.range.n;
        k1_add(&acc, K1_range, u.range.n, u.range.bad, 0.0);
        k1_add(&acc, K1_step, u.step.n, u.step.bad, 0.0);
        for (int k = 0; k < 3; k++) if (ag[k].n) k1_add(&acc, K1_road_node + k, ag[k].n, ag[k].bad, ag[k].worst);
        /* the failed-leaf count was added to `failing` above without a checked count */
        k1_ctx ctx = {B, lat, nw, walk, leaf, frame, bgs, bgc, &R, &acc, &R.shp, c0, c1, r0, r1, NULL};
        ctxp = &ctx;
        if ((rc = k1_bg_kinds(&ctx)) < 0) goto done;
        if ((rc = k1_cmp_kinds(&ctx)) < 0) goto done;
        stats[K1_leaves] += nw;
        stats[K1_failed_frames] += dstats[D1_S_FAILED];
        stats[K1_cells] += R.ncells;
        stats[K1_items] += items;
        stats[K1_rescues] += u.rescues;
        stats[K1_d1_ns] += dstats[D1_S_NS];
        rc = 0;
    }
done:
    if (dump_need) *dump_need = ds.n;
    if (rc == 0 && acc.dump && acc.dump->overflow) rc = 1;
    if (ctxp) k1_bg_release(ctxp);
    stats[K1_calls]++;
    stats[K1_d1_retries] += retries;
    for (int t = 1; t < D1_NOUT; t++) free(buf[t]);
    free(leaf);
    region_free(&R);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    stats[K1_ns] += (int64_t)(t1.tv_sec - t0.tv_sec) * 1000000000LL + (t1.tv_nsec - t0.tv_nsec);
    return rc;
}

/* ---------------------------------------------------------------- tall pass */

int64_t kw_k1_tall(const uint8_t *idx, int64_t idx_len, const uint8_t *data, int64_t data_len,
                   const int32_t *colmap, const int32_t *esz, const int32_t *ckey, int64_t ncols,
                   const double *lat5, int64_t a, int64_t b, k1_tallrow *rows, int64_t rows_cap,
                   double *xy, int64_t xy_cap, int64_t *need) {
    k1_spool S;
    int64_t rc = spool_open(&S, idx, idx_len, data, data_len, colmap, esz, ckey, ncols);
    if (rc < 0) return rc;
    if (a < 0 || b > S.n || a > b) return -1;
    k1_lat L = {lat5[0], lat5[1], lat5[2], lat5[3], lat5[4]};
    int64_t nrow = 0, nxy = 0;
    for (int64_t i = a; i < b; i++) {
        k1_cell C;
        if ((rc = parse_cell(&S, i, &C)) < 0) return rc;
        int64_t hx = sp_ix(&S, i), hy = sp_iy(&S, i), co = 0;
        for (int64_t s = 0; s < C.n[3]; s++) {
            int64_t n = rd_i32(C.c[K1_b_nstored], s);
            if (n > 0) {
                double mnx = INFINITY, mxx = -INFINITY, mny = INFINITY, mxy = -INFINITY;
                for (int64_t j = 0; j < n; j++) {
                    double x = gx(&L, rd_f64(C.c[K1_c_lon], co + j)), y = gy(&L, rd_f64(C.c[K1_c_lat], co + j));
                    if (x < mnx) mnx = x;
                    if (x > mxx) mxx = x;
                    if (y < mny) mny = y;
                    if (y > mxy) mxy = y;
                }
                int local = mnx >= (double)((hx - 1) * K1_RAW + 1) && mxx <= (double)((hx + 2) * K1_RAW - 1) &&
                            mny >= (double)((hy - 1) * K1_RAW + 1) && mxy <= (double)((hy + 2) * K1_RAW - 1);
                if (!local) {
                    if (nrow < rows_cap && nxy + n <= xy_cap) {
                        for (int64_t j = 0; j < n; j++) {
                            xy[2 * (nxy + j)] = gx(&L, rd_f64(C.c[K1_c_lon], co + j));
                            xy[2 * (nxy + j) + 1] = gy(&L, rd_f64(C.c[K1_c_lat], co + j));
                        }
                        k1_tallrow t = {rd_i32(C.c[K1_b_type], s),
                                        rd_i32(C.c[K1_b_class], s), (int32_t)n, (int32_t)hx,
                                        (int32_t)hy, (int32_t)s, rd_i32(C.c[K1_b_mult], s)};
                        rows[nrow] = t;
                    }
                    nrow++; nxy += n;
                }
            }
            co += n > 0 ? n : 0;
        }
    }
    need[0] = nrow; need[1] = nxy;
    return (nrow > rows_cap || nxy > xy_cap) ? 1 : 0;
}
