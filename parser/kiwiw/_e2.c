/* E2 -- the Stage 1 kernel (plan 03, 3C-07, 3C-09; DESIGN.md Contract B, "E2").
 *
 * One call per target row range [row_lo, row_hi) of one level. For every
 * receiving cell of the range (canonical (iy, ix) order) it merges the
 * cell's own spool record with the borrowed background shapes E1 routed
 * to it (read in place from the spool), adds interior-cover rings, and
 * encodes the cell with `_cenc.c`'s per-cell encoder. A cell that fits is
 * written to `out_fd` and indexed. A cell that does not fit is divided here
 * (3C-09; the old `divide.py`, byte for byte): re-tiled into a 2x2 (type 1)
 * and, if a quadrant is still over, a 4x4 (type 2) sub-grid; at type 2 the
 * per-kind budgets are enforced by priority trimming (or, when even that
 * cannot be represented, the priority shrink) and, on level 0, road names
 * a sub-cell lost to a neighbour are added back as a halo. Every sub-frame
 * is encoded against its parent's bounds (`kw__probe`).
 *
 * Inputs: the level descriptor (layout: `_e1.c` / `descriptor.py`; the last
 * 128 bytes are the division block E2 reads: sub-parcel ranges and keep-order
 * tables), the level's spool `.idx` / `.data` bytes (zero-copy), and the
 * routed E1 rows (`descriptor.E1_ROW_DTYPE`) whose targets lie in this range,
 * ordered by target (iy, ix), then source (iy, ix), then shape -- E1 emits
 * source then shape order, so one stable sort on the target key routes them.
 *
 * Receiving cells: every cell of the descriptor window, rows clipped to
 * [row_lo, row_hi), whose existence bit is set (a spool cell, or a cell of
 * the mask rect; a mask cell with no record is encoded empty).
 *
 * Merge (today's `overlap.RowOverlap.merge_raw`, byte for byte): borrowed
 * shapes are appended after the cell's own backgrounds, in row order. Every
 * background-count column copies the source shape's element, except that a
 * cover row (kind 1) has b_ncoords = 4 and b_nstored = 5; coordinates are
 * the source shape's own, or for a cover row the receiver's bounds grown by
 * a quarter cell (`overlap.cover_ring`); the source label bytes are
 * appended to blob_bg_label. The result is in `spool.encode_columns` form.
 * The column layout is the descriptor's; it must equal `_cenc.c`'s COLS[]
 * (the encoders are bound to that schema) or the call fails (-7). The
 * division code addresses columns by its own enum, checked by name against
 * `_cenc.c` (kw__col_named) at descriptor parse.
 *
 * Outputs (C-owned, thread-local, valid until the next kw_e2 call on the
 * thread; `bufs[0..1]` receive their addresses):
 *   index    36-byte packed rows (`descriptor.E2_INDEX_DTYPE`): ix i32, iy
 *            i32, level u8, pt u8, sx u8, sy u8 (a divided parent: one row
 *            per populated sub-cell, pt = 1 or 2, ascending (sy, sx)), off
 *            u64 (absolute in out_fd), len u32, road u32, bg u32, name u32
 *   declined 28-byte packed rows (`descriptor.E2_DECLINED_DTYPE`): ix i32,
 *            iy i32, reason u32 (2 = cannot be encoded even after
 *            division, which includes a missing sub-parcel range), off,
 *            len u64 (0). The build treats any declined row as an error.
 * Frame bytes go to out_fd from out_off on, contiguously, in index order.
 *
 * Counters (int64[E2_NCNT], additive over ranges): 0 cells, 1 frames,
 * 2 declined, 3 frame bytes, 4 total roads, 5 total backgrounds, 6 total
 * names (over every cell, merged -- the manifest's `total`), 7 borrowed
 * shapes appended, 8 cover rings, 9..11 items dropped by trimming (road,
 * background, name), 12..14 sub-cells trimmed (road, background, name),
 * 15 halo names added, 16 C nanoseconds.
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
#define E2_NCNT 17
#define E2_DIVB 128
#define E2_NOLIM (1LL << 62)
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
int kw__col_named(const char *name);
int64_t kw__probe(const uint8_t *rec, int64_t rec_len, int level, int64_t ix, int64_t iy,
                  const double *b4, const double *rect4, int64_t *sizes, uint8_t *out,
                  double coord_range);
double kw__norm_lon(double v);
int64_t kw__bg_shape(const double *lat, const double *lon, int64_t nc, int closed, int64_t mc,
                     int64_t tc, int64_t fl, const double *b4, const double *rect4, double cr,
                     uint8_t *out, int64_t room, int64_t *nrec);

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
    /* division block (descriptor.py KWLDIV01) */
    int32_t range1[4], range2[16];
    uint8_t road_rank[16], name_rank[8];
    uint8_t road_rank_def, halo, dup_rank, name_rank_def;
    uint32_t pin_mask;
    int use_kinds;
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

static __thread e2_buf g_e2_idx, g_e2_dec, g_e2_mrec, g_e2_wbuf;
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

/* The division code addresses spool columns by this enum (same order as
 * `_cenc.c` COLS[]); every name is checked against `_cenc.c` at descriptor
 * parse, so drift from the schema fails loudly (-7). */
enum {
    X_R_DC, X_R_TYPE, X_R_P3D, X_R_NN, X_R_LID, X_R_ORD, X_R_WAY, X_R_FLAGS, X_R_NST, X_R_NPTS,
    X_N_X, X_N_Y, X_N_LAT, X_N_LON, X_N_ONEWAY, X_N_PLANNED, X_N_FLAGS,
    X_P_LAT, X_P_LON,
    X_B_CLASS, X_B_TYPE, X_B_NCOORDS, X_B_MULT, X_B_FLAGS, X_B_NST, X_B_LLEN,
    X_C_LAT, X_C_LON,
    X_S_TYPE, X_S_CODE, X_S_PRIO, X_S_DSF, X_S_ANGF, X_S_VERT, X_S_PRES,
    X_S_LLEN, X_S_TLEN, X_S_LAT, X_S_LON, X_S_ANGLE,
    X_BLOB_BG, X_BLOB_NL, X_BLOB_NT,
    X_N
};
static const char *const X_NAMES[X_N] = {
    "r_display_class", "r_road_type", "r_pseudo3d", "r_n_nodes", "r_link_id",
    "r_ordinal", "r_way_id", "r_flags", "r_nstored", "r_npts",
    "n_x", "n_y", "n_lat", "n_lon", "n_oneway", "n_planned", "n_flags",
    "p_lat", "p_lon",
    "b_class", "b_type", "b_ncoords", "b_mult", "b_flags", "b_nstored", "b_label_len",
    "c_lat", "c_lon",
    "s_type", "s_code", "s_prio", "s_dsf", "s_angflags", "s_vertical", "s_present",
    "s_label_len", "s_text_len", "s_lat", "s_lon", "s_angle",
    "blob_bg_label", "blob_name_label", "blob_name_text",
};

