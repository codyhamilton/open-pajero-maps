/* E1 -- the C level pre-pass (plan 03, 3C-06; DESIGN.md Contract B, "E1").
 *
 * One call per row range [row_lo, row_hi) of one level. Input: the level
 * descriptor (built once per level by `kiwiw/descriptor.py`), the level's
 * spool `.idx` and `.data` bytes (zero-copy; Python passes mmap'd buffers).
 * Output: 32-byte routing rows plus additive counters. It replaces
 * `overlap.py`'s scan; it is not wired into the build by this unit.
 *
 * ---------------------------------------------------------------- layouts
 * Level descriptor (little-endian; `descriptor.py` is its writer and mirrors
 * this table in its docstring):
 *     0  u8[8] magic "KWLDESC1"        8  u32 version (1)
 *    12  u32 header_bytes (168)       16  u64 total_bytes
 *    24  i32 level  28 i32 nx  32 i32 ny  36 i32 frame_class (0 urban, 1 full)
 *    40  f64 disc_lat_lo  48 f64 disc_lon_lo  56 f64 cell_lat  64 f64 cell_lon
 *    72  i32 range[4]   (parcel_type 0 undivided, 1..3 pardiv<t>; -1 = none)
 *    88  i32 window[4]  (ix_lo, ix_hi, iy_lo, iy_hi) inclusive receiver window
 *   104  i32 max_frame  108 i32 threshold
 *   112  i64 kind_limits[3] (road, bg, name; 1<<62 = no limit)
 *   136  u64 mask_off   144 u64 mask_len
 *   152  u32 cols_off   156 u32 n_cols  160 u32 n_count_keys
 *   164  u8 role[4]     column index of b_class, b_nstored, c_lat, c_lon
 *   cols_off: n_cols x (u8 elem_size, u8 count_key_index), padded to 8
 *   mask_off: existence bitmap, bit (iy*nx + ix), LSB-first within a byte;
 *             a cell exists iff it is a spool cell or inside the mask rect.
 * E1 reads only what it needs (grid, window, columns, mask); the rest is
 * carried for E2 (3C-07).
 *
 * Spool record (`spool.py`): 9 x u64 counts, then every column of the cols
 * table in order, each count[key] * elem_size bytes, zero-padded to 8. Here
 * the column table comes from the descriptor, not a C copy of `_COLUMNS`.
 * Spool index: "KWSPIDX1", u64 n, 4 x u64 totals, ix i32[n], iy i32[n],
 * offset u64[n], length u64[n]; cells ascending (iy, ix).
 *
 * E1 row (32 bytes, little-endian, packed; numpy `descriptor.E1_ROW_DTYPE`):
 *     0 i32 tix   4 i32 tiy   8 i32 six   12 i32 siy
 *    16 u64 cell_off  (source cell's .data offset = its idx offset)
 *    24 u32 shape     (index among the source cell's background shapes)
 *    28 u8  kind      (0 edge: receives the ring; 1 interior: cover ring)
 *    29 u8  pad[3]    (zero)
 * Order: source cell (idx order), shape, target key (iy, ix).
 *
 * Counters (int64[8], additive over ranges): 0 shared_shapes (shapes with
 * >= 1 row), 1 edge_cells (kind-0 rows), 2 interior_cells (kind-1 rows),
 * 3 skipped_missing_cells (in-grid, in-window, non-own receivers that do
 * not exist), 4 cells scanned, 5 shapes scanned, 6 shapes that leave their
 * cell, 7 C nanoseconds.
 *
 * Geometry (the scan `overlap.py` defined, in cell units gx = (lon -
 * disc_lon_lo)/cell_lon, gy = (lat - disc_lat_lo)/cell_lat, EPS = 1e-6):
 * edge cells are those each segment's EPS-grown footprint touches; for a
 * closed shape (b_class == 2) interior cells are the even-odd scanline cover
 * at row centres minus the edge cells. The own cell is removed, then the
 * window is applied, then existence (non-existing = skipped). Built with
 * -ffp-contract=off so every expression rounds as written.
 *
 * Return: rows needed (>= 0; rows beyond rows_cap are counted, not
 * written -- the caller grows its buffer and calls again), or < 0:
 * -1 bad descriptor, -2 bad index, -3 bad record, -4 out of memory. */
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define E1_EPS 1e-6
#define E1_HDR 168
#define E1_ROW 32
#define E1_MAXCOLS 64

