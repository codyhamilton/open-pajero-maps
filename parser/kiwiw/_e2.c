/* E2 -- the Stage 1 kernel (plan 03, 3C-07; DESIGN.md Contract B, "E2").
 *
 * One call per target row range [row_lo, row_hi) of one level. For every
 * receiving cell of the range (canonical (iy, ix) order) it merges the
 * cell's own spool record with the borrowed background shapes E1 routed
 * to it (read in place from the spool), adds interior-cover rings, and
 * encodes the cell with `_cenc.c`'s per-cell encoder. A cell that fits is
 * written to `out_fd` and indexed; a cell that does not is declined
 * (reason 1: needs division) with its merged content, for Stage 2. Not
 * wired into the build by this unit.
 *
 * Inputs: the level descriptor (layout: `_e1.c` / `descriptor.py`), the
 * level's spool `.idx` / `.data` bytes (zero-copy), and the routed E1 rows
 * (`descriptor.E1_ROW_DTYPE`) whose targets lie in this range, ordered by
 * target (iy, ix), then source (iy, ix), then shape -- E1 emits source then
 * shape order, so one stable sort on the target key routes them.
 *
 * Receiving cells: every cell of the descriptor window, rows clipped to
 * [row_lo, row_hi), whose existence bit is set (a spool cell, or a cell of
 * the mask rect; a mask cell with no record is encoded empty -- today's
 * `_fill_masked`).
 *
 * Merge (today's `overlap.RowOverlap.merge_raw`, byte for byte): borrowed
 * shapes are appended after the cell's own backgrounds, in row order. Every
 * background-count column copies the source shape's element, except that a
 * cover row (kind 1) has b_ncoords = 4 and b_nstored = 5; coordinates are
 * the source shape's own, or for a cover row the receiver's bounds grown by
 * a quarter cell (`overlap.cover_ring`); the source label bytes are
 * appended to blob_bg_label. The result is in `spool.encode_columns` form.
 * The column layout is the descriptor's; it must equal `_cenc.c`'s COLS[]
 * (the encoders are bound to that schema) or the call fails (-7).
 *
 * Outputs (C-owned, thread-local, valid until the next kw_e2 call on the
 * thread; `bufs[0..2]` receive their addresses):
 *   index    36-byte packed rows (`descriptor.E2_INDEX_DTYPE`): ix i32, iy
 *            i32, level u8, pt u8, sx u8, sy u8 (pt=sx=sy=0), off u64
 *            (absolute in out_fd), len u32, road u32, bg u32, name u32
 *   declined 28-byte packed rows (`descriptor.E2_DECLINED_DTYPE`): ix i32,
 *            iy i32, reason u32 (1 = needs division), off u64, len u64
 *            into the blob
 *   blob     declined cells' merged records, concatenated
 * Frame bytes go to out_fd from out_off on, contiguously, in index order.
 *
 * Counters (int64[E2_NCNT], additive over ranges): 0 cells, 1 frames,
 * 2 declined, 3 frame bytes, 4 blob bytes, 5 total roads, 6 total
 * backgrounds, 7 total names (over every cell, merged -- the manifest's
 * `total`), 8 borrowed shapes appended, 9 cover rings, 10 C nanoseconds.
 *
 * Return 0, or < 0: -1 bad descriptor, -2 bad spool index, -3 bad spool
 * record, -4 out of memory, -5 bad rows (order, or a target that is not a
 * receiving cell of this range), -6 write to out_fd failed, -7 descriptor
 * column table differs from COLS[]. */
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define E2_HDR 168
#define E2_MAXCOLS 64
#define E2_E1ROW 32
#define E2_IXROW 36
#define E2_DCROW 28
#define E2_FRAME_CAP 0x20000 /* encode_common's `out` capacity (SUB_CAP) */
#define E2_WBUF (8 << 20)
#define E2_NCNT 11
#define E2_COVER_MARGIN 0.25

/* _cenc.c internals (same shared object) */
int64_t kw__encode_rec(const uint8_t *rec, int64_t rec_len, int level, int64_t ix,
                       int64_t iy, const double *grid, int64_t threshold,
                       const int64_t *lim, uint8_t *out, int64_t *sizes_out,
                       double coord_range);
int kw__col_index(int which);
int kw_ncols(void);
int kw_col_size(int i);
int kw_col_key(int i);
int kw_bounds(int64_t ix, int64_t iy, double dlat, double dlon, double cell_lat,
              double cell_lon, double *out4);