static int e2_check_names(void) {
    for (int i = 0; i < X_N; i++)
        if (kw__col_named(X_NAMES[i]) != i) return -7;
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
    /* the division block (descriptor.py KWLDIV01), the descriptor's last 128 bytes */
    if (len < E2_HDR + E2_DIVB) return -1;
    const uint8_t *v = d + len - E2_DIVB;
    if (memcmp(v, "KWLDIV01", 8) != 0) return -1;
    uint64_t vo = (uint64_t)len - E2_DIVB;
    if (moff + mlen > vo || (uint64_t)coff + 2ull * o->n_cols > vo) return -1;
    for (int i = 0; i < 4; i++) o->range1[i] = e2_i32(v + 8 + 4 * i);
    for (int i = 0; i < 16; i++) o->range2[i] = e2_i32(v + 24 + 4 * i);
    memcpy(o->road_rank, v + 88, 16);
    o->road_rank_def = v[104]; o->halo = v[105]; o->dup_rank = v[106]; o->name_rank_def = v[107];
    memcpy(o->name_rank, v + 108, 8);
    o->pin_mask = e2_u32(v + 116);
    o->use_kinds = o->lim[0] != E2_NOLIM || o->lim[1] != E2_NOLIM || o->lim[2] != E2_NOLIM;
    return e2_check_names();
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

/* ==================================================================
 * Division (3C-09). Everything below is the port of the old `divide.py`
 * (`plan_divisions`, `_retile_content`, `_bg_sub_cells`, `_trim_kinds`,
 * `_shrink_priority`, `_halo_candidates`, `_add_name_halo`) and of the
 * extractor's `assign_to_parcel` / `split_polyline_by_parcel` /
 * `parcel_bounds`; same float operations in the same order. Content is
 * never decoded: a sub-cell's content is three lists of item ids into the
 * parent's spool columns (a road chain, a parent background, a name), and
 * every probe assembles a spool-form record from them for `kw__probe`.
 * ================================================================== */
#define K_NR_ 0
#define K_NN_ 1
#define K_NP_ 2
#define K_NB_ 3
#define K_NC_ 4
#define K_NS_ 5
#define K_BL_ 6
#define K_NL_ 7
#define K_NT_ 8
#define DV_NO_WAY (-(int64_t)9223372036854775807LL - 1)

typedef struct { int32_t par, cell, len; int64_t start; } dv_road;
typedef struct { int32_t par, cell; double lat, lon; } dv_name;
/* one sub-cell's content: road chains / background shapes / names, each an
 * array of item ids (dv_road index / parent background / dv_name index) */
typedef struct { const int32_t *v[3]; int64_t n[3]; } dv_lists;

typedef struct {
    const e2_desc *D;
    const e2_rec *P;
    int level, ix, iy, oom;
    double b4[4], lat_span, lon_span, cell_lat, cell_lon;
    int64_t nr, nb, ns;
    int64_t *roff, *boff, *toff; /* prefix sums, n + 1 entries */
    int64_t cap_roff, cap_boff, cap_toff;
    uint8_t *ltxt;               /* ASCII-lowercased blob_name_text */
    int64_t cap_ltxt;
    dv_road *rr; int64_t nrr, cap_rr;
    double *cpl, *cpo; int64_t ncp, cap_cp; /* chain vertex pool */
    dv_name *nm; int64_t nnm, cap_nm;
    int32_t *fc[3], *fi[3]; int64_t nf[3], cap_f[3]; /* flat (cell, item) entries */
    int32_t *bk[3]; int64_t bk_off[3][17], cap_bk[3]; /* bucketed by cell */
    int ptype, nx, ncell;
    int32_t cr[16];
    double rect[16][4];
    int64_t stats[7]; /* dropped road/bg/name, trimmed cells road/bg/name, halo names */
    int64_t flen[16], fsz[16][3]; /* per sub-cell frame length (-1 = none) and kind sizes */
    uint8_t no_halo[16];
} dv_state;

static __thread dv_state g_dv;
static __thread uint8_t *g_dv_frames; /* 18 * E2_FRAME_CAP: 16 cell slots, tmp, best */
static __thread e2_buf g_dv_rec;
static __thread uint8_t *g_dv_bgout;
static __thread int64_t g_dv_bgcap;

static int dv_grow(void **p, int64_t *cap, int64_t need, size_t esz) {
    if (need <= *cap) return 0;
    int64_t nc = *cap ? *cap : 1024;
    while (nc < need) nc *= 2;
    void *np = realloc(*p, (size_t)nc * esz);
    if (!np) return -1;
    *p = np; *cap = nc;
    return 0;
}
#define DV_GROW(X, ptr, cap, need) \
    (dv_grow((void **)&(ptr), &(cap), (need), sizeof *(ptr)) ? ((X)->oom = 1, -1) : 0)

/* LIFO scratch allocations (bisect order arrays, ...) */
static __thread void **g_dv_tp;
static __thread int g_dv_tn, g_dv_tc;
static void *dv_alloc(dv_state *X, size_t n) {
    if (!n) n = 1;
    void *q = malloc(n);
    if (!q) { X->oom = 1; return NULL; }
    if (g_dv_tn == g_dv_tc) {
        int nc = g_dv_tc ? 2 * g_dv_tc : 64;
        void **np = realloc(g_dv_tp, (size_t)nc * sizeof *np);
        if (!np) { free(q); X->oom = 1; return NULL; }
        g_dv_tp = np; g_dv_tc = nc;
    }
    g_dv_tp[g_dv_tn++] = q;
    return q;
}
static int dv_mark(void) { return g_dv_tn; }
static void dv_release(int m) { while (g_dv_tn > m) free(g_dv_tp[--g_dv_tn]); }

static inline int dv_clamp(double v, int n) { return v >= (double)n ? n - 1 : v > 0.0 ? (int)v : 0; }

/* assign_to_parcel against the sub-grid scoped to the parent's bounds;
 * the cell index sub_iy * nx + sub_ix, or -1 (None) */
static int dv_assign(const dv_state *X, double lat, double lon) {
    /* Sub-cell index for (lat, lon) inside the parent, or -1 if outside.
     * Lon is brought into [0, 360) relative to the west edge so an
     * antimeridian-spanning parent still works, but a point that remains
     * outside [0, lon_span] after that normalize must NOT wrap into the
     * opposite side of the cell (plan 53: epsilon past the east edge was
     * wrapping to sx=0 while encode clamped x to 4096 — R-G9-3-d). */
    double dlat = lat - X->b4[0];
    if (dlat < 0.0 || dlat >= X->lat_span) return -1;
    double delta = lon - X->b4[2];
    while (delta < 0.0) delta += 360.0;
    while (delta >= 360.0) delta -= 360.0;
    if (delta > X->lon_span) return -1;
    int sx = dv_clamp(delta / X->cell_lon, X->nx), sy = dv_clamp(dlat / X->cell_lat, X->nx);
    return sy * X->nx + sx;
}

static int dv_push(dv_state *X, int k, int cell, int32_t item) {
    if (X->nf[k] + 1 > X->cap_f[k]) {
        int64_t nc = X->cap_f[k] ? 2 * X->cap_f[k] : 1024;
        int32_t *a = realloc(X->fc[k], (size_t)nc * 4);
        if (a) X->fc[k] = a;
        int32_t *b = a ? realloc(X->fi[k], (size_t)nc * 4) : NULL;
        if (b) X->fi[k] = b;
        if (!a || !b) { X->oom = 1; return -1; }
        X->cap_f[k] = nc;
    }
    X->fc[k][X->nf[k]] = cell; X->fi[k][X->nf[k]] = item; X->nf[k]++;
    return 0;
}

static int dv_pt(dv_state *X, double lat, double lon) {
    if (X->ncp + 1 > X->cap_cp) {
        int64_t nc = X->cap_cp ? 2 * X->cap_cp : 4096;
        double *a = realloc(X->cpl, (size_t)nc * sizeof *a);
        if (a) X->cpl = a;
        double *b = a ? realloc(X->cpo, (size_t)nc * sizeof *b) : NULL;
        if (b) X->cpo = b;
        if (!a || !b) { X->oom = 1; return -1; }
        X->cap_cp = nc;
    }
    X->cpl[X->ncp] = lat; X->cpo[X->ncp] = lon; X->ncp++;
    return 0;
}

typedef struct { dv_state *X; int road, cur_par, have; int64_t start; } dv_sp;

static int dv_reg(dv_state *X, int road, int cell, int64_t start) {
    if (DV_GROW(X, X->rr, X->cap_rr, X->nrr + 1)) return -1;
    dv_road *r = &X->rr[X->nrr];
    r->par = road; r->cell = cell; r->len = (int32_t)(X->ncp - start); r->start = start;
    if (dv_push(X, 0, cell, (int32_t)X->nrr)) return -1;
    X->nrr++;
    return 0;
}

/* `_emit`: a chain of >= 2 points in a real parcel becomes a new link */
static int dv_finish(dv_sp *S) {
    dv_state *X = S->X;
    S->have = 0;
    if (S->cur_par >= 0 && X->ncp - S->start >= 2) return dv_reg(X, S->road, S->cur_par, S->start);
    X->ncp = S->start;
    return 0;
}

static int dv_leaf(dv_sp *S, double alat, double alon, double blat, double blon, int par) {
    dv_state *X = S->X;
    if (S->have && par == S->cur_par) return dv_pt(X, blat, blon);
    if (S->have && dv_finish(S)) return -1;
    S->start = X->ncp; S->cur_par = par; S->have = 1;
    if (dv_pt(X, alat, alon)) return -1;
    return dv_pt(X, blat, blon);
}

/* `_split_segment` (streamed straight into the chains) */
static int dv_split(dv_sp *S, double alat, double alon, double blat, double blon, int depth) {
    int p1 = dv_assign(S->X, alat, alon), p2 = dv_assign(S->X, blat, blon);
    if (p1 == p2 || depth >= 18) return dv_leaf(S, alat, alon, blat, blon, p1);
    double mlat = (alat + blat) / 2, mlon = (alon + blon) / 2;
    if (dv_split(S, alat, alon, mlat, mlon, depth + 1)) return -1;
    return dv_split(S, mlat, mlon, blat, blon, depth + 1);
}

/* stable counting sort of the flat entries of kind k by cell */
static int dv_bucket(dv_state *X, int k) {
    int64_t *off = X->bk_off[k], n = X->nf[k];
    memset(off, 0, sizeof X->bk_off[k]);
    for (int64_t e = 0; e < n; e++) off[X->fc[k][e] + 1]++;
    for (int c = 0; c < 16; c++) off[c + 1] += off[c];
    if (DV_GROW(X, X->bk[k], X->cap_bk[k], n ? n : 1)) return -1;
    int64_t fill[16];
    memcpy(fill, off, sizeof fill);
    for (int64_t e = 0; e < n; e++) X->bk[k][fill[X->fc[k][e]]++] = X->fi[k][e];
    return 0;
}

/* The parent's prefix sums, and the lowercased name-text blob. -1: the
 * record's counts are inconsistent. */
static int dv_setup_parent(dv_state *X) {
    const e2_rec *P = X->P;
    X->nr = (int64_t)P->cnt[K_NR_]; X->nb = (int64_t)P->cnt[K_NB_]; X->ns = (int64_t)P->cnt[K_NS_];
    if (DV_GROW(X, X->roff, X->cap_roff, X->nr + 1) || DV_GROW(X, X->boff, X->cap_boff, X->nb + 1) ||
        DV_GROW(X, X->toff, X->cap_toff, X->ns + 1)) return -1;
    X->roff[0] = X->boff[0] = X->toff[0] = 0;
    for (int64_t i = 0; i < X->nr; i++) {
        int64_t n = e2_i32(P->col[X_R_NPTS] + 4 * i);
        X->roff[i + 1] = X->roff[i] + (n > 0 ? n : 0);
    }
    for (int64_t i = 0; i < X->nb; i++) {
        int64_t n = e2_i32(P->col[X_B_NST] + 4 * i);
        if (n < 0) return -2;
        X->boff[i + 1] = X->boff[i] + n;
    }
    for (int64_t i = 0; i < X->ns; i++) {
        int64_t n = e2_i32(P->col[X_S_TLEN] + 4 * i);
        if (n < 0) return -2;
        X->toff[i + 1] = X->toff[i] + n;
    }
    if (X->roff[X->nr] > (int64_t)P->cnt[K_NP_] || X->boff[X->nb] > (int64_t)P->cnt[K_NC_] ||
        X->toff[X->ns] > (int64_t)P->cnt[K_NT_]) return -2;
    int64_t nt = (int64_t)P->cnt[K_NT_];
    if (DV_GROW(X, X->ltxt, X->cap_ltxt, nt ? nt : 1)) return -1;
    for (int64_t i = 0; i < nt; i++) {
        uint8_t c = P->col[X_BLOB_NT][i];
        X->ltxt[i] = (c >= 'A' && c <= 'Z') ? (uint8_t)(c + 32) : c;
    }
    return 0;
}

/* `_bg_sub_cells` for parent background `i`: push it onto every sub-cell
 * whose clip of it writes something (or its one wholly-containing cell). */
static int dv_bg_cells(dv_state *X, int64_t i) {
    const e2_rec *P = X->P;
    int64_t s = X->boff[i], n = X->boff[i + 1] - s;
    const uint8_t *cl = P->col[X_C_LAT] + 8 * s, *co = P->col[X_C_LON] + 8 * s;
    double dlon = X->b4[3] - X->b4[2], dlat = X->b4[1] - X->b4[0], cr0 = (double)X->cr[0];
    double x0 = 0, x1 = 0, y0 = 0, y1 = 0;
    for (int64_t j = 0; j < n; j++) {
        double fx = (e2_f64(co + 8 * j) - X->b4[2]) / dlon * cr0;
        double fy = (e2_f64(cl + 8 * j) - X->b4[0]) / dlat * cr0;
        if (j == 0) { x0 = x1 = fx; y0 = y1 = fy; continue; }
        if (fx < x0) x0 = fx;
        if (fx > x1) x1 = fx;
        if (fy < y0) y0 = fy;
        if (fy > y1) y1 = fy;
    }
    int cand[16], nc = 0, nx = X->nx;
    for (int sy = 0; sy < nx; sy++)
        for (int sx = 0; sx < nx; sx++) {
            int64_t cr = X->cr[sy * nx + sx];
            double k = (double)cr / cr0;
            double rx0 = (double)(sx * cr / nx), ry0 = (double)(sy * cr / nx);
            double rx1 = (double)((sx + 1) * cr / nx), ry1 = (double)((sy + 1) * cr / nx);
            if (x0 * k <= rx1 && x1 * k >= rx0 && y0 * k <= ry1 && y1 * k >= ry0)
                cand[nc++] = sy * nx + sx;
        }
    if (nc == 0) return 0;
    if (nc == 1) {
        int c = cand[0], sx = c % nx, sy = c / nx;
        int64_t cr = X->cr[c];
        double k = (double)cr / cr0;
        double rx0 = (double)(sx * cr / nx), ry0 = (double)(sy * cr / nx);
        double rx1 = (double)((sx + 1) * cr / nx), ry1 = (double)((sy + 1) * cr / nx);
        if (rx0 <= x0 * k && x1 * k <= rx1 && ry0 <= y0 * k && y1 * k <= ry1)
            return dv_push(X, 1, c, (int32_t)i);
    }
    int closed = e2_i32(P->col[X_B_CLASS] + 4 * i) == 2;
    int64_t mc = e2_i32(P->col[X_B_MULT] + 4 * i), tc = e2_i32(P->col[X_B_TYPE] + 4 * i);
    int64_t fl = P->col[X_B_FLAGS][i * 1];
    for (int q = 0; q < nc; q++) {
        int c = cand[q];
        int64_t nrec = 0, r;
        for (;;) {
            if (!g_dv_bgout || g_dv_bgcap == 0) {
                g_dv_bgcap = 1 << 16;
                free(g_dv_bgout);
                g_dv_bgout = malloc((size_t)g_dv_bgcap);
                if (!g_dv_bgout) { g_dv_bgcap = 0; X->oom = 1; return -1; }
            }
            r = kw__bg_shape((const double *)cl, (const double *)co, n, closed, mc, tc, fl,
                             X->b4, X->rect[c], (double)X->cr[c], g_dv_bgout, g_dv_bgcap, &nrec);
            if (r != -2 || g_dv_bgcap >= (1 << 26)) break;
            g_dv_bgcap <<= 2;
            free(g_dv_bgout);
            g_dv_bgout = malloc((size_t)g_dv_bgcap);
            if (!g_dv_bgout) { g_dv_bgcap = 0; X->oom = 1; return -1; }
        }
        /* a decline (-1, or -2 at the cap) is counted as "wrote something": the
         * Python fell back to its own clipper here (see the 3C-09 amendment) */
        if (r < 0 || nrec > 0)
            if (dv_push(X, 1, c, (int32_t)i)) return -1;
    }
    return 0;
}

/* Tier setup: sub-grid geometry, per-cell ranges and clip rectangles.
 * 1 = a needed range is missing (declined). */
static int dv_tier_setup(dv_state *X, int ptype) {
    const e2_desc *D = X->D;
    X->ptype = ptype; X->nx = ptype == 1 ? 2 : 4; X->ncell = X->nx * X->nx;
    X->lat_span = X->b4[1] - X->b4[0];
    X->lon_span = X->b4[3] - X->b4[2];
    X->cell_lat = X->lat_span / X->nx;
    X->cell_lon = X->lon_span / X->nx;
    for (int c = 0; c < X->ncell; c++) {
        int32_t cr = ptype == 1 ? D->range1[c] : D->range2[c];
        if (cr <= 0) return 1;
        X->cr[c] = cr;
        int sx = c % X->nx, sy = c / X->nx;
        int64_t n = X->nx;
        X->rect[c][0] = (double)(sx * (int64_t)cr / n);
        X->rect[c][1] = (double)(sy * (int64_t)cr / n);
        X->rect[c][2] = (double)((sx + 1) * (int64_t)cr / n);
        X->rect[c][3] = (double)((sy + 1) * (int64_t)cr / n);
    }
    return 0;
}

/* `_retile_content` for the tier set up in X: flat lists, then buckets. */
static int dv_retile(dv_state *X) {
    const e2_rec *P = X->P;
    X->nrr = X->ncp = X->nnm = 0;
    for (int k = 0; k < 3; k++) X->nf[k] = 0;
    for (int64_t i = 0; i < X->nr; i++) {
        int64_t n = X->roff[i + 1] - X->roff[i], s = X->roff[i];
        const uint8_t *pl = P->col[X_P_LAT] + 8 * s, *po = P->col[X_P_LON] + 8 * s;
        if (n == 1) {
            int par = dv_assign(X, e2_f64(pl), e2_f64(po));
            if (par >= 0) {
                int64_t st = X->ncp;
                if (dv_pt(X, e2_f64(pl), e2_f64(po)) || dv_reg(X, (int)i, par, st)) return -1;
            }
        } else if (n >= 2) {
            dv_sp S = {X, (int)i, -1, 0, 0};
            for (int64_t j = 0; j + 1 < n; j++)
                if (dv_split(&S, e2_f64(pl + 8 * j), e2_f64(po + 8 * j), e2_f64(pl + 8 * (j + 1)),
                             e2_f64(po + 8 * (j + 1)), 0))
                    return -1;
            if (dv_finish(&S)) return -1;
        }
    }
    for (int64_t i = 0; i < X->nb; i++) {
        int64_t s = X->boff[i];
        if (X->boff[i + 1] == s) continue;
        int32_t cls = e2_i32(P->col[X_B_CLASS] + 4 * i);
        if (cls != 1 && cls != 2) {
            int cell = dv_assign(X, e2_f64(P->col[X_C_LAT] + 8 * s), e2_f64(P->col[X_C_LON] + 8 * s));
            if (cell >= 0 && dv_push(X, 1, cell, (int32_t)i)) return -1;
        } else if (dv_bg_cells(X, i)) {
            return -1;
        }
    }
    for (int64_t i = 0; i < X->ns; i++) {
        if ((P->col[X_S_PRES][i * 1] & 3) != 3) continue;
        double lat = e2_f64(P->col[X_S_LAT] + 8 * i), lon = e2_f64(P->col[X_S_LON] + 8 * i);
        int cell = dv_assign(X, lat, lon);
        if (cell < 0) continue;
        if (DV_GROW(X, X->nm, X->cap_nm, X->nnm + 1)) return -1;
        X->nm[X->nnm] = (dv_name){(int32_t)i, cell, lat, lon};
        if (dv_push(X, 2, cell, (int32_t)X->nnm)) return -1;
        X->nnm++;
    }
    for (int k = 0; k < 3; k++)
        if (dv_bucket(X, k)) return -1;
    return 0;
}

static inline dv_lists dv_cell_lists(const dv_state *X, int c) {
    dv_lists L;
    for (int k = 0; k < 3; k++) {
        L.v[k] = X->bk[k] + X->bk_off[k][c];
        L.n[k] = X->bk_off[k][c + 1] - X->bk_off[k][c];
    }
    return L;
}

/* Probe: build the spool-form record of one sub-cell's content (`L`) and
 * encode it against the parent's bounds at the sub-cell's range and clip
 * rectangle. Only the columns the encoders read are filled; the point and
 * label blobs are empty (K_NP = K_BL = K_NL = 0, label-length columns 0).
 * Returns the frame length (bytes in `out`, kind sizes in `sizes`), or -1. */
static int64_t dv_probe(dv_state *X, int cell, const dv_lists *L, uint8_t *out, int64_t *sizes) {
    const e2_desc *D = X->D;
    const e2_rec *P = X->P;
    int64_t nr = L->n[0], nb = L->n[1], ns = L->n[2];
    uint64_t cnt[9] = {0};
    int64_t nn = 0, nc = 0, nt = 0;
    for (int64_t j = 0; j < nr; j++) nn += X->rr[L->v[0][j]].len;
    for (int64_t j = 0; j < nb; j++) nc += X->boff[L->v[1][j] + 1] - X->boff[L->v[1][j]];
    for (int64_t j = 0; j < ns; j++) {
        int64_t p = X->nm[L->v[2][j]].par;
        nt += X->toff[p + 1] - X->toff[p];
    }
    cnt[K_NR_] = (uint64_t)nr; cnt[K_NN_] = (uint64_t)nn; cnt[K_NB_] = (uint64_t)nb;
    cnt[K_NC_] = (uint64_t)nc; cnt[K_NS_] = (uint64_t)ns; cnt[K_NT_] = (uint64_t)nt;
    int64_t off[E2_MAXCOLS], total = 72;
    for (uint32_t c = 0; c < D->n_cols; c++) {
        off[c] = total;
        total += (int64_t)((cnt[D->ckey[c]] * D->csize[c] + 7) & ~7ull);
    }
    if (g_dv_rec.cap < total) {
        e2_buf t = {g_dv_rec.p, 0, g_dv_rec.cap};
        if (e2_reserve(&t, total)) { X->oom = 1; return -1; }
        g_dv_rec.p = t.p; g_dv_rec.cap = t.cap;
    }
    uint8_t *r = g_dv_rec.p;
    memset(r, 0, (size_t)total);
    memcpy(r, cnt, 72);
#define PC(cc, i, j) memcpy(r + off[cc] + (int64_t)(j) * D->csize[cc], \
                             P->col[cc] + (int64_t)(i) * D->csize[cc], D->csize[cc])
    int64_t nidx = 0;
    for (int64_t j = 0; j < nr; j++) {
        const dv_road *q = &X->rr[L->v[0][j]];
        int64_t p = q->par;
        PC(X_R_DC, p, j); PC(X_R_TYPE, p, j); PC(X_R_P3D, p, j);
        PC(X_R_LID, p, j); PC(X_R_ORD, p, j); PC(X_R_WAY, p, j);
        PC(X_R_FLAGS, p, j);
        int32_t len = q->len;
        memcpy(r + off[X_R_NN] + 4 * j, &len, 4);
        memcpy(r + off[X_R_NST] + 4 * j, &len, 4);
        memcpy(r + off[X_R_NPTS] + 4 * j, &len, 4);
        for (int32_t t = 0; t < len; t++) {
            memcpy(r + off[X_N_LAT] + 8 * (nidx + t), &X->cpl[q->start + t], 8);
            memcpy(r + off[X_N_LON] + 8 * (nidx + t), &X->cpo[q->start + t], 8);
        }
        nidx += len;
    }
    int64_t cpos = 0;
    for (int64_t j = 0; j < nb; j++) {
        int64_t i = L->v[1][j], n = X->boff[i + 1] - X->boff[i];
        PC(X_B_CLASS, i, j); PC(X_B_TYPE, i, j); PC(X_B_MULT, i, j);
        PC(X_B_FLAGS, i, j); PC(X_B_NST, i, j);
        memcpy(r + off[X_C_LAT] + 8 * cpos, P->col[X_C_LAT] + 8 * X->boff[i], (size_t)(8 * n));
        memcpy(r + off[X_C_LON] + 8 * cpos, P->col[X_C_LON] + 8 * X->boff[i], (size_t)(8 * n));
        cpos += n;
    }
    int64_t tpos = 0;
    for (int64_t j = 0; j < ns; j++) {
        const dv_name *q = &X->nm[L->v[2][j]];
        int64_t p = q->par, tl = X->toff[p + 1] - X->toff[p];
        PC(X_S_TYPE, p, j); PC(X_S_CODE, p, j); PC(X_S_PRIO, p, j);
        PC(X_S_DSF, p, j); PC(X_S_ANGF, p, j); PC(X_S_VERT, p, j);
        PC(X_S_PRES, p, j); PC(X_S_TLEN, p, j); PC(X_S_ANGLE, p, j);
        memcpy(r + off[X_S_LAT] + 8 * j, &q->lat, 8);
        memcpy(r + off[X_S_LON] + 8 * j, &q->lon, 8);
        memcpy(r + off[X_BLOB_NT] + tpos, P->col[X_BLOB_NT] + X->toff[p], (size_t)tl);
        tpos += tl;
    }
#undef PC
    return kw__probe(r, total, X->level, cell % X->nx, cell / X->nx, X->b4, X->rect[cell], sizes,
                     out, (double)X->cr[cell]);
}