typedef struct { uint64_t *v; int64_t n, cap; } e1_keys;
typedef struct { int64_t r; double x; } e1_rx;
typedef struct {
    e1_keys edge, cover;
    e1_rx *rx; int64_t nrx, caprx;
    double *gx, *gy; int64_t capg;
} e1_scratch;

typedef struct {
    int32_t nx, ny;
    double lat_lo, lon_lo, cell_lat, cell_lon;
    int32_t win[4];
    const uint8_t *mask;
    uint32_t n_cols, n_keys;
    uint8_t csize[E1_MAXCOLS], ckey[E1_MAXCOLS], role[4];
} e1_desc;

static inline uint32_t e1_u32(const uint8_t *p) { uint32_t v; memcpy(&v, p, 4); return v; }
static inline int32_t e1_i32(const uint8_t *p) { int32_t v; memcpy(&v, p, 4); return v; }
static inline uint64_t e1_u64(const uint8_t *p) { uint64_t v; memcpy(&v, p, 8); return v; }
static inline double e1_f64(const uint8_t *p) { double v; memcpy(&v, p, 8); return v; }

static int e1_push(e1_keys *k, uint64_t key) {
    if (k->n == k->cap) {
        int64_t nc = k->cap ? k->cap * 2 : 256;
        uint64_t *nv = realloc(k->v, (size_t)nc * sizeof *nv);
        if (!nv) return -1;
        k->v = nv; k->cap = nc;
    }
    k->v[k->n++] = key;
    return 0;
}

static int e1_push_rx(e1_scratch *s, int64_t r, double x) {
    if (s->nrx == s->caprx) {
        int64_t nc = s->caprx ? s->caprx * 2 : 256;
        e1_rx *nv = realloc(s->rx, (size_t)nc * sizeof *nv);
        if (!nv) return -1;
        s->rx = nv; s->caprx = nc;
    }
    s->rx[s->nrx].r = r; s->rx[s->nrx].x = x; s->nrx++;
    return 0;
}

static int e1_cmp_u64(const void *a, const void *b) {
    uint64_t x = *(const uint64_t *)a, y = *(const uint64_t *)b;
    return (x > y) - (x < y);
}

static int e1_cmp_rx(const void *a, const void *b) {
    const e1_rx *p = a, *q = b;
    if (p->r != q->r) return (p->r > q->r) - (p->r < q->r);
    return (p->x > q->x) - (p->x < q->x);
}

static void e1_sort_unique(e1_keys *k) {
    if (k->n < 2) return;
    qsort(k->v, (size_t)k->n, sizeof *k->v, e1_cmp_u64);
    int64_t w = 1;
    for (int64_t i = 1; i < k->n; i++)
        if (k->v[i] != k->v[w - 1]) k->v[w++] = k->v[i];
    k->n = w;
}

/* floor/ceil to int64, clamped far outside any grid (values that far out
 * only ever fall off the grid, so the clamp changes no result). */
static inline int64_t e1_fl(double v) {
    v = floor(v);
    return v < -1e9 ? -1000000000LL : v > 1e9 ? 1000000000LL : (int64_t)v;
}
static inline int64_t e1_ce(double v) {
    v = ceil(v);
    return v < -1e9 ? -1000000000LL : v > 1e9 ? 1000000000LL : (int64_t)v;
}

static inline uint64_t e1_key(int64_t ix, int64_t iy) {
    return ((uint64_t)iy << 32) | (uint64_t)ix;
}

/* Edge and interior cell keys of one shape of n points (gx, gy in cell
 * units; the arrays must have room for n + 1 points), clipped to the
 * nx x ny grid. On return s->edge and s->cover are sorted, unique and
 * disjoint. Returns 0, or -4 on allocation failure. */
