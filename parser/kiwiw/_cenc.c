/*
 * Whole-cell Map Frame encoder (plan 03: build performance, C hot path).
 *
 * Port of the Python oracle in synth.py (build_road_frame_bytes,
 * build_background_frame_bytes, build_name_frame_bytes, build_map_frame_bytes)
 * plus osm_to_parcel_geometry.parcel_bounds, operating straight on one binary
 * spool cell record (kiwiw/spool.py `_COLUMNS` layout).
 *
 * Contract: kw_encode_cell() returns the frame length when the cell fits the
 * frame threshold and the per-kind byte budgets; -1 for *anything else*
 * (oversize, kind breach, any input the Python encoders would raise on or that
 * this port does not model, malformed record). The caller then runs the Python
 * oracle (columns_to_content + divide.plan_divisions) for that cell, so this
 * file only ever has to be exactly right on the common path, and refuses
 * everything it is unsure of.
 *
 * Float exactness: build with -ffp-contract=off (no FMA), and keep the same
 * operation order as the Python expressions; rint() == Python's half-even
 * round().
 */
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define SUB_CAP 0x20000 /* sub-frame scratch capacity (> 131070 ceiling) */
#define MAX_FRAME 131070

enum { K_NR, K_NN, K_NP, K_NB, K_NC, K_NS, K_BL, K_NL, K_NT, N_KEYS };

typedef struct { int size; int key; } ColSpec;

/* Must mirror kiwiw/spool.py _COLUMNS exactly (checked by the tests). */
static const ColSpec COLS[] = {
    {4, K_NR}, {4, K_NR}, {4, K_NR}, {4, K_NR}, {4, K_NR}, {4, K_NR},
    {8, K_NR}, {2, K_NR}, {4, K_NR}, {4, K_NR},
    {4, K_NN}, {4, K_NN}, {8, K_NN}, {8, K_NN}, {4, K_NN}, {4, K_NN}, {1, K_NN},
    {8, K_NP}, {8, K_NP},
    {4, K_NB}, {4, K_NB}, {4, K_NB}, {4, K_NB}, {1, K_NB}, {4, K_NB}, {4, K_NB},
    {8, K_NC}, {8, K_NC},
    {4, K_NS}, {4, K_NS}, {4, K_NS}, {4, K_NS}, {4, K_NS}, {1, K_NS}, {1, K_NS},
    {4, K_NS}, {4, K_NS}, {8, K_NS}, {8, K_NS}, {8, K_NS},
    {1, K_BL}, {1, K_NL}, {1, K_NT},
};
enum {
    C_R_DC, C_R_TYPE, C_R_P3D, C_R_NN, C_R_LID, C_R_ORD, C_R_WAY, C_R_FLAGS,
    C_R_NST, C_R_NPTS,
    C_N_X, C_N_Y, C_N_LAT, C_N_LON, C_N_ONEWAY, C_N_PLANNED, C_N_FLAGS,
    C_P_LAT, C_P_LON,
    C_B_CLASS, C_B_TYPE, C_B_NCOORDS, C_B_MULT, C_B_FLAGS, C_B_NST, C_B_LLEN,
    C_C_LAT, C_C_LON,
    C_S_TYPE, C_S_CODE, C_S_PRIO, C_S_DSF, C_S_ANGF, C_S_VERT, C_S_PRES,
    C_S_LLEN, C_S_TLEN, C_S_LAT, C_S_LON, C_S_ANGLE,
    C_BLOB_BG, C_BLOB_NL, C_BLOB_NT,
    N_COLS
};

int kw_ncols(void) { return N_COLS; }
int kw_col_size(int i) { return COLS[i].size; }
int kw_col_key(int i) { return COLS[i].key; }

typedef struct {
    const uint8_t *col[N_COLS];
    int64_t cnt[N_KEYS];
} Rec;

static int parse_rec(const uint8_t *rec, int64_t len, Rec *r) {
    if (len < 72) return -1;
    for (int k = 0; k < N_KEYS; k++) {
        uint64_t v;
        memcpy(&v, rec + 8 * k, 8);
        if (v > (1u << 28)) return -1;
        r->cnt[k] = (int64_t)v;
    }
    int64_t pos = 72;
    for (int i = 0; i < N_COLS; i++) {
        int64_t bytes = r->cnt[COLS[i].key] * COLS[i].size;
        if (pos + bytes > len) return -1;
        r->col[i] = rec + pos;
        pos += bytes;
        pos += (8 - (pos & 7)) & 7;
    }
    return pos == len ? 0 : -1;
}

static inline int64_t rd_i32(const uint8_t *p, int64_t i) {
    int32_t v; memcpy(&v, p + 4 * i, 4); return v;
}
static inline int64_t rd_u16(const uint8_t *p, int64_t i) {
    uint16_t v; memcpy(&v, p + 2 * i, 2); return v;
}
static inline double rd_f64(const uint8_t *p, int64_t i) {
    double v; memcpy(&v, p + 8 * i, 8); return v;
}

static inline void put16(uint8_t *b, int64_t pos, int64_t v) {
    b[pos] = (uint8_t)((v >> 8) & 0xFF);
    b[pos + 1] = (uint8_t)(v & 0xFF);
}
static inline void put32(uint8_t *b, int64_t pos, int64_t v) {
    b[pos] = (uint8_t)((v >> 24) & 0xFF);
    b[pos + 1] = (uint8_t)((v >> 16) & 0xFF);
    b[pos + 2] = (uint8_t)((v >> 8) & 0xFF);
    b[pos + 3] = (uint8_t)(v & 0xFF);
}

/* range: the frame's coordinate range (coordconv.range_for), supplied by the
 * caller -- this file owns no range constant. Road and name vertices are
 * clamped to the admissible pixel interval [0, range] inclusive (cmax =
 * range; a boundary vertex lands exactly on the frame edge). Background
 * geometry is clipped to `rect` (x0, y0, x1, y1), never clamped. */
typedef struct { double lat_lo, lat_hi, lon_lo, lon_hi, range, cmax; double rect[4]; } Bounds;

/* latlon_to_xy + _clamp_coord: 0 ok, -1 not representable (NaN). */
static inline int to_xy(double lat, double lon, const Bounds *b, int64_t *x, int64_t *y) {
    double fx = rint((lon - b->lon_lo) / (b->lon_hi - b->lon_lo) * b->range);
    double fy = rint((lat - b->lat_lo) / (b->lat_hi - b->lat_lo) * b->range);
    if (isnan(fx) || isnan(fy)) return -1;
    *x = fx < 0 ? 0 : fx > b->cmax ? (int64_t)b->cmax : (int64_t)fx;
    *y = fy < 0 ? 0 : fy > b->cmax ? (int64_t)b->cmax : (int64_t)fy;
    return 0;
}

static inline int64_t region_coord(int64_t v) { /* encode_region_coord */
    return (v % 4096) | ((v / 4096) << 13);
}