/* ---- keep-order (the priority tables come from the descriptor) ---- */
typedef struct { double f; int64_t k1, k2, k3, k4; int32_t item, pos; } dv_key;

static int dv_cmp_i64(int64_t a, int64_t b) { return a < b ? -1 : a > b; }
static int dv_cmp_road(const void *a, const void *b) {
    const dv_key *x = a, *y = b;
    int c;
    if ((c = dv_cmp_i64(x->k1, y->k1)) || (c = dv_cmp_i64(x->k2, y->k2)) ||
        (c = dv_cmp_i64(x->k3, y->k3)) || (c = dv_cmp_i64(x->k4, y->k4))) return c;
    return dv_cmp_i64(x->pos, y->pos);
}
static int dv_cmp_bg(const void *a, const void *b) {
    const dv_key *x = a, *y = b;
    if (x->f < y->f) return -1;
    if (x->f > y->f) return 1;
    int c = dv_cmp_i64(x->k2, y->k2);
    return c ? c : dv_cmp_i64(x->pos, y->pos);
}
static int dv_cmp_name(const void *a, const void *b) {
    const dv_key *x = a, *y = b;
    int c = dv_cmp_i64(x->k1, y->k1);
    return c ? c : dv_cmp_i64(x->pos, y->pos);
}