static int e1_shape_cells(e1_scratch *s, double *gx, double *gy, int64_t n, int closed,
                          int64_t nx, int64_t ny) {
    s->edge.n = 0; s->cover.n = 0; s->nrx = 0;
    if (n <= 0) return 0;
    if (closed && n > 1 && (gx[0] != gx[n - 1] || gy[0] != gy[n - 1])) {
        gx[n] = gx[0]; gy[n] = gy[0]; n++;
    }
    if (n == 1) { gx[1] = gx[0]; gy[1] = gy[0]; n = 2; }
    for (int64_t i = 0; i + 1 < n; i++) {
        double ax = gx[i], ay = gy[i], bx = gx[i + 1], by = gy[i + 1];
        double xmin = ax < bx ? ax : bx, xmax = ax < bx ? bx : ax;
        double ymin = ay < by ? ay : by, ymax = ay < by ? by : ay;
        int64_t xlo = e1_fl(xmin - E1_EPS), xhi = e1_fl(xmax + E1_EPS);
        int64_t ylo = e1_fl(ymin - E1_EPS), yhi = e1_fl(ymax + E1_EPS);
        if (xhi - xlo <= 1 && yhi - ylo <= 1) {
            for (int64_t x = xlo; x <= xhi; x++)
                for (int64_t y = ylo; y <= yhi; y++)
                    if (x >= 0 && x < nx && y >= 0 && y < ny &&
                        e1_push(&s->edge, e1_key(x, y))) return -4;
            continue;
        }
        int64_t c0 = xlo < 0 ? 0 : xlo, c1 = xhi > nx - 1 ? nx - 1 : xhi;
        for (int64_t c = c0; c <= c1; c++) {
            int64_t r0, r1;
            if (bx == ax) {
                r0 = ylo; r1 = yhi;
            } else {
                double xa = (double)c - E1_EPS, xb = (double)(c + 1) + E1_EPS;
                if (xa < xmin) xa = xmin;
                if (xb > xmax) xb = xmax;
                double t = (by - ay) / (bx - ax);
                double ya = ay + (xa - ax) * t;
                double yb = ay + (xb - ax) * t;
                r0 = e1_fl((ya < yb ? ya : yb) - E1_EPS);
                r1 = e1_fl((ya < yb ? yb : ya) + E1_EPS);
            }
            if (r0 < 0) r0 = 0;
            if (r1 > ny - 1) r1 = ny - 1;
            for (int64_t r = r0; r <= r1; r++)
                if (e1_push(&s->edge, e1_key(c, r))) return -4;
        }
    }
    e1_sort_unique(&s->edge);
    if (!closed) return 0;
    /* interior: even-odd scanline at each row centre */
    for (int64_t i = 0; i + 1 < n; i++) {
        double ax = gx[i], ay = gy[i], bx = gx[i + 1], by = gy[i + 1];
        if (ay == by) continue;
        int64_t rlo = e1_ce((ay < by ? ay : by) - 0.5);
        int64_t rhi = e1_ce((ay < by ? by : ay) - 0.5) - 1;
        if (rlo < 0) rlo = 0;
        if (rhi > ny - 1) rhi = ny - 1;
        for (int64_t r = rlo; r <= rhi; r++) {
            double yc = (double)r + 0.5;
            double x = ax + (yc - ay) / (by - ay) * (bx - ax);
            if (e1_push_rx(s, r, x)) return -4;
        }
    }
    if (s->nrx < 2) return 0;
    qsort(s->rx, (size_t)s->nrx, sizeof *s->rx, e1_cmp_rx);
    for (int64_t i = 0; i + 1 < s->nrx; i += 2) {
        int64_t r = s->rx[i].r;
        int64_t c0 = e1_ce(s->rx[i].x - 0.5), c1 = e1_fl(s->rx[i + 1].x - 0.5);
        if (c0 < 0) c0 = 0;
        if (c1 > nx - 1) c1 = nx - 1;
        for (int64_t c = c0; c <= c1; c++)
            if (e1_push(&s->cover, e1_key(c, r))) return -4;
    }
    e1_sort_unique(&s->cover);
    int64_t w = 0, j = 0;
    for (int64_t i = 0; i < s->cover.n; i++) {
        uint64_t k = s->cover.v[i];
        while (j < s->edge.n && s->edge.v[j] < k) j++;
        if (j < s->edge.n && s->edge.v[j] == k) continue;
        s->cover.v[w++] = k;
    }
    s->cover.n = w;
    return 0;
}