/* ---------------------------------------------------------------- road */

static __thread int32_t *g_order = NULL;
static __thread int64_t *g_nstart = NULL;
static __thread int64_t g_cap_roads = 0;

static int ensure_roads(int64_t n) {
    if (n <= g_cap_roads) return 0;
    int64_t cap = n < 1024 ? 1024 : n;
    int32_t *o = realloc(g_order, (size_t)cap * sizeof(int32_t));
    if (!o) return -1;
    g_order = o;
    int64_t *s = realloc(g_nstart, (size_t)cap * sizeof(int64_t));
    if (!s) return -1;
    g_nstart = s;
    g_cap_roads = cap;
    return 0;
}

/* returns frame length (>0), or -1. Only called with n_roads > 0. */
static int64_t enc_road(const Rec *r, const Bounds *bd, uint8_t *out) {
    int64_t nr = r->cnt[K_NR], nn = r->cnt[K_NN];
    if (ensure_roads(nr)) return -1;
    const uint8_t *dcc = r->col[C_R_DC], *nst = r->col[C_R_NST];
    int64_t dc_count[256];
    memset(dc_count, 0, sizeof dc_count);
    int64_t max_dc = -1, ni = 0;
    for (int64_t i = 0; i < nr; i++) {
        int64_t dc = rd_i32(dcc, i), ns = rd_i32(nst, i);
        if (dc < 0 || dc > 254 || ns < 1) return -1;
        if (16 + 6 * ns > 2 * 0xFFFF) return -1;
        g_nstart[i] = ni;
        ni += ns;
        if (ni > nn) return -1;
        dc_count[dc]++;
        if (dc > max_dc) max_dc = dc;
    }
    int64_t n_dc = max_dc + 1;
    /* counting sort of link indices by display class, input order kept */
    int64_t base[257];
    base[0] = 0;
    for (int64_t d = 0; d < n_dc; d++) base[d + 1] = base[d] + dc_count[d];
    int64_t fill[256];
    for (int64_t d = 0; d < n_dc; d++) fill[d] = base[d];
    for (int64_t i = 0; i < nr; i++) g_order[fill[rd_i32(dcc, i)]++] = (int32_t)i;

    int64_t header_end = 8 + n_dc * 4;
    if (header_end > SUB_CAP) return -1;
    memset(out, 0, (size_t)header_end);
    out[4] = (uint8_t)n_dc;

    const uint8_t *rtype = r->col[C_R_TYPE], *p3d = r->col[C_R_P3D], *fl = r->col[C_R_FLAGS];
    const uint8_t *nlat = r->col[C_N_LAT], *nlon = r->col[C_N_LON];
    const uint8_t *now = r->col[C_N_ONEWAY], *npl = r->col[C_N_PLANNED], *nfl = r->col[C_N_FLAGS];

    int64_t cursor = header_end;
    for (int64_t d = 0; d < n_dc; d++) {
        int64_t tbl = 8 + d * 4;
        if (dc_count[d] == 0) {
            put16(out, tbl, 0xFFFF);
            put16(out, tbl + 2, 0);
            continue;
        }
        put16(out, tbl, (cursor / 2));
        put16(out, tbl + 2, dc_count[d] & 0xFFF);
        if (cursor + 2 > SUB_CAP) return -1;
        out[cursor] = 0;
        out[cursor + 1] = 0;
        cursor += 2;
        for (int64_t k = base[d]; k < base[d + 1]; k++) {
            int64_t i = g_order[k];
            int64_t ns = rd_i32(nst, i);
            int64_t total_len = 16 + ns * 6;
            if (cursor + total_len > SUB_CAP) return -1;
            int64_t f = rd_u16(fl, i);
            int64_t lattr = (f & 1) | (((f & 2) ? 1 : 0) << 1) | (rd_i32(p3d, i) << 2)
                | (((f & 4) ? 1 : 0) << 4) | (((f & 8) ? 1 : 0) << 6)
                | (((f & 16) ? 1 : 0) << 7) | (((f & 32) ? 1 : 0) << 8)
                | (((f & 64) ? 1 : 0) << 9) | (((f & 128) ? 1 : 0) << 10)
                | (((f & 256) ? 1 : 0) << 11) | (rd_i32(rtype, i) << 12);
            if (lattr < 0 || lattr > 0xFFFF) return -1;
            uint8_t *o = out + cursor;
            put32(o, 0, 8 | ((total_len / 2) << 16));
            put16(o, 4, ns & 0x7FF);
            put16(o, 6, 0);
            memset(o + 8, 0, 6);
            put16(o, 14, lattr);
            int64_t pos = 16;
            for (int64_t j = g_nstart[i]; j < g_nstart[i] + ns; j++) {
                /* always from lat/lon at the frame's range: the spool's n_x/n_y
                 * were computed at another range/orientation and are not read */
                int64_t x, y;
                if (to_xy(rd_f64(nlat, j), rd_f64(nlon, j), bd, &x, &y)) return -1;
                int64_t nfj = nfl[j];
                int64_t na = ((nfj & 2) ? 1 : 0) << 11 | (((nfj & 1) ? 1 : 0) << 12)
                    | (rd_i32(npl, j) << 13) | (rd_i32(now, j) << 15);
                if (na < 0 || na > 0xFFFF) return -1;
                put16(o, pos, na);
                put16(o, pos + 2, region_coord(x));
                put16(o, pos + 4, region_coord(y));
                pos += 6;
            }
            cursor += total_len;
        }
    }
    return cursor;
}

/* ---------------------------------------------------------- background */

/* Background geometry is clipped to the parcel's rectangle before rounding,
 * never clamped: a port of kiwiw/clip.py (same algorithm, same float operation
 * order; byte-identical, tests/test_cenc.py). Keep the two in step. */

enum { KO = 0, KCX = 1, KCY = 2, KCO = 3, KDE = 4 };
typedef struct { double x, y; int k; } Pt;
typedef struct { int ok; Pt a, b; } Por;

static __thread double *g_fx = NULL, *g_fy = NULL;
static __thread Por *g_por = NULL;
static __thread Pt *g_ch = NULL, *g_pc = NULL, *g_dn = NULL;
static __thread int64_t *g_cs = NULL, *g_qx = NULL, *g_qy = NULL;
static __thread int64_t g_cap_v = 0, g_cap_ch = 0, g_cap_pc = 0, g_cap_dn = 0, g_cap_qx = 0, g_cap_qy = 0;
static __thread int g_full = 0;  /* last bg_shape ran out of room */
static __thread double *g_sin = NULL, *g_sout = NULL;
static __thread char *g_used = NULL;

static int grow(void **p, int64_t *cap, int64_t n, size_t sz) {
    if (n <= *cap) return 0;
    int64_t c = *cap ? *cap : 256;
    while (c < n) c *= 2;
    void *q = realloc(*p, (size_t)c * sz);
    if (!q) return -1;
    *p = q;
    *cap = c;
    return 0;
}