typedef struct { int64_t idx, len; } dv_slot; /* idx = parent name index, -1 empty */

static uint64_t dv_fnv(const uint8_t *p, int64_t n, uint64_t h) {
    for (int64_t i = 0; i < n; i++) { h ^= p[i]; h *= 1099511628211ull; }
    return h;
}

/* `kind` (0 road, 1 background, 2 name) of `items` (n ids) best-first, in a
 * fresh scratch array; *n_pinned for roads. NULL on out of memory. */
static int32_t *dv_order(dv_state *X, int kind, const int32_t *items, int64_t n,
                         int64_t *n_pinned) {
    const e2_desc *D = X->D;
    const e2_rec *P = X->P;
    int32_t *out = dv_alloc(X, (size_t)n * 4);
    int mk = dv_mark();
    dv_key *K = dv_alloc(X, (size_t)n * sizeof *K);
    if (!out || !K) return NULL;
    *n_pinned = 0;
    if (kind == 0) {
        for (int64_t j = 0; j < n; j++) {
            const dv_road *q = &X->rr[items[j]];
            int32_t t = e2_i32(P->col[X_R_TYPE] + 4 * q->par);
            int64_t way = e2_i64(P->col[X_R_WAY] + 8 * q->par);
            K[j] = (dv_key){0, t >= 0 && t < 16 ? D->road_rank[t] : D->road_rank_def, -(int64_t)q->len,
                            way == DV_NO_WAY ? 0 : way, e2_i32(P->col[X_R_ORD] + 4 * q->par),
                            items[j], (int32_t)j};
            if (t >= 0 && t < 32 && ((D->pin_mask >> t) & 1)) (*n_pinned)++;
        }
        qsort(K, (size_t)n, sizeof *K, dv_cmp_road);
    } else if (kind == 1) {
        for (int64_t j = 0; j < n; j++) {
            int64_t i = items[j], s = X->boff[i], m = X->boff[i + 1] - s;
            double area = 0.0;
            if (m) {
                double la = e2_f64(P->col[X_C_LAT] + 8 * s), lb = la;
                double oa = e2_f64(P->col[X_C_LON] + 8 * s), ob = oa;
                for (int64_t q = 1; q < m; q++) {
                    double a = e2_f64(P->col[X_C_LAT] + 8 * (s + q)), b = e2_f64(P->col[X_C_LON] + 8 * (s + q));
                    if (a < la) la = a;
                    if (a > lb) lb = a;
                    if (b < oa) oa = b;
                    if (b > ob) ob = b;
                }
                area = (lb - la) * (ob - oa);
            }
            K[j] = (dv_key){m ? -area : 0.0, 0, -m, 0, 0, items[j], (int32_t)j};
        }
        qsort(K, (size_t)n, sizeof *K, dv_cmp_bg);
    } else {
        /* (text, string_type) seen-set in input order: a repeat ranks as a duplicate */
        int64_t cap = 16;
        while (cap < 2 * n + 2) cap *= 2;
        dv_slot *H = dv_alloc(X, (size_t)cap * sizeof *H);
        if (!H) return NULL;
        for (int64_t i = 0; i < cap; i++) H[i].idx = -1;
        for (int64_t j = 0; j < n; j++) {
            int64_t p = X->nm[items[j]].par, tl = X->toff[p + 1] - X->toff[p];
            const uint8_t *tx = P->col[X_BLOB_NT] + X->toff[p];
            int32_t ty = e2_i32(P->col[X_S_TYPE] + 4 * p);
            uint64_t h = dv_fnv(tx, tl, 1469598103934665603ull) ^ (uint64_t)(uint32_t)ty * 0x9E3779B97F4A7C15ull;
            int dup = 0;
            for (int64_t s = (int64_t)(h & (uint64_t)(cap - 1));; s = (s + 1) & (cap - 1)) {
                if (H[s].idx < 0) { H[s].idx = p; break; }
                int64_t q = H[s].idx;
                if (e2_i32(P->col[X_S_TYPE] + 4 * q) == ty && X->toff[q + 1] - X->toff[q] == tl &&
                    !memcmp(P->col[X_BLOB_NT] + X->toff[q], tx, (size_t)tl)) { dup = 1; break; }
            }
            int64_t rank = dup ? D->dup_rank : (ty >= 0 && ty < 8) ? D->name_rank[ty] : D->name_rank_def;
            K[j] = (dv_key){0, rank, 0, 0, 0, items[j], (int32_t)j};
        }
        qsort(K, (size_t)n, sizeof *K, dv_cmp_name);
    }
    for (int64_t j = 0; j < n; j++) out[j] = K[j].item;
    dv_release(mk);
    return out;
}