static int e1_parse_desc(const uint8_t *d, int64_t len, e1_desc *o) {
    if (len < E1_HDR || memcmp(d, "KWLDESC1", 8) != 0) return -1;
    if (e1_u32(d + 8) != 1 || e1_u32(d + 12) != E1_HDR) return -1;
    if ((int64_t)e1_u64(d + 16) != len) return -1;
    o->nx = e1_i32(d + 28); o->ny = e1_i32(d + 32);
    if (o->nx <= 0 || o->ny <= 0 || o->nx > (1 << 16) || o->ny > (1 << 16)) return -1;
    o->lat_lo = e1_f64(d + 40); o->lon_lo = e1_f64(d + 48);
    o->cell_lat = e1_f64(d + 56); o->cell_lon = e1_f64(d + 64);
    if (!(o->cell_lat > 0) || !(o->cell_lon > 0)) return -1;
    for (int i = 0; i < 4; i++) o->win[i] = e1_i32(d + 88 + 4 * i);
    uint64_t moff = e1_u64(d + 136), mlen = e1_u64(d + 144);
    uint64_t need = ((uint64_t)o->nx * (uint64_t)o->ny + 7) / 8;
    if (mlen < need || moff > (uint64_t)len || mlen > (uint64_t)len - moff) return -1;
    o->mask = d + moff;
    uint32_t coff = e1_u32(d + 152);
    o->n_cols = e1_u32(d + 156); o->n_keys = e1_u32(d + 160);
    if (o->n_keys != 9 || o->n_cols == 0 || o->n_cols > E1_MAXCOLS) return -1;
    if ((uint64_t)coff + 2ull * o->n_cols > (uint64_t)len) return -1;
    for (uint32_t c = 0; c < o->n_cols; c++) {
        o->csize[c] = d[coff + 2 * c]; o->ckey[c] = d[coff + 2 * c + 1];
        if (o->ckey[c] >= o->n_keys || o->csize[c] == 0 || o->csize[c] > 8) return -1;
    }
    static const uint8_t want[4] = {4, 4, 8, 8};
    for (int i = 0; i < 4; i++) {
        o->role[i] = d[164 + i];
        if (o->role[i] >= o->n_cols || o->csize[o->role[i]] != want[i]) return -1;
    }
    return 0;
}

static inline int e1_exists(const e1_desc *D, uint64_t key) {
    uint64_t ix = key & 0xFFFFFFFFu, iy = key >> 32;
    uint64_t bit = iy * (uint64_t)D->nx + ix;
    return (D->mask[bit >> 3] >> (bit & 7)) & 1;
}