typedef struct {
    int32_t level, nx, ny, range0, threshold;
    double grid[4];
    int32_t win[4];
    int64_t lim[3];
    const uint8_t *mask;
    uint32_t n_cols;
    uint8_t csize[E2_MAXCOLS], ckey[E2_MAXCOLS];
    int c_class, c_nst, c_lat, c_lon, c_ncoords, c_llen, c_blob;
    int k_bg, k_coord, k_blob;
} e2_desc;

typedef struct {
    const uint8_t *col[E2_MAXCOLS];
    uint64_t cnt[9];
    uint64_t len;
    /* incremental walk over the shapes (source records only) */
    int64_t kk, cs, ls;
} e2_rec;

typedef struct { int64_t src, k, cstart, n, lstart, llen; int cover; } e2_item;

typedef struct { uint8_t *p; int64_t n, cap; } e2_buf;

static __thread e2_buf g_e2_idx, g_e2_dec, g_e2_blob, g_e2_mrec, g_e2_wbuf;
static __thread e2_item *g_e2_items = NULL;
static __thread int64_t g_e2_cap_items = 0;
static __thread e2_rec *g_e2_srcs = NULL;
static __thread int64_t g_e2_cap_srcs = 0;

static inline uint32_t e2_u32(const uint8_t *p) { uint32_t v; memcpy(&v, p, 4); return v; }
static inline int32_t e2_i32(const uint8_t *p) { int32_t v; memcpy(&v, p, 4); return v; }
static inline uint64_t e2_u64(const uint8_t *p) { uint64_t v; memcpy(&v, p, 8); return v; }
static inline double e2_f64(const uint8_t *p) { double v; memcpy(&v, p, 8); return v; }
static inline int64_t e2_i64(const uint8_t *p) { int64_t v; memcpy(&v, p, 8); return v; }

static int e2_reserve(e2_buf *b, int64_t extra) {
    if (b->n + extra <= b->cap) return 0;
    int64_t nc = b->cap ? b->cap : 1 << 16;
    while (nc < b->n + extra) nc *= 2;
    uint8_t *np = realloc(b->p, (size_t)nc);
    if (!np) return -1;
    b->p = np; b->cap = nc;
    return 0;
}

static int e2_parse_desc(const uint8_t *d, int64_t len, e2_desc *o) {
    if (len < E2_HDR || memcmp(d, "KWLDESC1", 8) != 0) return -1;
    if (e2_u32(d + 8) != 1 || e2_u32(d + 12) != E2_HDR) return -1;
    if ((int64_t)e2_u64(d + 16) != len) return -1;
    o->level = e2_i32(d + 24); o->nx = e2_i32(d + 28); o->ny = e2_i32(d + 32);
    if (o->nx <= 0 || o->ny <= 0 || o->nx > (1 << 16) || o->ny > (1 << 16)) return -1;
    for (int i = 0; i < 4; i++) o->grid[i] = e2_f64(d + 40 + 8 * i);
    if (!(o->grid[2] > 0) || !(o->grid[3] > 0)) return -1;
    o->range0 = e2_i32(d + 72);
    if (o->range0 <= 0) return -1;
    for (int i = 0; i < 4; i++) o->win[i] = e2_i32(d + 88 + 4 * i);
    o->threshold = e2_i32(d + 108);
    for (int i = 0; i < 3; i++) o->lim[i] = e2_i64(d + 112 + 8 * i);
    uint64_t moff = e2_u64(d + 136), mlen = e2_u64(d + 144);
    uint64_t need = ((uint64_t)o->nx * (uint64_t)o->ny + 7) / 8;
    if (mlen < need || moff > (uint64_t)len || mlen > (uint64_t)len - moff) return -1;
    o->mask = d + moff;
    uint32_t coff = e2_u32(d + 152);
    o->n_cols = e2_u32(d + 156);
    if (e2_u32(d + 160) != 9 || o->n_cols == 0 || o->n_cols > E2_MAXCOLS) return -1;
    if ((uint64_t)coff + 2ull * o->n_cols > (uint64_t)len) return -1;
    for (uint32_t c = 0; c < o->n_cols; c++) {
        o->csize[c] = d[coff + 2 * c]; o->ckey[c] = d[coff + 2 * c + 1];
        if (o->ckey[c] >= 9 || o->csize[c] == 0 || o->csize[c] > 8) return -1;
    }
    /* the encoders' schema binding (see _cenc.c COLS[]) */
    if ((int)o->n_cols != kw_ncols()) return -7;
    for (uint32_t c = 0; c < o->n_cols; c++)
        if (o->csize[c] != kw_col_size((int)c) || o->ckey[c] != kw_col_key((int)c)) return -7;
    int role[4];
    for (int i = 0; i < 4; i++) {
        role[i] = d[164 + i];
        if (role[i] >= (int)o->n_cols) return -1;
    }
    o->c_class = role[0]; o->c_nst = role[1]; o->c_lat = role[2]; o->c_lon = role[3];
    if (o->c_class != kw__col_index(6) || o->c_nst != kw__col_index(3) ||
        o->c_lat != kw__col_index(4) || o->c_lon != kw__col_index(5)) return -7;
    o->c_ncoords = kw__col_index(0); o->c_llen = kw__col_index(1); o->c_blob = kw__col_index(2);
    o->k_bg = o->ckey[o->c_nst]; o->k_coord = o->ckey[o->c_lat]; o->k_blob = o->ckey[o->c_blob];
    if (o->csize[o->c_nst] != 4 || o->csize[o->c_ncoords] != 4 || o->csize[o->c_llen] != 4 ||
        o->csize[o->c_lat] != 8 || o->csize[o->c_lon] != 8 || o->csize[o->c_blob] != 1 ||
        o->ckey[o->c_lon] != o->k_coord || o->ckey[o->c_ncoords] != o->k_bg ||
        o->ckey[o->c_llen] != o->k_bg || o->ckey[o->c_class] != o->k_bg) return -1;
    /* coordinate and label-blob columns are exactly the ones the merge fills */
    for (uint32_t c = 0; c < o->n_cols; c++) {
        if (o->ckey[c] == o->k_coord && (int)c != o->c_lat && (int)c != o->c_lon) return -1;
        if (o->ckey[c] == o->k_blob && (int)c != o->c_blob) return -1;
    }
    return 0;
}