#define DV_SLOT(c) (g_dv_frames + (size_t)(c) * E2_FRAME_CAP)
#define DV_TMP 16
#define DV_BEST 17

static inline int dv_breach(const dv_state *X, const int64_t *sz) {
    for (int k = 0; k < 3; k++)
        if (X->D->lim[k] < E2_NOLIM && sz[k] > X->D->lim[k]) return 1;
    return 0;
}

/* `_trim_kinds` (last tier): the cell's standing frame is in its slot with
 * kind sizes fsz[cell]. Returns items dropped, or -1 on out of memory. */
static int64_t dv_trim(dv_state *X, int cell, const dv_lists *L) {
    const e2_desc *D = X->D;
    int mk = dv_mark();
    dv_lists cur = *L, T;
    uint8_t *tmp = DV_SLOT(DV_TMP), *bestf = DV_SLOT(DV_BEST);
    int64_t total = 0;
    for (int kind = 0; kind < 3; kind++) {
        int64_t limit = D->lim[kind];
        if (limit >= E2_NOLIM || X->fsz[cell][kind] <= limit) continue;
        int64_t n = cur.n[kind], np = 0, sz[3], bsz[3] = {0, 0, 0}, blen = 0;
        int32_t *ordered = dv_order(X, kind, cur.v[kind], n, &np);
        if (!ordered) { dv_release(mk); return -1; }
        T = cur; T.v[kind] = ordered; T.n[kind] = n;
        if (kind == 0 && np) {
            T.n[0] = np;
            int64_t r = dv_probe(X, cell, &T, tmp, sz);
            if (X->oom) { dv_release(mk); return -1; }
            if (r < 0 || sz[0] > limit) np = 0;
        }
        int64_t lo = np, hi = n, best = np;
        int have = 0;
        while (lo <= hi) {
            int64_t mid = (lo + hi) / 2;
            T.n[kind] = mid;
            int64_t r = dv_probe(X, cell, &T, tmp, sz);
            if (X->oom) { dv_release(mk); return -1; }
            if (r >= 0 && sz[kind] <= limit) {
                best = mid; have = 1; blen = r;
                memcpy(bsz, sz, sizeof bsz);
                uint8_t *t = tmp; tmp = bestf; bestf = t;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        if (!have) {
            T.n[kind] = best;
            int64_t r = dv_probe(X, cell, &T, tmp, sz);
            if (X->oom) { dv_release(mk); return -1; }
            if (r < 0) continue;
            blen = r; memcpy(bsz, sz, sizeof bsz);
            uint8_t *t = tmp; tmp = bestf; bestf = t;
        }
        cur.v[kind] = ordered; cur.n[kind] = best;
        memcpy(DV_SLOT(cell), bestf, (size_t)blen);
        X->flen[cell] = blen;
        memcpy(X->fsz[cell], bsz, sizeof bsz);
        int64_t dropped = n - best;
        total += dropped;
        if (dropped > 0) { X->stats[kind] += dropped; X->stats[3 + kind]++; }
    }
    dv_release(mk);
    return total;
}

/* `_shrink_priority` (last tier, the whole cell is over the hard ceiling).
 * 0 = frame in the slot, 1 = declined, -1 = out of memory. */
static int dv_shrink(dv_state *X, int cell, const dv_lists *L) {
    const e2_desc *D = X->D;
    int mk = dv_mark();
    dv_lists cur, T;
    uint8_t *tmp = DV_SLOT(DV_TMP), *bestf = DV_SLOT(DV_BEST);
    int64_t np, sz[3];
    for (int kind = 0; kind < 3; kind++) {
        int32_t *o = dv_order(X, kind, L->v[kind], L->n[kind], &np);
        if (!o) { dv_release(mk); return -1; }
        cur.v[kind] = o; cur.n[kind] = L->n[kind];
    }
    for (int kind = 0; kind < 3; kind++) {
        if (D->lim[kind] >= E2_NOLIM) continue;
        int64_t lo = 0, hi = L->n[kind], best = 0;
        T.v[0] = T.v[1] = T.v[2] = cur.v[kind]; T.n[0] = T.n[1] = T.n[2] = 0;
        T.v[kind] = cur.v[kind];
        while (lo <= hi) {
            int64_t mid = (lo + hi) / 2;
            T.n[kind] = mid;
            int64_t r = dv_probe(X, cell, &T, tmp, sz);
            if (X->oom) { dv_release(mk); return -1; }
            if (r >= 0 && sz[kind] <= D->lim[kind]) { best = mid; lo = mid + 1; }
            else hi = mid - 1;
        }
        cur.n[kind] = best;
    }
    int64_t rlen = dv_probe(X, cell, &cur, bestf, sz), rsz[3] = {0, 0, 0};
    if (X->oom) { dv_release(mk); return -1; }
    int have = rlen >= 0;
    if (have) memcpy(rsz, sz, sizeof rsz);
    for (int kind = 0; kind < 3 && !have; kind++) {
        int64_t lo = 0, hi = cur.n[kind], best = 0, blen = -1, bsz[3] = {0, 0, 0};
        T = cur;
        while (lo <= hi) {
            int64_t mid = (lo + hi) / 2;
            T.n[kind] = mid;
            int64_t r = dv_probe(X, cell, &T, tmp, sz);
            if (X->oom) { dv_release(mk); return -1; }
            if (r >= 0) {
                best = mid; blen = r; memcpy(bsz, sz, sizeof bsz);
                uint8_t *t = tmp; tmp = bestf; bestf = t;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        cur.n[kind] = best;
        if (blen >= 0) {
            rlen = blen; memcpy(rsz, bsz, sizeof rsz); have = 1;
        } else {
            rlen = dv_probe(X, cell, &cur, bestf, sz);
            if (X->oom) { dv_release(mk); return -1; }
            if (rlen >= 0) { memcpy(rsz, sz, sizeof rsz); have = 1; }
        }
    }
    if (!have) { dv_release(mk); return 1; }
    memcpy(DV_SLOT(cell), bestf, (size_t)rlen);
    X->flen[cell] = rlen;
    memcpy(X->fsz[cell], rsz, sizeof rsz);
    for (int kind = 0; kind < 3; kind++) {
        int64_t d = L->n[kind] - cur.n[kind];
        if (d > 0) { X->stats[kind] += d; X->stats[3 + kind]++; }
    }
    dv_release(mk);
    return 0;
}

/* ---- name halo ---- */
typedef struct { int64_t par; double d, lat, lon; } dv_cand;

static int dv_text_cmp(const dv_state *X, int64_t a, int64_t b) {
    int64_t la = X->toff[a + 1] - X->toff[a], lb = X->toff[b + 1] - X->toff[b];
    int c = memcmp(X->ltxt + X->toff[a], X->ltxt + X->toff[b], (size_t)(la < lb ? la : lb));
    return c ? c : (la < lb ? -1 : la > lb);
}
static int dv_cmp_cand(const void *a, const void *b) {
    const dv_cand *x = a, *y = b;
    if (x->d < y->d) return -1;
    if (x->d > y->d) return 1;
    return dv_text_cmp(&g_dv, x->par, y->par);
}

/* slot table over lowercased texts; values are parent name indices */
static int64_t dv_tfind(const dv_state *X, const int64_t *tab, int64_t cap, int64_t p, int *found) {
    int64_t len = X->toff[p + 1] - X->toff[p];
    uint64_t h = dv_fnv(X->ltxt + X->toff[p], len, 1469598103934665603ull);
    for (int64_t s = (int64_t)(h & (uint64_t)(cap - 1));; s = (s + 1) & (cap - 1)) {
        if (tab[s] < 0) { *found = 0; return s; }
        if (dv_text_cmp(X, tab[s], p) == 0) { *found = 1; return s; }
    }
}

/* `_halo_candidates` + `_add_name_halo` for one populated sub-cell. */
static int dv_halo(dv_state *X, int cell, const dv_lists *L) {
    const e2_desc *D = X->D;
    const e2_rec *P = X->P;
    int nx = X->nx, sx = cell % nx, sy = cell / nx;
    volatile double two = 2.0;
    double lat_lo = X->b4[0] + sy * X->cell_lat, lat_hi = lat_lo + X->cell_lat;
    double lon_lo = kw__norm_lon(X->b4[2] + sx * X->cell_lon);
    double lon_hi = kw__norm_lon(X->b4[2] + sx * X->cell_lon + X->cell_lon);
    double h = lat_hi - lat_lo, w = lon_hi - lon_lo, inset_lat = h * 0.01, inset_lon = w * 0.01;
    int mk = dv_mark();
    int64_t ns = X->ns, nbase = L->n[2];
    int64_t cap = 16;
    while (cap < 2 * ns + 2) cap *= 2;
    int64_t *have = dv_alloc(X, (size_t)cap * 8), *best = dv_alloc(X, (size_t)cap * 8);
    int64_t *bidx = dv_alloc(X, (size_t)cap * 8);
    dv_cand *cand = dv_alloc(X, (size_t)(ns ? ns : 1) * sizeof *cand);
    if (!have || !best || !bidx || !cand) { dv_release(mk); return -1; }
    for (int64_t i = 0; i < cap; i++) have[i] = best[i] = -1;
    int found;
    for (int64_t j = 0; j < nbase; j++) {
        int64_t p = X->nm[L->v[2][j]].par;
        if (e2_i32(P->col[X_S_TYPE] + 4 * p) != 5) continue;
        int64_t s = dv_tfind(X, have, cap, p, &found);
        if (!found) have[s] = p;
    }
    int64_t nc = 0;
    for (int64_t p = 0; p < ns; p++) {
        if (e2_i32(P->col[X_S_TYPE] + 4 * p) != 5 || (P->col[X_S_PRES][p] & 3) != 3) continue;
        int64_t s = dv_tfind(X, have, cap, p, &found);
        if (found) continue;
        double lat = e2_f64(P->col[X_S_LAT] + 8 * p), lon = e2_f64(P->col[X_S_LON] + 8 * p);
        double dlat = lat_lo - lat, t2 = 0.0, t3 = lat - lat_hi;
        if (t2 > dlat) dlat = t2;
        if (t3 > dlat) dlat = t3;
        double dlon = lon_lo - lon, u3 = lon - lon_hi;
        if (t2 > dlon) dlon = t2;
        if (u3 > dlon) dlon = u3;
        if (dlat == 0.0 && dlon == 0.0) continue;
        if (dlat > h || dlon > w) continue;
        double a = dlat / h, b = dlon / w;
        double d = pow(a, two) + pow(b, two);
        s = dv_tfind(X, best, cap, p, &found);
        if (!found) {
            best[s] = p;            /* the table is keyed by text (via a parent index) */
            bidx[s] = nc;
            cand[nc++] = (dv_cand){p, d, lat, lon};
        } else {
            dv_cand *c = &cand[bidx[s]];
            if (d < c->d || (d == c->d && (lat < c->lat || (lat == c->lat && lon < c->lon)))) {
                c->par = p; c->d = d; c->lat = lat; c->lon = lon;
            }
        }
    }
    if (nc == 0) { dv_release(mk); return 0; }
    qsort(cand, (size_t)nc, sizeof *cand, dv_cmp_cand);
    int64_t nnm0 = X->nnm;
    if (DV_GROW(X, X->nm, X->cap_nm, nnm0 + nc)) { dv_release(mk); return -1; }
    int32_t *ids = dv_alloc(X, (size_t)(nbase + nc) * 4);
    if (!ids) { dv_release(mk); return -1; }
    memcpy(ids, L->v[2], (size_t)nbase * 4);
    for (int64_t k = 0; k < nc; k++) {
        double la = cand[k].lat, lo_ = cand[k].lon;
        double a = lat_lo + inset_lat, b = lat_hi - inset_lat;
        la = a > la ? a : la; la = la < b ? la : b;
        a = lon_lo + inset_lon; b = lon_hi - inset_lon;
        lo_ = a > lo_ ? a : lo_; lo_ = lo_ < b ? lo_ : b;
        X->nm[nnm0 + k] = (dv_name){(int32_t)cand[k].par, cell, la, lo_};
        ids[nbase + k] = (int32_t)(nnm0 + k);
    }
    dv_lists T = *L;
    T.v[2] = ids;
    uint8_t *tmp = DV_SLOT(DV_TMP), *bestf = DV_SLOT(DV_BEST);
    int64_t lo = 1, hi = nc, bk = 0, blen = 0, bsz[3] = {0, 0, 0}, sz[3];
    while (lo <= hi) {
        int64_t mid = (lo + hi) / 2;
        T.n[2] = nbase + mid;
        int64_t r = dv_probe(X, cell, &T, tmp, sz);
        if (X->oom) { X->nnm = nnm0; dv_release(mk); return -1; }
        if (r >= 0 && r <= D->threshold && (D->lim[2] >= E2_NOLIM || sz[2] <= D->lim[2])) {
            bk = mid; blen = r; memcpy(bsz, sz, sizeof bsz);
            uint8_t *t = tmp; tmp = bestf; bestf = t;
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    X->nnm = nnm0;
    if (bk > 0) {
        memcpy(DV_SLOT(cell), bestf, (size_t)blen);
        X->flen[cell] = blen;
        memcpy(X->fsz[cell], bsz, sizeof bsz);
        X->stats[6] += bk;
    }
    dv_release(mk);
    return 0;
}

/* Divide the parent in X (D, P, level, ix, iy, b4 set): 0 = frames in the
 * cell slots (flen >= 0, ascending cell index, X->ptype), 1 = declined (reason 2),
 * -1 = out of memory. */
static int dv_divide(dv_state *X) {
    const e2_desc *D = X->D;
    if (!D->use_kinds) return 1;
    if (!g_dv_frames && !(g_dv_frames = malloc((size_t)18 * E2_FRAME_CAP))) { X->oom = 1; return -1; }
    X->oom = 0;
    memset(X->stats, 0, sizeof X->stats);
    int rc = dv_setup_parent(X);
    if (rc == -1) return -1;
    if (rc) return -2;
    for (int ptype = 1; ptype <= 2; ptype++) {
        int last = ptype == 2, oversize = 0, any = 0;
        memset(X->stats, 0, sizeof X->stats);
        for (int c = 0; c < 16; c++) { X->flen[c] = -1; X->no_halo[c] = 0; }
        if (dv_tier_setup(X, ptype)) return 1;
        if (dv_retile(X)) return -1;
        for (int c = 0; c < X->ncell; c++) {
            dv_lists L = dv_cell_lists(X, c);
            if (!L.n[0] && !L.n[1] && !L.n[2]) continue;
            any = 1;
            int64_t sz[3], r = dv_probe(X, c, &L, DV_SLOT(c), sz);
            if (X->oom) return -1;
            if (r < 0) {
                oversize = 1;
                if (!last) break;
                int s = dv_shrink(X, c, &L);
                if (s < 0) return -1;
                if (s) return 1;
                X->no_halo[c] = 1;
                continue;
            }
            X->flen[c] = r;
            memcpy(X->fsz[c], sz, sizeof sz);
            if (r > D->threshold) oversize = 1;
            if (dv_breach(X, sz)) {
                if (last) {
                    int64_t n = dv_trim(X, c, &L);
                    if (n < 0) return -1;
                    if (n > 0) X->no_halo[c] = 1;
                } else {
                    oversize = 1;
                }
            }
            if (oversize && !last) break;
        }
        if (D->halo && (!oversize || last)) {
            for (int c = 0; c < X->ncell; c++) {
                if (X->flen[c] < 0 || X->no_halo[c]) continue;
                dv_lists L = dv_cell_lists(X, c);
                if (dv_halo(X, c, &L)) return -1;
            }
        }
        (void)any;
        if (!oversize || last) return 0;
    }
    return 0;
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
    g_e2_idx.n = g_e2_dec.n = g_e2_wbuf.n = 0;
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
                cnt[7]++;
                cnt[8] += it->cover;
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
            cnt[4] += (int64_t)e2_u64(rec);
            cnt[5] += (int64_t)e2_u64(rec + 24);
            cnt[6] += (int64_t)e2_u64(rec + 40);
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
                /* it did not fit whole: divide it here (retile, trim, name halo) */
                e2_rec mp;
                if (e2_parse_rec(&D, rec, rlen, 1, &mp)) { ret = -3; goto done; }
                dv_state *X = &g_dv;
                X->D = &D; X->P = &mp; X->level = D.level; X->ix = (int)ix; X->iy = (int)iy;
                kw_bounds(ix, iy, D.grid[0], D.grid[1], D.grid[2], D.grid[3], X->b4);
                int dr = dv_divide(X);
                if (dr == -1 || X->oom) { ret = -4; goto done; }
                if (dr < 0) { ret = -3; goto done; }
                if (dr == 1) {
                    /* reason 2: cannot be encoded even after division */
                    if (e2_reserve(&g_e2_dec, E2_DCROW)) { ret = -4; goto done; }
                    uint8_t *o = g_e2_dec.p + g_e2_dec.n;
                    int32_t xy[2] = {(int32_t)ix, (int32_t)iy};
                    uint32_t reason = 2;
                    uint64_t zero = 0;
                    memcpy(o, xy, 8);
                    memcpy(o + 8, &reason, 4);
                    memcpy(o + 12, &zero, 8);
                    memcpy(o + 20, &zero, 8);
                    g_e2_dec.n += E2_DCROW;
                    cnt[2]++;
                } else {
                    for (int c = 0; c < X->ncell; c++) {
                        int64_t fl = X->flen[c];
                        if (fl < 0) continue;
                        if (g_e2_wbuf.cap - g_e2_wbuf.n < fl && e2_flush(out_fd, &wr_off)) {
                            ret = -6; goto done;
                        }
                        if (e2_reserve(&g_e2_idx, E2_IXROW)) { ret = -4; goto done; }
                        memcpy(g_e2_wbuf.p + g_e2_wbuf.n, DV_SLOT(c), (size_t)fl);
                        uint8_t *o = g_e2_idx.p + g_e2_idx.n;
                        int32_t xy[2] = {(int32_t)ix, (int32_t)iy};
                        uint32_t v[4] = {(uint32_t)fl, (uint32_t)X->fsz[c][0],
                                         (uint32_t)X->fsz[c][1], (uint32_t)X->fsz[c][2]};
                        memcpy(o, xy, 8);
                        o[8] = (uint8_t)D.level; o[9] = (uint8_t)X->ptype;
                        o[10] = (uint8_t)(c % X->nx); o[11] = (uint8_t)(c / X->nx);
                        memcpy(o + 12, &frame_off, 8);
                        memcpy(o + 20, v, 16);
                        g_e2_idx.n += E2_IXROW;
                        g_e2_wbuf.n += fl;
                        frame_off += (uint64_t)fl;
                        cnt[1]++;
                        cnt[3] += fl;
                    }
                    for (int i = 0; i < 7; i++) cnt[9 + i] += X->stats[i];
                }
            }
        }
    }
    if (ri != n_rows) { ret = -5; goto done; }
    if (e2_flush(out_fd, &wr_off)) { ret = -6; goto done; }
done:
    bufs[0] = g_e2_idx.p; bufs[1] = g_e2_dec.p;
    clock_gettime(CLOCK_MONOTONIC, &t1);
    if (ret >= 0)
        for (int i = 0; i < E2_NCNT - 1; i++) counters[i] += cnt[i];
    counters[E2_NCNT - 1] += (int64_t)(t1.tv_sec - t0.tv_sec) * 1000000000LL +
                             (t1.tv_nsec - t0.tv_nsec);
    return ret;
}