static int ensure_v(int64_t n) {
    if (n <= g_cap_v) return 0;
    int64_t c = g_cap_v ? g_cap_v : 256;
    while (c < n) c *= 2;
    double *a = realloc(g_fx, (size_t)c * sizeof(double)); if (!a) return -1; g_fx = a;
    a = realloc(g_fy, (size_t)c * sizeof(double)); if (!a) return -1; g_fy = a;
    Por *p = realloc(g_por, (size_t)c * sizeof(Por)); if (!p) return -1; g_por = p;
    int64_t *s = realloc(g_cs, (size_t)(c + 1) * sizeof(int64_t)); if (!s) return -1; g_cs = s;
    a = realloc(g_sin, (size_t)c * sizeof(double)); if (!a) return -1; g_sin = a;
    a = realloc(g_sout, (size_t)c * sizeof(double)); if (!a) return -1; g_sout = a;
    char *u = realloc(g_used, (size_t)c); if (!u) return -1; g_used = u;
    g_cap_v = c;
    return 0;
}

static inline int pt_lt(double ax, double ay, double bx, double by) {
    return ax < bx || (ax == bx && ay < by);
}
static inline double clampf(double v, double lo, double hi) {
    return v < lo ? lo : v > hi ? hi : v;
}

static Pt edge_pt(double ax, double ay, double bx, double by, int edge, const double *R) {
    Pt p;
    if (pt_lt(bx, by, ax, ay)) { double t = ax; ax = bx; bx = t; t = ay; ay = by; by = t; }
    if (edge <= 2) {
        double xe = edge == 1 ? R[0] : R[2];
        p.x = xe;
        p.y = clampf(ay + (by - ay) * ((xe - ax) / (bx - ax)), R[1], R[3]);
        p.k = KCX;
    } else {
        double ye = edge == 3 ? R[1] : R[3];
        p.x = clampf(ax + (bx - ax) * ((ye - ay) / (by - ay)), R[0], R[2]);
        p.y = ye;
        p.k = KCY;
    }
    return p;
}

static Por seg(double ax, double ay, double bx, double by, const double *R) {
    Por o;
    o.ok = 0;
    double dx = bx - ax, dy = by - ay, t0 = 0.0, t1 = 1.0;
    int e0 = 0, e1 = 0;
    double P[4] = {-dx, dx, -dy, dy};
    double Q[4] = {ax - R[0], R[2] - ax, ay - R[1], R[3] - ay};
    for (int j = 0; j < 4; j++) {
        if (P[j] == 0.0) {
            if (Q[j] < 0.0) return o;
            continue;
        }
        double r = Q[j] / P[j];
        if (P[j] < 0.0) {
            if (r > t0) { t0 = r; e0 = j + 1; }
        } else if (r < t1) { t1 = r; e1 = j + 1; }
    }
    if (!(t0 < t1)) return o;
    o.ok = 1;
    if (e0) o.a = edge_pt(ax, ay, bx, by, e0, R); else { o.a.x = ax; o.a.y = ay; o.a.k = KO; }
    if (e1) o.b = edge_pt(ax, ay, bx, by, e1, R); else { o.b.x = bx; o.b.y = by; o.b.k = KO; }
    return o;
}

/* inside runs -> g_ch (flat) with starts g_cs[0..m]; returns m, *whole */
static int64_t chains(int64_t n, int closed, const double *R, int *whole) {
    int64_t nseg = closed ? n : n - 1;
    *whole = 0;
    for (int64_t i = 0; i < nseg; i++) {
        int64_t j = (i + 1) % n;
        g_por[i] = seg(g_fx[i], g_fy[i], g_fx[j], g_fy[j], R);
    }
#define JOINS(i) (g_por[i].ok && g_por[i].a.k == KO && \
    ((i) ? (g_por[(i) - 1].ok && g_por[(i) - 1].b.k == KO) \
         : (closed && nseg > 0 && g_por[nseg - 1].ok && g_por[nseg - 1].b.k == KO)))
    int64_t m = 0, np = 0;
    for (int64_t s = 0; s < nseg; s++) {
        if (!g_por[s].ok || JOINS(s)) continue;
        if (grow((void **)&g_ch, &g_cap_ch, np + nseg + 2, sizeof(Pt))) return -1;
        g_cs[m++] = np;
        g_ch[np++] = g_por[s].a;
        g_ch[np++] = g_por[s].b;
        int64_t i = closed ? (s + 1) % nseg : s + 1;
        while (i < nseg && i != s && g_por[i].ok && JOINS(i)) {
            g_ch[np++] = g_por[i].b;
            i = closed ? (i + 1) % nseg : i + 1;
        }
    }
#undef JOINS
    g_cs[m] = np;
    if (closed && m == 0) {
        int all = nseg > 0;
        for (int64_t i = 0; i < nseg; i++) all &= g_por[i].ok;
        *whole = all;
    }
    return m;
}

static double sparam(Pt p, const double *R) {
    double w = R[2] - R[0], h = R[3] - R[1];
    if (p.y == R[1]) return p.x - R[0];
    if (p.x == R[2]) return w + (p.y - R[1]);
    if (p.y == R[3]) return w + h + (R[2] - p.x);
    return 2 * w + h + (R[3] - p.y);
}

static int pip(double px, double py, int64_t n) {
    int inside = 0;
    int64_t j = n - 1;
    for (int64_t i = 0; i < n; i++) {
        if ((g_fy[i] > py) != (g_fy[j] > py)) {
            double xi = g_fx[i] + (py - g_fy[i]) / (g_fy[j] - g_fy[i]) * (g_fx[j] - g_fx[i]);
            if (px < xi) inside = !inside;
        }
        j = i;
    }
    return inside;
}

typedef struct {
    uint8_t *out;
    int64_t room, len, nrec;
    int64_t mc, mult_exp, tc, fl;
    int closed;
    const double *R;
} Emit;

/* 3-11: `pts` (pre-densify, closed) is a whole-cell/sub-cell fill -- exactly
 * `R`'s four corners, in some rotation -- iff true, with the largest
 * mult_const in {128,...,1} dividing both of R's edge lengths in *mult_out
 * (mirrors clip.py's `_rect_mult`). */
static int rect_mult_for(const Pt *pts, int64_t n, const double *R, int64_t *mult_out) {
    if (n != 4) return 0;
    double cx[4] = {R[0], R[2], R[2], R[0]}, cy[4] = {R[1], R[1], R[3], R[3]};
    int seen[4] = {0, 0, 0, 0};
    for (int64_t i = 0; i < 4; i++) {
        int matched = -1;
        for (int c = 0; c < 4; c++)
            if (pts[i].x == cx[c] && pts[i].y == cy[c]) { matched = c; break; }
        if (matched < 0 || seen[matched]) return 0;
        seen[matched] = 1;
    }
    double w = R[2] - R[0], h = R[3] - R[1];
    if (!(w > 0.0) || !(h > 0.0)) return 0;
    int64_t wi = (int64_t)w, hi = (int64_t)h;
    static const int64_t cands[8] = {128, 64, 32, 16, 8, 4, 2, 1};
    for (int i = 0; i < 8; i++)
        if (wi % cands[i] == 0 && hi % cands[i] == 0) { *mult_out = cands[i]; return 1; }
    *mult_out = 1;  /* unreachable: 1 always divides */
    return 1;
}

