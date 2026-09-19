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

#define COORD_RANGE 32768.0
#define COORD_MAX 32767
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

typedef struct { double lat_lo, lat_hi, lon_lo, lon_hi; } Bounds;

/* latlon_to_xy + _clamp_coord: 0 ok, -1 not representable (NaN). */
static inline int to_xy(double lat, double lon, const Bounds *b, int64_t *x, int64_t *y) {
    double fx = rint((lon - b->lon_lo) / (b->lon_hi - b->lon_lo) * COORD_RANGE);
    double fy = rint((b->lat_hi - lat) / (b->lat_hi - b->lat_lo) * COORD_RANGE);
    if (isnan(fx) || isnan(fy)) return -1;
    *x = fx < 0 ? 0 : fx > COORD_MAX ? COORD_MAX : (int64_t)fx;
    *y = fy < 0 ? 0 : fy > COORD_MAX ? COORD_MAX : (int64_t)fy;
    return 0;
}

static inline int64_t region_coord(int64_t v) { /* encode_region_coord */
    return (v % 4096) | ((v / 4096) << 13);
}

static inline int64_t clampc(int64_t v) {
    return v < 0 ? 0 : v > COORD_MAX ? COORD_MAX : v;
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
    const uint8_t *nx = r->col[C_N_X], *ny = r->col[C_N_Y];
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
                int64_t x = rd_i32(nx, j), y = rd_i32(ny, j);
                if (x != 0 || y != 0) {
                    x = clampc(x);
                    y = clampc(y);
                } else if (to_xy(rd_f64(nlat, j), rd_f64(nlon, j), bd, &x, &y)) {
                    return -1;
                }
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

/* One line/polygon shape record (12 + 2*(nc-1) bytes) from nc coords at
 * lat[o + k*stride], lon[o + k*stride] (element indices). -1 on anything odd. */
static int64_t bg_shape(const uint8_t *lat, const uint8_t *lon, int64_t o, int64_t stride,
                        int64_t nc, int64_t mc, int64_t tc, int64_t fl, const Bounds *bd,
                        uint8_t *o_, int64_t room) {
    if (nc < 1) return -1;
    if (mc < 1) mc = 1;
    if (mc > ((int64_t)1 << 40)) return -1;
    int64_t mult_exp = 0, mcc = 1;
    while (mcc < mc) { mcc <<= 1; mult_exp++; }
    int64_t nd = nc - 1;
    int64_t rec_len = 12 + nd * 2;
    if (rec_len > room) return -1;
    int64_t x0, y0;
    if (to_xy(rd_f64(lat, o), rd_f64(lon, o), bd, &x0, &y0)) return -1;
    put16(o_, 0, (rec_len / 2) & 0xFFF);
    put16(o_, 2, nd & 0x7FF);
    put16(o_, 4, tc & 0xFFFF);
    int64_t addl = (mult_exp & 7) | (((fl & 1) ? 1 : 0) << 9) | (((fl & 2) ? 1 : 0) << 10);
    put16(o_, 6, addl);
    put16(o_, 8, region_coord(x0));
    put16(o_, 10, region_coord(y0));
    int64_t xc = x0, yc = y0;
    for (int64_t k = 1; k <= nd; k++) {
        int64_t xi, yi;
        if (to_xy(rd_f64(lat, o + k * stride), rd_f64(lon, o + k * stride), bd, &xi, &yi))
            return -1;
        int64_t a = xi - xc, b = yi - yc;
        int64_t dx = a / mc, dy = b / mc;
        if ((a % mc != 0) && (a < 0)) dx--;
        if ((b % mc != 0) && (b < 0)) dy--;
        if (dx < -128) dx = -128; else if (dx > 127) dx = 127;
        if (dy < -128) dy = -128; else if (dy > 127) dy = 127;
        xc = clampc(xc + dx * mc);
        yc = clampc(yc + dy * mc);
        o_[12 + (k - 1) * 2] = (uint8_t)(dx & 0xFF);
        o_[12 + (k - 1) * 2 + 1] = (uint8_t)(dy & 0xFF);
    }
    return rec_len;
}

/* Python entry: interleaved (lat, lon) doubles, bounds = lat_lo,lat_hi,lon_lo,lon_hi.
 * Returns the record length or -1 (caller falls back to the scalar oracle). */
int64_t kw_bg_shape(const double *latlon, int64_t n, int64_t mult, int64_t type_code,
                    int64_t flags, const double *b4, uint8_t *out) {
    Bounds bd = {b4[0], b4[1], b4[2], b4[3]};
    if (n < 2) return -1;
    return bg_shape((const uint8_t *)latlon, (const uint8_t *)(latlon + 1), 0, 2, n, mult,
                    type_code, flags, &bd, out, 12 + 2 * 2047 + 2);
}

static int64_t enc_bg(const Rec *r, const Bounds *bd, uint8_t *out) {
    int64_t nb = r->cnt[K_NB];
    if (nb == 0) {
        out[0] = 0;
        out[1] = 1;
        return 2;
    }
    const uint8_t *cls = r->col[C_B_CLASS], *typ = r->col[C_B_TYPE], *mult = r->col[C_B_MULT];
    const uint8_t *bfl = r->col[C_B_FLAGS], *nst = r->col[C_B_NST];
    const uint8_t *clat = r->col[C_C_LAT], *clon = r->col[C_C_LON];
    int64_t class_n[4] = {0, 0, 0, 0};
    for (int64_t i = 0; i < nb; i++) {
        int64_t c = rd_i32(cls, i);
        if (c < 0 || c > 3) return -1;
        class_n[c]++;
    }
    int64_t n_units = 0;
    for (int c = 0; c < 4; c++) n_units += class_n[c] > 0;
    int64_t p = 6;
    /* element section: n_units word, then unit table; filled after records */
    int64_t unit_off = p;
    p += 2 + n_units * 4;
    if (p > SUB_CAP) return -1;
    const Bounds bd_local = *bd;
    /* per-shape coord start offsets need a prefix pass */
    int64_t *cstart = (int64_t *)malloc((size_t)nb * sizeof(int64_t));
    if (!cstart) return -1;
    int64_t ci = 0;
    for (int64_t i = 0; i < nb; i++) {
        cstart[i] = ci;
        ci += rd_i32(nst, i);
        if (ci > r->cnt[K_NC]) { free(cstart); return -1; }
    }
    for (int c = 0; c < 4; c++) {
        if (!class_n[c]) continue;
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
                continue;
            }
            int64_t nc = rd_i32(nst, i);
            int64_t rec_len = bg_shape(clat, clon, cstart[i], 1, nc, rd_i32(mult, i), tc,
                                       fl, &bd_local, out + p, SUB_CAP - p);
            if (rec_len < 0) { free(cstart); return -1; }
            p += rec_len;
        }
    }
    free(cstart);
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
int64_t kw_encode_cell(const uint8_t *rec, int64_t rec_len, int level, int64_t ix,
                       int64_t iy, const double *grid, int64_t threshold,
                       const int64_t *lim, uint8_t *out) {
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
    kw_bounds(ix, iy, grid[0], grid[1], grid[2], grid[3], b4);
    bd.lat_lo = b4[0]; bd.lat_hi = b4[1]; bd.lon_lo = b4[2]; bd.lon_hi = b4[3];

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
    if (road_n > lim[0] || bg_n > lim[1] || name_n > lim[2]) return -1;

    int mfde_len = level == 12 ? 12 : 20;
    int dup = level >= 6 && name_n > 0;
    int64_t first = 36 + (int64_t)mfde_len * 6;
    int64_t total = first + road_n + bg_n + name_n + (dup ? name_n : 0);
    if (total > threshold || total > MAX_FRAME) return -1;

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