/* Parse the record at `rec` (at most `avail` bytes; `exact` = it must be
 * exactly `avail` long). Columns per the descriptor table. */
static int e2_parse_rec(const e2_desc *D, const uint8_t *rec, uint64_t avail, int exact,
                        e2_rec *r) {
    if (avail < 72) return -1;
    for (int k = 0; k < 9; k++) {
        r->cnt[k] = e2_u64(rec + 8 * k);
        if (r->cnt[k] > (1ull << 28)) return -1;
    }
    uint64_t pos = 72;
    for (uint32_t c = 0; c < D->n_cols; c++) {
        uint64_t nb = r->cnt[D->ckey[c]] * D->csize[c];
        if (pos + nb > avail) return -1;
        r->col[c] = rec + pos;
        pos += (nb + 7) & ~7ull;
        if (pos > avail) return -1;
    }
    if (exact && pos != avail) return -1;
    r->len = pos;
    r->kk = r->cs = r->ls = 0;
    return 0;
}

/* overlap.cover_ring: the receiver's bounds grown by a quarter cell,
 * counter-clockwise, closed; same operation order as the Python. */
static void e2_cover_ring(const double *b4, double *lat5, double *lon5) {
    double mlat = (b4[1] - b4[0]) * E2_COVER_MARGIN;
    double mlon = (b4[3] - b4[2]) * E2_COVER_MARGIN;
    double a = b4[0] - mlat, b = b4[1] + mlat;
    double c = b4[2] - mlon, d = b4[3] + mlon;
    lat5[0] = a; lon5[0] = c;
    lat5[1] = a; lon5[1] = d;
    lat5[2] = b; lon5[2] = d;
    lat5[3] = b; lon5[3] = c;
    lat5[4] = a; lon5[4] = c;
}

/* Locate shape `k` of source `s` (shapes arrive ascending per source). */
static int e2_locate(const e2_desc *D, e2_rec *s, int64_t k, e2_item *it) {
    int64_t nbg = (int64_t)s->cnt[D->k_bg];
    if (k < s->kk || k >= nbg) return -1;
    while (s->kk < k) {
        s->cs += e2_i32(s->col[D->c_nst] + 4 * s->kk);
        s->ls += e2_i32(s->col[D->c_llen] + 4 * s->kk);
        s->kk++;
    }
    int64_t n = e2_i32(s->col[D->c_nst] + 4 * k), ll = e2_i32(s->col[D->c_llen] + 4 * k);
    if (n < 0 || ll < 0 || s->cs + n > (int64_t)s->cnt[D->k_coord] ||
        s->ls + ll > (int64_t)s->cnt[D->k_blob]) return -1;
    it->k = k; it->cstart = s->cs; it->n = n; it->lstart = s->ls; it->llen = ll;
    return 0;
}