/* Round-clean q[0..q) already built (rect path skips densify/round since its
 * vertices are exact integers by construction); write one record at `mc`. */
static int write_record(Emit *e, const int64_t *qx, const int64_t *qy, int64_t q,
                        int64_t mc, int64_t mult_exp) {
    const double *R = e->R;
    for (int64_t i = 0; i < q; i++)
        if ((double)qx[i] < R[0] || (double)qx[i] > R[2] ||
            (double)qy[i] < R[1] || (double)qy[i] > R[3]) return -1;  /* Python asserts */
    int64_t ndl = q - 1, rec_len = 12 + ndl * 2;
    if (e->len + rec_len > e->room) { g_full = 1; return -1; }
    uint8_t *o_ = e->out + e->len;
    put16(o_, 0, (rec_len / 2) & 0xFFF);
    put16(o_, 2, ndl & 0x7FF);
    put16(o_, 4, e->tc & 0xFFFF);
    put16(o_, 6, (mult_exp & 7) | (((e->fl & 1) ? 1 : 0) << 9) | (((e->fl & 2) ? 1 : 0) << 10));
    put16(o_, 8, region_coord(qx[0]));
    put16(o_, 10, region_coord(qy[0]));
    int64_t xc = qx[0], yc = qy[0];
    for (int64_t k = 1; k < q; k++) {
        int64_t a = qx[k] - xc, b = qy[k] - yc;
        int64_t dx = a / mc, dy = b / mc;
        if ((a % mc != 0) && (a < 0)) dx--;
        if ((b % mc != 0) && (b < 0)) dy--;
        if (dx < -128) dx = -128; else if (dx > 127) dx = 127;
        if (dy < -128) dy = -128; else if (dy > 127) dy = 127;
        xc += dx * mc;
        yc += dy * mc;
        o_[12 + (k - 1) * 2] = (uint8_t)(dx & 0xFF);
        o_[12 + (k - 1) * 2 + 1] = (uint8_t)(dy & 0xFF);
    }
    e->len += rec_len;
    e->nrec++;
    return 0;
}

/* 3-11: the rectangle case -- `pts` (4 corners, CCW) split into exact
 * multiples of `mult` per edge (mirrors clip.py's `_rect_ring`/`_edge_steps`),
 * no proportional densify, no rounding (the corners are exact integers). */
static int emit_rect_piece(Emit *e, const Pt *pts, int64_t mult) {
    int64_t mult_exp = 0, mcc = 1;
    while (mcc < mult) { mcc <<= 1; mult_exp++; }
    int64_t q = 0;
    if (grow((void **)&g_qx, &g_cap_qx, q + 1, sizeof(int64_t))) return -1;
    if (grow((void **)&g_qy, &g_cap_qy, q + 1, sizeof(int64_t))) return -1;
    g_qx[q] = (int64_t)pts[0].x;
    g_qy[q] = (int64_t)pts[0].y;
    q++;
    for (int64_t i = 0; i < 4; i++) {
        int64_t ax = (int64_t)pts[i].x, ay = (int64_t)pts[i].y;
        int64_t bx = (int64_t)pts[(i + 1) % 4].x, by = (int64_t)pts[(i + 1) % 4].y;
        int64_t dx = bx - ax, dy = by - ay;
        int64_t length = dx != 0 ? (dx > 0 ? dx : -dx) : (dy > 0 ? dy : -dy);
        int64_t sx = dx > 0 ? 1 : (dx < 0 ? -1 : 0), sy = dy > 0 ? 1 : (dy < 0 ? -1 : 0);
        if (length > 0) {
            /* Evenly distribute length/mult units over k = ceil(length/(127*mult))
             * steps: k - r steps of q units, r steps of q + 1 units (mirrors
             * clip.py's _edge_steps -- dumping the whole remainder on the last
             * step, as a naive "k-1 equal + remainder" split would, can exceed
             * the 127*mult per-step cap when the remainder is large). */
            int64_t lim = 127 * mult;
            int64_t k = (length + lim - 1) / lim;  /* ceil */
            int64_t lu = length / mult;  /* exact: length is a multiple of mult */
            int64_t qu = lu / k, r = lu % k;
            int64_t x = ax, y = ay;
            for (int64_t s = 0; s < k - 1; s++) {
                int64_t units = qu + (s >= (k - r) ? 1 : 0);
                x += units * mult * sx;
                y += units * mult * sy;
                if (grow((void **)&g_qx, &g_cap_qx, q + 1, sizeof(int64_t))) return -1;
                if (grow((void **)&g_qy, &g_cap_qy, q + 1, sizeof(int64_t))) return -1;
                g_qx[q] = x; g_qy[q] = y; q++;
            }
        }
        if (grow((void **)&g_qx, &g_cap_qx, q + 1, sizeof(int64_t))) return -1;
        if (grow((void **)&g_qy, &g_cap_qy, q + 1, sizeof(int64_t))) return -1;
        g_qx[q] = bx; g_qy[q] = by; q++;
    }
    return write_record(e, g_qx, g_qy, q, mult, mult_exp);
}