int64_t kw_e1(const uint8_t *desc, int64_t desc_len, const uint8_t *idx, int64_t idx_len,
              const uint8_t *data, int64_t data_len, int64_t row_lo, int64_t row_hi,
              uint8_t *rows, int64_t rows_cap, int64_t *counters) {
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    int64_t ret = 0;
    e1_desc D;
    if (e1_parse_desc(desc, desc_len, &D)) return -1;
    if (idx_len < 48 || memcmp(idx, "KWSPIDX1", 8) != 0) return -2;
    uint64_t ncell = e1_u64(idx + 8);
    if (ncell > (uint64_t)(idx_len - 48) / 24 || 48 + 24 * ncell != (uint64_t)idx_len) return -2;
    const uint8_t *aix = idx + 48, *aiy = aix + 4 * ncell;
    const uint8_t *aoff = aiy + 4 * ncell, *alen = aoff + 8 * ncell;
    /* [a, b): first cells with iy >= row_lo / iy >= row_hi */
    int64_t a = 0, b = (int64_t)ncell;
    for (int64_t lo = 0, hi = (int64_t)ncell; lo < hi;) {
        int64_t m = (lo + hi) / 2;
        if (e1_i32(aiy + 4 * m) < row_lo) lo = m + 1; else hi = m;
        a = hi;
    }
    for (int64_t lo = a, hi = (int64_t)ncell; lo < hi;) {
        int64_t m = (lo + hi) / 2;
        if (e1_i32(aiy + 4 * m) < row_hi) lo = m + 1; else hi = m;
        b = hi;
    }
    if (a > b) b = a;
    e1_scratch S;
    memset(&S, 0, sizeof S);
    int64_t cnt[7] = {0};
    int64_t nrow = 0;
    const int64_t nx = D.nx, ny = D.ny;
    for (int64_t i = a; i < b; i++) {
        int64_t ix = e1_i32(aix + 4 * i), iy = e1_i32(aiy + 4 * i);
        uint64_t off = e1_u64(aoff + 8 * i), len = e1_u64(alen + 8 * i);
        if (off > (uint64_t)data_len || len > (uint64_t)data_len - off || len < 72) {
            ret = -3; goto done;
        }
        const uint8_t *rec = data + off;
        uint64_t counts[9];
        for (int k = 0; k < 9; k++) {
            counts[k] = e1_u64(rec + 8 * k);
            if (counts[k] > (1ull << 28)) { ret = -3; goto done; }
        }
        const uint8_t *colp[4] = {0};
        uint64_t pos = 72;
        for (uint32_t c = 0; c < D.n_cols; c++) {
            uint64_t nb = counts[D.ckey[c]] * D.csize[c];
            for (int r = 0; r < 4; r++) if (D.role[r] == c) colp[r] = rec + pos;
            pos += (nb + 7) & ~7ull;
            if (pos > len) { ret = -3; goto done; }
        }
        if (pos != len) { ret = -3; goto done; }
        cnt[4]++;
        int64_t nbg = (int64_t)counts[D.ckey[D.role[1]]];
        int64_t ncoord = (int64_t)counts[D.ckey[D.role[2]]];
        if ((int64_t)counts[D.ckey[D.role[0]]] != nbg ||
            (int64_t)counts[D.ckey[D.role[3]]] != ncoord) { ret = -3; goto done; }
        uint64_t own = e1_key(ix, iy);
        int64_t start = 0;
        for (int64_t k = 0; k < nbg; k++) {
            int64_t n = e1_i32(colp[1] + 4 * k);
            if (n < 0 || start + n > ncoord) { ret = -3; goto done; }
            int64_t s0 = start;
            start += n;
            cnt[5]++;
            if (n == 0) continue;
            if (n + 2 > S.capg) {
                int64_t nc = n + 2 > 1024 ? n + 2 : 1024;
                double *ngx = realloc(S.gx, (size_t)nc * sizeof(double));
                if (!ngx) { ret = -4; goto done; }
                S.gx = ngx;
                double *ngy = realloc(S.gy, (size_t)nc * sizeof(double));
                if (!ngy) { ret = -4; goto done; }
                S.gy = ngy; S.capg = nc;
            }
            double x0 = INFINITY, x1 = -INFINITY, y0 = INFINITY, y1 = -INFINITY;
            for (int64_t p = 0; p < n; p++) {
                double lat = e1_f64(colp[2] + 8 * (s0 + p));
                double lon = e1_f64(colp[3] + 8 * (s0 + p));
                double gx = (lon - D.lon_lo) / D.cell_lon;
                double gy = (lat - D.lat_lo) / D.cell_lat;
                S.gx[p] = gx; S.gy[p] = gy;
                if (gx < x0) x0 = gx;
                if (gx > x1) x1 = gx;
                if (gy < y0) y0 = gy;
                if (gy > y1) y1 = gy;
            }
            int64_t fx0 = e1_fl(x0 - E1_EPS), fx1 = e1_fl(x1 + E1_EPS);
            int64_t fy0 = e1_fl(y0 - E1_EPS), fy1 = e1_fl(y1 + E1_EPS);
            /* a shape whose grown bbox stays in its own cell reaches no other
             * cell; one whose bbox misses the window reaches none in it */
            if (fx0 >= ix && fx1 <= ix && fy0 >= iy && fy1 <= iy) continue;
            if (fx1 < D.win[0] || fx0 > D.win[1] || fy1 < D.win[2] || fy0 > D.win[3]) continue;
            cnt[6]++;
            int closed = e1_i32(colp[0] + 4 * k) == 2;
            int rc = e1_shape_cells(&S, S.gx, S.gy, n, closed, nx, ny);
            if (rc) { ret = rc; goto done; }
            int64_t ie = 0, ic = 0, emitted = 0;
            while (ie < S.edge.n || ic < S.cover.n) {
                int kind;
                uint64_t key;
                if (ic >= S.cover.n || (ie < S.edge.n && S.edge.v[ie] < S.cover.v[ic])) {
                    key = S.edge.v[ie++]; kind = 0;
                } else {
                    key = S.cover.v[ic++]; kind = 1;
                }
                if (key == own) continue;
                int64_t tx = (int64_t)(key & 0xFFFFFFFFu), ty = (int64_t)(key >> 32);
                if (tx < D.win[0] || tx > D.win[1] || ty < D.win[2] || ty > D.win[3]) continue;
                if (!e1_exists(&D, key)) { cnt[3]++; continue; }
                cnt[1 + kind]++;
                emitted++;
                if (nrow < rows_cap) {
                    uint8_t *o = rows + E1_ROW * nrow;
                    int32_t v[4] = {(int32_t)tx, (int32_t)ty, (int32_t)ix, (int32_t)iy};
                    uint32_t sh = (uint32_t)k;
                    memcpy(o, v, 16);
                    memcpy(o + 16, &off, 8);
                    memcpy(o + 24, &sh, 4);
                    o[28] = (uint8_t)kind; o[29] = o[30] = o[31] = 0;
                }
                nrow++;
            }
            if (emitted) cnt[0]++;
        }
    }
    ret = nrow;
done:
    free(S.edge.v); free(S.cover.v); free(S.rx); free(S.gx); free(S.gy);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    if (ret >= 0) {
        for (int i = 0; i < 7; i++) counters[i] += cnt[i];
    }
    counters[7] += (int64_t)(t1.tv_sec - t0.tv_sec) * 1000000000LL + (t1.tv_nsec - t0.tv_nsec);
    return ret;
}