/* The merged record (encode_columns form) of `own` plus `it[0..n_it)` into
 * `out` (replaced). Returns its length, or -1 on out of memory. */
static int64_t e2_merge(const e2_desc *D, const e2_rec *own, const e2_item *it, int64_t n_it,
                        const e2_rec *srcs, const double *rlat, const double *rlon,
                        e2_buf *out) {
    uint64_t cnt[9];
    memcpy(cnt, own->cnt, sizeof cnt);
    for (int64_t j = 0; j < n_it; j++) {
        cnt[D->k_bg] += 1;
        cnt[D->k_coord] += (uint64_t)(it[j].cover ? 5 : it[j].n);
        cnt[D->k_blob] += (uint64_t)it[j].llen;
    }
    int64_t total = 72;
    for (uint32_t c = 0; c < D->n_cols; c++)
        total += (int64_t)((cnt[D->ckey[c]] * D->csize[c] + 7) & ~7ull);
    out->n = 0;
    if (e2_reserve(out, total)) return -1;
    uint8_t *o = out->p;
    memcpy(o, cnt, 72);
    int64_t pos = 72;
    for (uint32_t c = 0; c < D->n_cols; c++) {
        int sz = D->csize[c], key = D->ckey[c];
        int64_t nb = (int64_t)own->cnt[key] * sz;
        if (nb) memcpy(o + pos, own->col[c], (size_t)nb);
        pos += nb;
        for (int64_t j = 0; j < n_it; j++) {
            const e2_item *t = &it[j];
            const e2_rec *s = &srcs[t->src];
            if (key == D->k_bg) {
                if (t->cover && ((int)c == D->c_ncoords || (int)c == D->c_nst)) {
                    int32_t v = (int)c == D->c_ncoords ? 4 : 5;
                    memcpy(o + pos, &v, 4);
                } else {
                    memcpy(o + pos, s->col[c] + t->k * sz, (size_t)sz);
                }
                pos += sz;
            } else if (key == D->k_coord) {
                if (t->cover) {
                    memcpy(o + pos, (int)c == D->c_lat ? rlat : rlon, 40);
                    pos += 40;
                } else {
                    memcpy(o + pos, s->col[c] + t->cstart * sz, (size_t)(t->n * sz));
                    pos += t->n * sz;
                }
            } else if (key == D->k_blob) {
                memcpy(o + pos, s->col[c] + t->lstart, (size_t)t->llen);
                pos += t->llen;
            }
        }
        while (pos & 7) o[pos++] = 0;
    }
    out->n = pos;
    return pos;
}

static int e2_flush(int fd, uint64_t *off) {
    const uint8_t *b = g_e2_wbuf.p;
    size_t n = (size_t)g_e2_wbuf.n;
    while (n) {
        ssize_t r = pwrite(fd, b, n, (off_t)*off);
        if (r <= 0) return -1;
        b += r; n -= (size_t)r; *off += (uint64_t)r;
    }
    g_e2_wbuf.n = 0;
    return 0;
}

static inline int e2_exists(const e2_desc *D, int64_t ix, int64_t iy) {
    uint64_t bit = (uint64_t)iy * (uint64_t)D->nx + (uint64_t)ix;
    return (D->mask[bit >> 3] >> (bit & 7)) & 1;
}