/* densify + round/clean + write one record; 0 ok (possibly nothing), -1 fail */
static int emit_piece(Emit *e, const Pt *pts, int64_t n) {
    int64_t rmc;
    if (e->closed && rect_mult_for(pts, n, e->R, &rmc))
        return emit_rect_piece(e, pts, rmc);
    double lim = 127.0 * (double)e->mc - 1.0;
    int closed = e->closed;
    int64_t nseg = closed ? n : n - 1, nd = 0;
    for (int64_t i = 0; i < n; i++) {
        if (grow((void **)&g_dn, &g_cap_dn, nd + 1, sizeof(Pt))) return -1;
        Pt a = pts[i];
        g_dn[nd++] = a;
        if (i >= nseg) break;
        Pt b = pts[(i + 1) % n];
        double dx = b.x - a.x, dy = b.y - a.y;
        double mx = fabs(dx) > fabs(dy) ? fabs(dx) : fabs(dy);
        if (mx > lim) {
            double kf = ceil(mx / lim);
            if (!(kf < 1e7)) return -1;
            int64_t k = (int64_t)kf;
            if (grow((void **)&g_dn, &g_cap_dn, nd + k, sizeof(Pt))) return -1;
            for (int64_t j = 1; j < k; j++) {
                double t = (double)j / (double)k;
                g_dn[nd].x = a.x + dx * t;
                g_dn[nd].y = a.y + dy * t;
                g_dn[nd].k = KDE;
                nd++;
            }
        }
    }
    if (grow((void **)&g_qx, &g_cap_qx, nd + 1, sizeof(int64_t))) return -1;
    if (grow((void **)&g_qy, &g_cap_qy, nd + 1, sizeof(int64_t))) return -1;
    int64_t *qx = g_qx, *qy = g_qy, q = 0;
    for (int64_t i = 0; i < nd; i++) {
        double rx = rint(g_dn[i].x), ry = rint(g_dn[i].y);
        if (isnan(rx) || isnan(ry)) return -1;
        int64_t x = (int64_t)rx, y = (int64_t)ry;
        if (q && qx[q - 1] == x && qy[q - 1] == y) continue;
        qx[q] = x; qy[q] = y; q++;
    }
    if (closed) {
        while (q > 1 && qx[q - 1] == qx[0] && qy[q - 1] == qy[0]) q--;
        while (q >= 3) {
            int64_t i, found = -1;
            for (i = 0; i < q; i++) {
                int64_t a = i ? i - 1 : q - 1, c = (i + 1) % q;
                if (qx[a] == qx[c] && qy[a] == qy[c]) { found = i; break; }
            }
            if (found < 0) break;
            memmove(qx + found, qx + found + 1, (size_t)(q - found - 1) * sizeof(int64_t));
            memmove(qy + found, qy + found + 1, (size_t)(q - found - 1) * sizeof(int64_t));
            q--;
            int64_t r = found < q ? found : 0;
            memmove(qx + r, qx + r + 1, (size_t)(q - r - 1) * sizeof(int64_t));
            memmove(qy + r, qy + r + 1, (size_t)(q - r - 1) * sizeof(int64_t));
            q--;
        }
        if (q < 3) return 0;
        int64_t area2 = 0;
        for (int64_t i = 0; i < q; i++) {
            int64_t j = (i + 1) % q;
            area2 += qx[i] * qy[j] - qx[j] * qy[i];
        }
        if (area2 == 0) return 0;
        if (area2 < 0) {
            for (int64_t i = 1, j = q - 1; i < j; i++, j--) {
                int64_t t = qx[i]; qx[i] = qx[j]; qx[j] = t;
                t = qy[i]; qy[i] = qy[j]; qy[j] = t;
            }
        }
        qx[q] = qx[0]; qy[q] = qy[0]; q++;
    } else if (q < 2) {
        return 0;
    }
    return write_record(e, qx, qy, q, e->mc, e->mult_exp);
}

/* Clip one line/polygon (nc coords at lat[o + k*stride], lon[...]) to bd's
 * rectangle and write its records to out. Returns bytes written (>= 0) and
 * *nrec; -1 on anything odd (the caller defers to Python). */
static int64_t bg_shape(const uint8_t *lat, const uint8_t *lon, int64_t o, int64_t stride,
                        int64_t nc, int closed, int64_t mc, int64_t tc, int64_t fl,
                        const Bounds *bd, uint8_t *out, int64_t room, int64_t *nrec) {
    *nrec = 0;
    g_full = 0;
    if (nc < 1) return -1;
    if (mc < 1) mc = 1;
    if (mc > ((int64_t)1 << 40)) return -1;
    if (ensure_v(nc + 1)) return -1;
    Emit e = {out, room, 0, 0, mc, 0, tc, fl, closed, bd->rect};
    int64_t mcc = 1;
    while (mcc < mc) { mcc <<= 1; e.mult_exp++; }
    double dlon = bd->lon_hi - bd->lon_lo, dlat = bd->lat_hi - bd->lat_lo;
    int64_t n = nc;
    for (int64_t k = 0; k < n; k++) {
        g_fx[k] = (rd_f64(lon, o + k * stride) - bd->lon_lo) / dlon * bd->range;
        g_fy[k] = (rd_f64(lat, o + k * stride) - bd->lat_lo) / dlat * bd->range;
        if (isnan(g_fx[k]) || isnan(g_fy[k])) return -1;
    }
    const double *R = bd->rect;
    if (closed) {
        if (n > 1 && g_fx[n - 1] == g_fx[0] && g_fy[n - 1] == g_fy[0]) n--;
        double a2 = 0.0;
        for (int64_t i = 0; i < n; i++) {
            int64_t j = (i + 1) % n;
            a2 += g_fx[i] * g_fy[j] - g_fx[j] * g_fy[i];
        }
        if (a2 < 0.0) {
            for (int64_t i = 1, j = n - 1; i < j; i++, j--) {
                double t = g_fx[i]; g_fx[i] = g_fx[j]; g_fx[j] = t;
                t = g_fy[i]; g_fy[i] = g_fy[j]; g_fy[j] = t;
            }
        }
    }
    if ((closed && n < 3) || n < 2) return 0;
    int inside = 1;
    for (int64_t i = 0; i < n && inside; i++)
        inside = R[0] <= g_fx[i] && g_fx[i] <= R[2] && R[1] <= g_fy[i] && g_fy[i] <= R[3];
    if (inside) {
        if (grow((void **)&g_pc, &g_cap_pc, n, sizeof(Pt))) return -1;
        for (int64_t i = 0; i < n; i++) { g_pc[i].x = g_fx[i]; g_pc[i].y = g_fy[i]; g_pc[i].k = KO; }
        if (emit_piece(&e, g_pc, n)) return -1;
        *nrec = e.nrec;
        return e.len;
    }
    int whole;
    int64_t m = chains(n, closed, R, &whole);
    if (m < 0) return -1;
    if (!closed) {
        for (int64_t c = 0; c < m; c++)
            if (emit_piece(&e, g_ch + g_cs[c], g_cs[c + 1] - g_cs[c])) return -1;
        *nrec = e.nrec;
        return e.len;
    }
    Pt corners[4] = {{R[0], R[1], KCO}, {R[2], R[1], KCO}, {R[2], R[3], KCO}, {R[0], R[3], KCO}};
    if (whole) {
        if (grow((void **)&g_pc, &g_cap_pc, n, sizeof(Pt))) return -1;
        for (int64_t i = 0; i < n; i++) { g_pc[i].x = g_fx[i]; g_pc[i].y = g_fy[i]; g_pc[i].k = KO; }
        if (emit_piece(&e, g_pc, n)) return -1;
    } else if (m == 0) {
        double cx = (R[0] + R[2]) * 0.5, cy = (R[1] + R[3]) * 0.5;
        if (pip(cx, cy, n) && emit_piece(&e, corners, 4)) return -1;
    } else {
        double w = R[2] - R[0], h = R[3] - R[1], per = 2.0 * (w + h);
        double cs[4] = {0.0, w, w + h, 2 * w + h};
        for (int64_t c = 0; c < m; c++) {
            g_sin[c] = sparam(g_ch[g_cs[c]], R);
            g_sout[c] = sparam(g_ch[g_cs[c + 1] - 1], R);
            g_used[c] = 0;
        }
        for (int64_t c0 = 0; c0 < m; c0++) {
            if (g_used[c0]) continue;
            int64_t np = 0, c = c0;
            for (int64_t guard = 0; guard < m + 1; guard++) {
                g_used[c] = 1;
                int64_t len = g_cs[c + 1] - g_cs[c];
                if (grow((void **)&g_pc, &g_cap_pc, np + len + 4, sizeof(Pt))) return -1;
                memcpy(g_pc + np, g_ch + g_cs[c], (size_t)len * sizeof(Pt));
                np += len;
                double sx = g_sout[c], bd_ = 0.0;
                int64_t best = -1;
                for (int64_t k = 0; k < m; k++) {
                    double d = g_sin[k] - sx;
                    if (d < 0.0) d += per;
                    if (best < 0 || d < bd_) { best = k; bd_ = d; }
                }
                double dcs[4];
                int idx[4], ni = 0;
                for (int ci = 0; ci < 4; ci++) {
                    double dc = cs[ci] - sx;
                    if (dc < 0.0) dc += per;
                    if (0.0 < dc && dc < bd_) {
                        int j = ni++;  /* insertion sort by (dc, ci) */
                        while (j > 0 && (dcs[j - 1] > dc)) { dcs[j] = dcs[j - 1]; idx[j] = idx[j - 1]; j--; }
                        dcs[j] = dc; idx[j] = ci;
                    }
                }
                for (int j = 0; j < ni; j++) g_pc[np++] = corners[idx[j]];
                if (best == c0 || g_used[best]) break;
                c = best;
            }
            if (emit_piece(&e, g_pc, np)) return -1;
        }
    }
    *nrec = e.nrec;
    return e.len;
}

/* Python entry: interleaved (lat, lon) doubles, b4 = lat_lo,lat_hi,lon_lo,lon_hi,
 * rect4 = clip rectangle (x0,y0,x1,y1) or NULL for [0, range]^2. Writes the
 * shape's records back to back; returns their total length (*nrec records),
 * -2 when `room` is too small, -1 otherwise (the caller uses the oracle). */
int64_t kw_bg_shape(const double *latlon, int64_t n, int64_t mult, int64_t type_code,
                    int64_t flags, int closed, const double *b4, const double *rect4,
                    uint8_t *out, int64_t room, double coord_range, int64_t *nrec) {
    Bounds bd = {b4[0], b4[1], b4[2], b4[3], coord_range, coord_range,
                 {0.0, 0.0, coord_range, coord_range}};
    if (rect4) memcpy(bd.rect, rect4, sizeof bd.rect);
    int64_t r = bg_shape((const uint8_t *)latlon, (const uint8_t *)(latlon + 1), 0, 2, n,
                         closed, mult, type_code, flags, &bd, out, room, nrec);
    return r < 0 && g_full ? -2 : r;
}

static int64_t enc_bg(const Rec *r, const Bounds *bd, uint8_t *out) {
    int64_t nb = r->cnt[K_NB];
    const uint8_t *cls = r->col[C_B_CLASS], *typ = r->col[C_B_TYPE], *mult = r->col[C_B_MULT];
    const uint8_t *bfl = r->col[C_B_FLAGS], *nst = r->col[C_B_NST];
    const uint8_t *clat = r->col[C_C_LAT], *clon = r->col[C_C_LON];
    int64_t class_in[4] = {0, 0, 0, 0}, class_n[4] = {0, 0, 0, 0};
    for (int64_t i = 0; i < nb; i++) {
        int64_t c = rd_i32(cls, i);
        if (c < 0 || c > 3) return -1;
        class_in[c]++;
    }
    /* records are written after a unit table sized for every input class;
     * classes clipped away entirely are squeezed out afterwards */
    int64_t n_in = 0;
    for (int c = 0; c < 4; c++) n_in += class_in[c] > 0;
    int64_t unit_off = 6;
    int64_t rec0 = unit_off + 2 + n_in * 4;
    int64_t p = rec0;
    if (p > SUB_CAP) return -1;
    int64_t *cstart = nb ? (int64_t *)malloc((size_t)nb * sizeof(int64_t)) : NULL;
    if (nb && !cstart) return -1;
    int64_t ci = 0;
    for (int64_t i = 0; i < nb; i++) {
        cstart[i] = ci;
        ci += rd_i32(nst, i);
        if (ci > r->cnt[K_NC]) { free(cstart); return -1; }
    }
    for (int c = 0; c < 4; c++) {
        if (!class_in[c]) continue;
        for (int64_t i = 0; i < nb; i++) {
            if (rd_i32(cls, i) != c) continue;
            int64_t tc = rd_i32(typ, i);
            int64_t fl = bfl[i];
            if (c == 0) {
                if (p + 12 > SUB_CAP) { free(cstart); return -1; }
                memset(out + p, 0, 12);
                put16(out, p, 6);
                put16(out, p + 4, tc & 0xFFFF);
                p += 12;
                class_n[c]++;
                continue;
            }
            int64_t nrec;
            int64_t len = bg_shape(clat, clon, cstart[i], 1, rd_i32(nst, i), c == 2,
                                   rd_i32(mult, i), tc, fl, bd, out + p, SUB_CAP - p, &nrec);
            if (len < 0) { free(cstart); return -1; }
            p += len;
            class_n[c] += nrec;
        }
    }
    free(cstart);
    int64_t n_units = 0;
    for (int c = 0; c < 4; c++) n_units += class_n[c] > 0;
    if (n_units == 0) {
        out[0] = 0;
        out[1] = 1;
        return 2;
    }
    if (n_units < n_in) {
        int64_t shift = (n_in - n_units) * 4;
        memmove(out + rec0 - shift, out + rec0, (size_t)(p - rec0));
        p -= shift;
    }
    int64_t esz = p - 6;
    out[0] = 0;
    out[1] = 3;
    put16(out, 2, 3);
    put16(out, 4, (esz + (esz & 1)) / 2);
    put16(out, unit_off, n_units);
    int64_t q = unit_off + 2;
    for (int c = 0; c < 4; c++) {
        if (!class_n[c]) continue;
        put16(out, q, 0);
        put16(out, q + 2, (class_n[c] & 0xFFF) | ((int64_t)c << 14));
        q += 4;
    }
    if (p & 1) { if (p + 1 > SUB_CAP) return -1; out[p++] = 0; }
    return p;
}

/* ---------------------------------------------------------------- names */

/* strict UTF-8 -> latin-1 with '?' for chars > 0xFF; appends to o. Returns
 * bytes written or -1 (invalid UTF-8 / overflow). */