int64_t kw_e2(const uint8_t *desc, int64_t desc_len, const uint8_t *idx, int64_t idx_len,
              const uint8_t *data, int64_t data_len, const uint8_t *rows, int64_t n_rows,
              int64_t row_lo, int64_t row_hi, int out_fd, uint64_t out_off,
              void **bufs, int64_t *counters) {
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    int64_t ret = 0;
    int64_t cnt[E2_NCNT - 1] = {0};
    e2_desc D;
    g_e2_idx.n = g_e2_dec.n = g_e2_blob.n = g_e2_wbuf.n = 0;
    if ((ret = e2_parse_desc(desc, desc_len, &D))) goto done;
    if (idx_len < 48 || memcmp(idx, "KWSPIDX1", 8) != 0) { ret = -2; goto done; }
    uint64_t ncell = e2_u64(idx + 8);
    if (ncell > (uint64_t)(idx_len - 48) / 24 || 48 + 24 * ncell != (uint64_t)idx_len) {
        ret = -2; goto done;
    }
    const uint8_t *aix = idx + 48, *aiy = aix + 4 * ncell;
    const uint8_t *aoff = aiy + 4 * ncell, *alen = aoff + 8 * ncell;
    int64_t y0 = D.win[2] > 0 ? D.win[2] : 0, y1 = D.win[3] < D.ny - 1 ? D.win[3] : D.ny - 1;
    int64_t x0 = D.win[0] > 0 ? D.win[0] : 0, x1 = D.win[1] < D.nx - 1 ? D.win[1] : D.nx - 1;
    if (row_lo > y0) y0 = row_lo;
    if (row_hi - 1 < y1) y1 = row_hi - 1;
    /* first spool cell with iy >= y0 */
    int64_t ci = 0;
    for (int64_t lo = 0, hi = (int64_t)ncell; lo < hi;) {
        int64_t m = lo + (hi - lo) / 2;
        if (e2_i32(aiy + 4 * m) < y0) lo = m + 1; else hi = m;
        ci = hi;
    }
    if (e2_reserve(&g_e2_wbuf, E2_WBUF)) { ret = -4; goto done; }
    uint64_t wr_off = out_off, frame_off = out_off;
    static const uint8_t empty_rec[72] = {0};
    e2_rec own;
    int64_t ri = 0;
    for (int64_t iy = y0; iy <= y1; iy++) {
        for (int64_t ix = x0; ix <= x1; ix++) {
            /* own record: skip spool cells before (iy, ix) (outside the window) */
            while (ci < (int64_t)ncell) {
                int64_t cy = e2_i32(aiy + 4 * ci), cx = e2_i32(aix + 4 * ci);
                if (cy < iy || (cy == iy && cx < ix)) ci++; else break;
            }
            int has_own = ci < (int64_t)ncell && e2_i32(aiy + 4 * ci) == iy &&
                          e2_i32(aix + 4 * ci) == ix;
            if (!has_own && !e2_exists(&D, ix, iy)) continue;
            const uint8_t *rec = empty_rec;
            uint64_t rlen = 72;
            if (has_own) {
                uint64_t off = e2_u64(aoff + 8 * ci);
                rlen = e2_u64(alen + 8 * ci);
                if (off > (uint64_t)data_len || rlen > (uint64_t)data_len - off) {
                    ret = -3; goto done;
                }
                rec = data + off;
            }
            /* this cell's routed rows */
            int64_t n_it = 0, n_src = 0;
            int64_t last_off = -1, pk_y = 0, pk_x = 0, pk_s = 0;
            while (ri < n_rows) {
                const uint8_t *r = rows + E2_E1ROW * ri;
                int64_t tx = e2_i32(r), ty = e2_i32(r + 4);
                if (ty != iy || tx != ix) break;
                int64_t sx = e2_i32(r + 8), sy = e2_i32(r + 12);
                uint64_t soff = e2_u64(r + 16);
                int64_t k = e2_u32(r + 24);
                int kind = r[28];
                if (n_it && !(sy > pk_y || (sy == pk_y && (sx > pk_x ||
                                                           (sx == pk_x && k > pk_s))))) {
                    ret = -5; goto done;
                }
                pk_y = sy; pk_x = sx; pk_s = k;
                if ((int64_t)soff != last_off) {
                    if (n_src == g_e2_cap_srcs) {
                        int64_t nc = g_e2_cap_srcs ? 2 * g_e2_cap_srcs : 64;
                        e2_rec *ns = realloc(g_e2_srcs, (size_t)nc * sizeof *ns);
                        if (!ns) { ret = -4; goto done; }
                        g_e2_srcs = ns; g_e2_cap_srcs = nc;
                    }
                    if (soff >= (uint64_t)data_len ||
                        e2_parse_rec(&D, data + soff, (uint64_t)data_len - soff, 0,
                                     &g_e2_srcs[n_src])) { ret = -3; goto done; }
                    n_src++;
                    last_off = (int64_t)soff;
                }
                if (n_it == g_e2_cap_items) {
                    int64_t nc = g_e2_cap_items ? 2 * g_e2_cap_items : 256;
                    e2_item *ni = realloc(g_e2_items, (size_t)nc * sizeof *ni);
                    if (!ni) { ret = -4; goto done; }
                    g_e2_items = ni; g_e2_cap_items = nc;
                }
                e2_item *it = &g_e2_items[n_it];
                it->src = n_src - 1;
                it->cover = kind == 1;
                if (e2_locate(&D, &g_e2_srcs[n_src - 1], k, it)) { ret = -3; goto done; }
                cnt[8]++;
                cnt[9] += it->cover;
                n_it++;
                ri++;
            }
            if (n_it) {
                if (e2_parse_rec(&D, rec, rlen, 1, &own)) { ret = -3; goto done; }
                double b4[4], rlat[5], rlon[5];
                kw_bounds(ix, iy, D.grid[0], D.grid[1], D.grid[2], D.grid[3], b4);
                e2_cover_ring(b4, rlat, rlon);
                int64_t m = e2_merge(&D, &own, g_e2_items, n_it, g_e2_srcs, rlat, rlon,
                                     &g_e2_mrec);
                if (m < 0) { ret = -4; goto done; }
                rec = g_e2_mrec.p;
                rlen = (uint64_t)m;
            } else if (rlen < 72) {
                ret = -3; goto done;
            }
            cnt[0]++;
            cnt[5] += (int64_t)e2_u64(rec);
            cnt[6] += (int64_t)e2_u64(rec + 24);
            cnt[7] += (int64_t)e2_u64(rec + 40);
            if (g_e2_wbuf.cap - g_e2_wbuf.n < E2_FRAME_CAP && e2_flush(out_fd, &wr_off)) {
                ret = -6; goto done;
            }
            int64_t sizes[3] = {0, 0, 0};
            int64_t n = kw__encode_rec(rec, (int64_t)rlen, D.level, ix, iy, D.grid,
                                       D.threshold, D.lim, g_e2_wbuf.p + g_e2_wbuf.n, sizes,
                                       (double)D.range0);
            if (n >= 0) {
                if (e2_reserve(&g_e2_idx, E2_IXROW)) { ret = -4; goto done; }
                uint8_t *o = g_e2_idx.p + g_e2_idx.n;
                int32_t xy[2] = {(int32_t)ix, (int32_t)iy};
                uint32_t v[4] = {(uint32_t)n, (uint32_t)sizes[0], (uint32_t)sizes[1],
                                 (uint32_t)sizes[2]};
                memcpy(o, xy, 8);
                o[8] = (uint8_t)D.level; o[9] = o[10] = o[11] = 0;
                memcpy(o + 12, &frame_off, 8);
                memcpy(o + 20, v, 16);
                g_e2_idx.n += E2_IXROW;
                g_e2_wbuf.n += n;
                frame_off += (uint64_t)n;
                cnt[1]++;
                cnt[3] += n;
            } else {
                if (e2_reserve(&g_e2_dec, E2_DCROW) || e2_reserve(&g_e2_blob, (int64_t)rlen)) {
                    ret = -4; goto done;
                }
                uint8_t *o = g_e2_dec.p + g_e2_dec.n;
                int32_t xy[2] = {(int32_t)ix, (int32_t)iy};
                uint32_t reason = 1;
                uint64_t boff = (uint64_t)g_e2_blob.n;
                memcpy(o, xy, 8);
                memcpy(o + 8, &reason, 4);
                memcpy(o + 12, &boff, 8);
                memcpy(o + 20, &rlen, 8);
                g_e2_dec.n += E2_DCROW;
                memcpy(g_e2_blob.p + g_e2_blob.n, rec, (size_t)rlen);
                g_e2_blob.n += (int64_t)rlen;
                cnt[2]++;
                cnt[4] += (int64_t)rlen;
            }
        }
    }
    if (ri != n_rows) { ret = -5; goto done; }
    if (e2_flush(out_fd, &wr_off)) { ret = -6; goto done; }
done:
    bufs[0] = g_e2_idx.p; bufs[1] = g_e2_dec.p; bufs[2] = g_e2_blob.p;
    clock_gettime(CLOCK_MONOTONIC, &t1);
    if (ret >= 0)
        for (int i = 0; i < E2_NCNT - 1; i++) counters[i] += cnt[i];
    counters[E2_NCNT - 1] += (int64_t)(t1.tv_sec - t0.tv_sec) * 1000000000LL +
                             (t1.tv_nsec - t0.tv_nsec);
    return ret;
}