static int64_t text_latin1(const uint8_t *s, int64_t n, uint8_t *o, int64_t room) {
    int64_t w = 0;
    for (int64_t i = 0; i < n;) {
        uint32_t c = s[i];
        int len;
        if (c < 0x80) { len = 1; }
        else if (c >= 0xC2 && c <= 0xDF) { len = 2; c &= 0x1F; }
        else if (c >= 0xE0 && c <= 0xEF) { len = 3; c &= 0x0F; }
        else if (c >= 0xF0 && c <= 0xF4) { len = 4; c &= 0x07; }
        else return -1;
        if (i + len > n) return -1;
        for (int k = 1; k < len; k++) {
            if ((s[i + k] & 0xC0) != 0x80) return -1;
            c = (c << 6) | (s[i + k] & 0x3F);
        }
        if ((len == 3 && c < 0x800) || (len == 4 && (c < 0x10000 || c > 0x10FFFF))
            || (c >= 0xD800 && c <= 0xDFFF)) return -1;
        if (w >= room) return -1;
        o[w++] = c < 256 ? (uint8_t)c : '?';
        i += len;
    }
    return w;
}

static int64_t enc_names(const Rec *r, int level, const Bounds *bd, uint8_t *out,
                         int *any_names) {
    int64_t ns = r->cnt[K_NS];
    *any_names = ns > 0;
    if (ns == 0) return 0;
    const uint8_t *st = r->col[C_S_TYPE], *sc = r->col[C_S_CODE], *sp = r->col[C_S_PRIO];
    const uint8_t *sd = r->col[C_S_DSF], *sa = r->col[C_S_ANGF], *sv = r->col[C_S_VERT];
    const uint8_t *spr = r->col[C_S_PRES], *sll = r->col[C_S_LLEN], *stl = r->col[C_S_TLEN];
    const uint8_t *slat = r->col[C_S_LAT], *slon = r->col[C_S_LON], *sang = r->col[C_S_ANGLE];
    const uint8_t *tblob = r->col[C_BLOB_NT];
    int64_t tblob_n = r->cnt[K_NT];
    int64_t p = 6, count = 0, to = 0;
    for (int64_t i = 0; i < ns; i++) {
        int64_t typ = rd_i32(st, i), tl = rd_i32(stl, i);
        int64_t t0 = to;
        to += tl;
        if (tl < 0 || to > tblob_n) return -1;
        int allowed = level == 0 ? (typ == 5 || typ == 6) : (typ == 1 || typ == 5);
        if (!allowed) continue;
        int64_t pres = spr[i];
        int64_t xc = 0, yc = 0;
        if ((pres & 1) && (pres & 2)) {
            if (to_xy(rd_f64(slat, i), rd_f64(slon, i), bd, &xc, &yc)) return -1;
        }
        int64_t sx = region_coord(xc), sy = region_coord(yc);
        int64_t rec_start = p;
        if (p + 6 + 8 + 2 > SUB_CAP) return -1;
        /* body layout by type; text goes after the fixed prefix */
        int64_t text_at;
        if (typ == 1) {
            text_at = p + 6 + 8;
        } else {
            text_at = p + 6 + 6 + 2 + 2;
        }
        int64_t room = SUB_CAP - text_at - 2;
        if (room < 0) return -1;
        int64_t w = text_latin1(tblob + t0, tl, out + text_at, room);
        if (w < 0) return -1;
        if (typ == 1) {
            out[text_at + w++] = 0;          /* always-NUL terminator */
            if (w & 1) out[text_at + w++] = 0;
        } else if (w & 1) {
            out[text_at + w++] = 0;
        }
        int64_t slen_word = w / 2;
        if (slen_word > 0xFFFF) return -1;
        int64_t body = typ == 1 ? 8 + w : 6 + 2 + 2 + w;
        int64_t reclen = 6 + body;
        if (reclen / 2 > 0xFFFF) return -1;
        int64_t attr1 = (rd_i32(sp, i) & 0x3F) | (((int64_t)(sv[i] != 0)) << 6)
            | ((typ & 7) << 8) | ((rd_i32(sd, i) & 0x1F) << 11);
        put16(out, rec_start, reclen / 2);
        put16(out, rec_start + 2, attr1);
        put16(out, rec_start + 4, rd_i32(sc, i) & 0xFFFF);
        int64_t b = rec_start + 6;
        put16(out, b, 0);
        put16(out, b + 2, sx);
        put16(out, b + 4, sy);
        if (typ == 1) {
            put16(out, b + 6, slen_word);
        } else if (typ == 5) {
            double ang = (pres & 4) ? rd_f64(sang, i) : 0.0;
            if (isnan(ang) || fabs(ang) > 1e15) return -1;
            int64_t low9 = ((int64_t)rint(ang) + 90) & 0x1FF;
            put16(out, b + 6, ((rd_i32(sa, i) & 0x7F) << 9) | low9);
            put16(out, b + 8, slen_word);
        } else {
            put16(out, b + 6, 0x8000);
            put16(out, b + 8, slen_word);
        }
        p = rec_start + reclen;
        count++;
    }
    if (count == 0) {
        out[0] = 0;
        out[1] = 1;
        return 2;
    }
    out[0] = 0;
    out[1] = 3;
    put16(out, 2, 3);
    put16(out, 4, count);
    if (p & 1) out[p++] = 0;
    return p;
}

/* ------------------------------------------------------------ map frame */

static __thread uint8_t *g_sub = NULL; /* 3 * SUB_CAP */

/* parcel_bounds() */
static double norm_lon(double v) {
    while (v > 360) v -= 360;
    while (v < -180) v += 360;
    return v;
}

int kw_bounds(int64_t ix, int64_t iy, double dlat, double dlon, double cell_lat,
              double cell_lon, double *out4) {
    double lat_lo = dlat + (double)iy * cell_lat;
    double lat_hi = lat_lo + cell_lat;
    double lon_lo_raw = dlon + (double)ix * cell_lon;
    double lon_hi_raw = lon_lo_raw + cell_lon;
    out4[0] = lat_lo;
    out4[1] = lat_hi;
    out4[2] = norm_lon(lon_lo_raw);
    out4[3] = norm_lon(lon_hi_raw);
    return 0;
}

static int geo3(double deg, uint8_t *o) {
    double u = rint(fabs(deg) * 3600.0 * 8);
    if (isnan(u) || u >= 8388608.0) return -1;
    int64_t units = (int64_t)u;
    if (deg < 0) units |= 1 << 23;
    o[0] = (uint8_t)((units >> 16) & 0xFF);
    o[1] = (uint8_t)((units >> 8) & 0xFF);
    o[2] = (uint8_t)(units & 0xFF);
    return 0;
}

/*
 * rec == NULL / rec_len == 0: an empty (mask-filled) cell.
 * grid = {disc_lat_lo, disc_lon_lo, cell_lat, cell_lon}
 * lim  = {road, background, name} per-kind byte budgets (INT64_MAX = none)
 * Returns frame length written to out (capacity >= SUB_CAP), or -1.
 */
static int64_t encode_common(const uint8_t *rec, int64_t rec_len, int level, int64_t ix,
                       int64_t iy, const double *grid, int64_t threshold,
                       const int64_t *lim, uint8_t *out, int64_t *sizes_out,
                       const double *xb, const double *xrect, double coord_range) {
    Rec r;
    static const uint8_t empty_hdr[72] = {0};
    if (rec == NULL || rec_len == 0) {
        rec = empty_hdr;
        rec_len = 72;
    }
    if (parse_rec(rec, rec_len, &r)) return -1;
    if (!g_sub) {
        g_sub = malloc((size_t)3 * SUB_CAP);
        if (!g_sub) return -1;
    }
    Bounds bd;
    double b4[4];
    if (grid) kw_bounds(ix, iy, grid[0], grid[1], grid[2], grid[3], b4);
    else memcpy(b4, xb, sizeof b4);
    bd.lat_lo = b4[0]; bd.lat_hi = b4[1]; bd.lon_lo = b4[2]; bd.lon_hi = b4[3];
    bd.range = coord_range;
    bd.cmax = coord_range;
    if (xrect) memcpy(bd.rect, xrect, sizeof bd.rect);
    else { bd.rect[0] = 0.0; bd.rect[1] = 0.0; bd.rect[2] = coord_range; bd.rect[3] = coord_range; }

    uint8_t *road = g_sub, *bg = g_sub + SUB_CAP, *nm = g_sub + 2 * SUB_CAP;
    int64_t road_n = 0, bg_n, name_n;
    if (r.cnt[K_NR] > 0) {
        road_n = enc_road(&r, &bd, road);
        if (road_n < 0) return -1;
    }
    bg_n = enc_bg(&r, &bd, bg);
    if (bg_n < 0) return -1;
    int any;
    name_n = enc_names(&r, level, &bd, nm, &any);
    if (name_n < 0) return -1;

    if (road_n > MAX_FRAME || bg_n > MAX_FRAME || name_n > MAX_FRAME) return -1;
    if (lim && (road_n > lim[0] || bg_n > lim[1] || name_n > lim[2])) return -1;

    int mfde_len = level == 12 ? 12 : 20;
    int dup = level >= 6 && name_n > 0;
    int64_t first = 36 + (int64_t)mfde_len * 6;
    int64_t total = first + road_n + bg_n + name_n + (dup ? name_n : 0);
    if ((lim && total > threshold) || total > MAX_FRAME) return -1;
    if (sizes_out) { sizes_out[0] = road_n; sizes_out[1] = bg_n; sizes_out[2] = name_n; }

    memset(out, 0, (size_t)total);
    put16(out, 0, total / 2);
    if (geo3(bd.lat_lo, out + 2)) return -1;
    out[5] = 0;
    if (geo3(bd.lon_lo, out + 6)) return -1;
    out[9] = 0;
    out[10] = (uint8_t)(iy % 256);
    out[11] = (uint8_t)(ix % 256);
    put16(out, 18, 0x0064);
    put32(out, 28, 0xFFFFFFFFLL);
    for (int i = 0; i < mfde_len; i++) {
        put32(out, 36 + i * 6, 0xFFFFFFFFLL);
        put16(out, 36 + i * 6 + 4, 0);
    }
    int64_t cur = first;
    int64_t sizes[3] = {road_n, bg_n, name_n};
    const uint8_t *srcs[3] = {road, bg, nm};
    for (int i = 0; i < 3; i++) {
        if (!sizes[i]) continue;
        put32(out, 36 + i * 6, cur / 2);
        put16(out, 36 + i * 6 + 4, sizes[i] / 2);
        memcpy(out + cur, srcs[i], (size_t)sizes[i]);
        cur += sizes[i];
    }
    if (dup) {
        put32(out, 36 + 10 * 6, cur / 2);
        put16(out, 36 + 10 * 6 + 4, name_n / 2);
        memcpy(out + cur, nm, (size_t)name_n);
        cur += name_n;
    }
    return cur;
}

int64_t kw_encode_cell(const uint8_t *rec, int64_t rec_len, int level, int64_t ix,
                       int64_t iy, const double *grid, int64_t threshold,
                       const int64_t *lim, uint8_t *out, double coord_range) {
    return encode_common(rec, rec_len, level, ix, iy, grid, threshold, lim, out, NULL, NULL,
                         NULL, coord_range);
}

/* Probe: frame + per-kind (even-padded) sizes, no fit/budget checks. -1 = ask Python. */
int64_t kw_measure_cell(const uint8_t *rec, int64_t rec_len, int level, int64_t ix,
                        int64_t iy, const double *bounds4, const double *rect4,
                        int64_t *sizes, uint8_t *out, double coord_range) {
    return encode_common(rec, rec_len, level, ix, iy, NULL, 0, NULL, out, sizes, bounds4,
                         rect4, coord_range);
}

/*
 * Assembly helpers (plan 02 step 3): GIL-free bulk file copy.
 *
 * kw_copy_frames: for i in [0, n): pread len[i] bytes at src_off[i] from
 * src_fds[fid[i]], zero-pad to pad[i], pwrite at dst_off[i] into out_fd.
 * Returns 0, or -(i+1) for the first failing item.
 */
static int full_pread(int fd, uint8_t *b, size_t n, uint64_t off) {
    while (n) {
        ssize_t r = pread(fd, b, n, (off_t)off);
        if (r <= 0) return -1;
        b += r; n -= (size_t)r; off += (uint64_t)r;
    }
    return 0;
}

static int full_pwrite(int fd, const uint8_t *b, size_t n, uint64_t off) {
    while (n) {
        ssize_t r = pwrite(fd, b, n, (off_t)off);
        if (r <= 0) return -1;
        b += r; n -= (size_t)r; off += (uint64_t)r;
    }
    return 0;
}

int64_t kw_copy_frames(int out_fd, int64_t n, const int *src_fds, const uint16_t *fid,
                       const uint64_t *src_off, const uint64_t *dst_off,
                       const uint32_t *len, const uint32_t *pad, int64_t bufcap) {
    uint8_t *buf = (uint8_t *)malloc((size_t)bufcap);
    if (!buf) return -1;
    for (int64_t i = 0; i < n; i++) {
        if ((int64_t)pad[i] > bufcap || pad[i] < len[i]) { free(buf); return -(i + 1); }
        if (full_pread(src_fds[fid[i]], buf, len[i], src_off[i]) ||
            (memset(buf + len[i], 0, pad[i] - len[i]), 0) ||
            full_pwrite(out_fd, buf, pad[i], dst_off[i])) { free(buf); return -(i + 1); }
    }
    free(buf);
    return 0;
}

/* kw_write_rows: pwrite n fixed-size rows (src + i*stride, len bytes) at dst_off[i]. */
int64_t kw_write_rows(int out_fd, int64_t n, const uint64_t *dst_off, const uint8_t *src,
                      int64_t stride, int64_t len) {
    for (int64_t i = 0; i < n; i++)
        if (full_pwrite(out_fd, src + i * stride, (size_t)len, dst_off[i])) return -(i + 1);
    return 0;
}
