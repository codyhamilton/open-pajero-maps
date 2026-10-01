/* D1 -- C frame decoders (plan 04, Phase 2, brief 2-01). See `_d1.h` for the
 * row layouts, offset conventions, status codes and return values.
 *
 * One call per range of leaf frames (`kw_d1_frames`): it decodes the Map
 * Frame header and directory, the road, background and name sub-frames of
 * every leaf, exactly as `parcel.decode_parcel` + `road.py`/`background.py`/
 * `name.py` do, into columnar rows in caller-provided buffers. No allocation,
 * no callbacks, no Python objects. Rows past a table's capacity are counted,
 * not written (the `e1` grow-and-repeat pattern), so the stats array always
 * carries the exact rows needed.
 *
 * Python's reads are `buf[i]` (IndexError past the sub-frame's end) and
 * slices (silently clipped); NEED() mirrors the first, clipped lengths the
 * second, so the set of frames this fails on is exactly the set Python raises
 * on. lat/lon use `coordconv.xy_to_latlon`'s operation order (built with
 * -ffp-contract=off) and are bit-identical to it. */
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "_d1.h"

/* ------------------------------------------------------------------ layout */

typedef struct { const char *name, *kind; int off, size; } d1_fspec;
#define D1_SPEC(S, T, N) {#N, #T, (int)offsetof(S, N), (int)sizeof(d1_##T)},
#define D1_SPECS(NAME, S) static const d1_fspec spec_##NAME[] = { D1_F_##NAME(D1_SPEC, S) };
D1_SPECS(LEAF, d1_leaf) D1_SPECS(FRAME, d1_frame) D1_SPECS(MFDE, d1_mfde)
D1_SPECS(DCLASS, d1_dclass) D1_SPECS(ADDL, d1_addl) D1_SPECS(LINK, d1_link)
D1_SPECS(NODE, d1_node) D1_SPECS(POINT, d1_point) D1_SPECS(BGELEM, d1_bgelem)
D1_SPECS(BGUNIT, d1_bgunit) D1_SPECS(BGSHAPE, d1_bgshape) D1_SPECS(BGCOORD, d1_bgcoord)
D1_SPECS(NLIST, d1_nlist) D1_SPECS(NREC, d1_nrec) D1_SPECS(WALK, d1_walk)
D1_SPECS(BLOCK, d1_block)

#define D1_TAB(NAME, S, STR) {STR, sizeof(S), sizeof(spec_##NAME) / sizeof(spec_##NAME[0]), spec_##NAME}
static const struct { const char *name; int size, nf; const d1_fspec *f; } TABS[D1_NTABLES] = {
    D1_TAB(LEAF, d1_leaf, "leaf"), D1_TAB(FRAME, d1_frame, "frame"),
    D1_TAB(MFDE, d1_mfde, "mfde"), D1_TAB(DCLASS, d1_dclass, "dclass"),
    D1_TAB(ADDL, d1_addl, "addl"), D1_TAB(LINK, d1_link, "link"),
    D1_TAB(NODE, d1_node, "node"), D1_TAB(POINT, d1_point, "point"),
    D1_TAB(BGELEM, d1_bgelem, "bgelem"), D1_TAB(BGUNIT, d1_bgunit, "bgunit"),
    D1_TAB(BGSHAPE, d1_bgshape, "bgshape"), D1_TAB(BGCOORD, d1_bgcoord, "bgcoord"),
    D1_TAB(NLIST, d1_nlist, "nlist"), D1_TAB(NREC, d1_nrec, "nrec"),
    D1_TAB(WALK, d1_walk, "walk"), D1_TAB(BLOCK, d1_block, "block"),
};
#define D1_NOUT (D1_T_WALK + 1)           /* output tables 1..D1_T_WALK; slot 0 unused */

int kw_d1_ntables(void) { return D1_NTABLES; }
const char *kw_d1_table_name(int t) { return t >= 0 && t < D1_NTABLES ? TABS[t].name : NULL; }
int kw_d1_row_size(int t) { return t >= 0 && t < D1_NTABLES ? TABS[t].size : -1; }
int kw_d1_nfields(int t) { return t >= 0 && t < D1_NTABLES ? TABS[t].nf : -1; }
const char *kw_d1_field_name(int t, int i) { return TABS[t].f[i].name; }
const char *kw_d1_field_kind(int t, int i) { return TABS[t].f[i].kind; }
int kw_d1_field_off(int t, int i) { return TABS[t].f[i].off; }

/* ----------------------------------------------------------------- context */

typedef struct {
    uint8_t *base[D1_NTABLES];
    int64_t cap[D1_NTABLES], n[D1_NTABLES];
    uint64_t scratch[64];                 /* 512 bytes: the sink for rows past capacity */
} d1_ctx;

#define D1_ROW_MAX 512
_Static_assert(sizeof(d1_frame) <= D1_ROW_MAX && sizeof(d1_link) <= D1_ROW_MAX &&
               sizeof(d1_nrec) <= D1_ROW_MAX, "scratch row too small");

/* Append a zero-padded copy of `src` (a fully initialised local row) to table t. */
static void put(d1_ctx *c, int t, const void *src) {
    int64_t i = c->n[t]++;
    if (i < c->cap[t]) memcpy(c->base[t] + (size_t)i * TABS[t].size, src, TABS[t].size);
}

#define ZERO(v) memset(&(v), 0, sizeof(v))

/* ------------------------------------------------------------ byte readers */

#define D1_ERR 1
#define NEED(o, k) do { if ((uint64_t)(o) + (uint64_t)(k) > (uint64_t)len) return D1_ERR; } while (0)
#define U8(o)  ((uint32_t)b[(o)])
#define U16(o) ((uint32_t)(((uint32_t)b[(o)] << 8) | b[(o) + 1]))
#define U32(o) (((uint32_t)b[(o)] << 24) | ((uint32_t)b[(o) + 1] << 16) | \
                ((uint32_t)b[(o) + 2] << 8) | b[(o) + 3])
#define I8(o)  ((int)(int8_t)b[(o)])

/* bitutils.sws on a 16-bit stored value (and, quirk kept, on a u32 mfde offset) */
static uint64_t sws(uint64_t v) { return v != 0xFFFF ? v << 1 : v; }

/* bitutils.geo_secs on 3 big-endian bytes */
static double geo(const uint8_t *p) {
    uint32_t v = ((uint32_t)p[0] << 16) | ((uint32_t)p[1] << 8) | p[2];
    double deg = (double)(v & 0x7FFFFFu) / (3600.0 * 8);
    return (v & 0x800000u) ? -deg : deg;
}

/* coordconv.decode_region_coord */
static int32_t region_coord(uint32_t raw) { return (int32_t)((raw & 0x1FFFu) + (raw >> 13) * 4096u); }

/* length of the Python slice buf[start:start+n] given len(buf) == len */
static uint32_t clip(uint64_t start, uint64_t n, uint64_t len) {
    if (start >= len) return 0;
    return (uint32_t)(n < len - start ? n : len - start);
}

typedef struct { double lat_lo, lat_hi, lon_lo, lon_hi; int32_t range; } d1_bnd;

/* coordconv.xy_to_latlon, same operation order */
static void latlon(const d1_bnd *g, int32_t xc, int32_t yc, double *lat, double *lon) {
    *lon = g->lon_lo + ((double)xc / (double)g->range) * (g->lon_hi - g->lon_lo);
    *lat = g->lat_lo + ((double)yc / (double)g->range) * (g->lat_hi - g->lat_lo);
}

/* ------------------------------------------------------------- road (7.2) */

static int road(d1_ctx *c, const uint8_t *b, uint64_t len, const d1_bnd *g, int32_t fi,
                d1_frame *fr) {
    NEED(0, 8);
    uint32_t ninter = U16(2), ndc = U8(4), nad = U8(5), lvl = U16(6);
    fr->has_road = 1; fr->n_intersections = (d1_u16)ninter;
    fr->n_display_classes = (d1_u8)ndc; fr->n_additional_data = (d1_u8)nad;
    fr->route_planning_level = (d1_u8)((lvl >> 10) & 0x3F);
    fr->road_header_size_raw = (d1_u16)U16(0); fr->lvl_field_raw = (d1_u16)lvl;
    fr->road_size = (d1_u32)len;
    fr->dclass_first = (d1_u32)c->n[D1_T_DCLASS]; fr->link_first = (d1_u32)c->n[D1_T_LINK];
    fr->node_first = (d1_u32)c->n[D1_T_NODE]; fr->point_first = (d1_u32)c->n[D1_T_POINT];
    fr->addl_first = (d1_u32)c->n[D1_T_ADDL];

    uint64_t off = 8;
    for (uint32_t dc = 0; dc < ndc; dc++) {
        NEED(off, 4);
        d1_dclass d; ZERO(d);
        d.raw_offset_word = (d1_u16)U16(off); d.raw_count_word = (d1_u16)U16(off + 2);
        uint64_t xoff = sws(d.raw_offset_word);
        uint32_t npoly = d.raw_count_word & 0xFFFu;
        if (xoff != 0xFFFF) {
            d.has_flags = 1; d.flags_off = (d1_u32)xoff; d.flags_len = (d1_u8)clip(xoff, 2, len);
            put(c, D1_T_DCLASS, &d);
            xoff += 2;
            for (uint32_t j = 0; j < npoly; j++) {
                uint64_t link_start = xoff;
                NEED(xoff, 16);
                uint32_t hdr = U32(xoff), nnodes = U16(xoff + 4) & 0x7FFu, lattr = U16(xoff + 14);
                d1_link L; ZERO(L);
                L.frame = fi; L.display_class = (d1_u8)dc; L.road_type = (d1_u8)(lattr >> 12);
                L.altitude_flag = lattr & 1; L.route_type_guidance_flag = (lattr >> 1) & 1;
                L.pseudo3d_updown = (lattr >> 2) & 3; L.route_planning_tag = (lattr >> 4) & 1;
                L.link_id_flag = (lattr >> 6) & 1; L.selected_link_flag = (lattr >> 7) & 1;
                L.toll_flag = (lattr >> 8) & 1; L.route_number_flag = (lattr >> 9) & 1;
                L.infra_link_flag = (lattr >> 10) & 1; L.link_id_number_flag = (lattr >> 11) & 1;
                L.n_nodes = (d1_u16)nnodes;
                L.node_first = (d1_u32)c->n[D1_T_NODE]; L.point_first = (d1_u32)c->n[D1_T_POINT];

                uint64_t noff = sws(hdr & 0xFFu);
                for (uint32_t k = 0; k < nnodes; k++) {
                    NEED(xoff + noff, 6);
                    uint32_t na = U16(xoff + noff);
                    uint32_t nip = na & 0x3FFu;
                    d1_node nd; ZERO(nd);
                    nd.oneway = (na >> 15) & 1; nd.planned = (na >> 13) & 3;
                    nd.tunnel = (na >> 12) & 1; nd.bridge = (na >> 11) & 1;
                    int32_t xc = region_coord(U16(xoff + noff + 2));
                    int32_t yc = region_coord(U16(xoff + noff + 4));
                    nd.x = xc; nd.y = yc;
                    latlon(g, xc, yc, &nd.lat, &nd.lon);
                    put(c, D1_T_NODE, &nd);
                    d1_point pt; ZERO(pt);
                    pt.lat = nd.lat; pt.lon = nd.lon; pt.x = xc; pt.y = yc;
                    put(c, D1_T_POINT, &pt);
                    L.n_points++;
                    noff += 6;
                    for (uint32_t l = 0; l < nip; l++) {
                        NEED(xoff + noff, 2);
                        xc += I8(xoff + noff); yc += I8(xoff + noff + 1);
                        ZERO(pt);
                        pt.x = xc; pt.y = yc;
                        latlon(g, xc, yc, &pt.lat, &pt.lon);
                        put(c, D1_T_POINT, &pt);
                        L.n_points++;
                        noff += 2;
                    }
                }
                xoff += ((hdr >> 16) & 0xFFFu) << 1;
                L.raw_off = (d1_u32)link_start;
                L.raw_len = clip(link_start, xoff - link_start, len);
                put(c, D1_T_LINK, &L);
            }
        } else {
            put(c, D1_T_DCLASS, &d);
        }
        off += 4;
    }
    for (uint32_t i = 0; i < nad; i++) {
        NEED(off, 4);
        d1_addl a; ZERO(a);
        a.raw_offset_word = (d1_u16)U16(off); a.raw_size_word = (d1_u16)U16(off + 2);
        off += 4;
        uint64_t aoff = sws(a.raw_offset_word), asize = sws(a.raw_size_word);
        if (aoff != 0xFFFF && asize) {
            a.has_raw = 1; a.data_off = (d1_u32)aoff; a.data_len = clip(aoff, asize, len);
        }
        put(c, D1_T_ADDL, &a);
    }
    return 0;
}

/* ------------------------------------------------------- background (7.3) */

static int background(d1_ctx *c, const uint8_t *b, uint64_t len, const d1_bnd *g, int32_t fi,
                      d1_frame *fr) {
    NEED(0, 2);
    uint32_t hraw = U16(0);
    uint64_t hlen = sws(hraw);
    fr->has_bg = 1; fr->bg_header_size_raw = (d1_u16)hraw; fr->bg_size = (d1_u32)len;
    fr->bgelem_first = (d1_u32)c->n[D1_T_BGELEM]; fr->bgunit_first = (d1_u32)c->n[D1_T_BGUNIT];
    fr->bgshape_first = (d1_u32)c->n[D1_T_BGSHAPE]; fr->bgcoord_first = (d1_u32)c->n[D1_T_BGCOORD];

    uint64_t off = 2;
    while (off < hlen) {
        NEED(off, 4);
        d1_bgelem e; ZERO(e);
        e.raw_offset_word = (d1_u16)U16(off); e.raw_size_word = (d1_u16)U16(off + 2);
        uint64_t poff = sws(e.raw_offset_word);
        off += 4;
        if (poff == 0xFFFF) { put(c, D1_T_BGELEM, &e); continue; }

        NEED(poff, 2);
        uint32_t n = U16(poff);
        e.n_raw = (d1_u16)n; e.unit_n = n; e.unit_first = (d1_u32)c->n[D1_T_BGUNIT];
        poff += 2;
        uint64_t unit0 = poff;
        for (uint32_t i = 0; i < n; i++) {
            NEED(poff, 4);
            d1_bgunit u; ZERO(u);
            u.boff_word = (d1_u16)U16(poff); u.val = (d1_u16)U16(poff + 2);
            put(c, D1_T_BGUNIT, &u);
            poff += 4;
        }
        put(c, D1_T_BGELEM, &e);

        for (uint32_t i = 0; i < n; i++) {
            uint32_t val = U16(unit0 + 4 * (uint64_t)i + 2);
            uint32_t count = val & 0xFFFu, sclass = val >> 14;
            for (uint32_t j = 0; j < count; j++) {
                uint64_t start = poff;
                NEED(poff, 12);
                uint32_t hdr = U16(poff), flag = U16(poff + 2), code = U16(poff + 4);
                uint32_t addl = U16(poff + 6), sx = U16(poff + 8), sy = U16(poff + 10);
                uint64_t rec_len = (uint64_t)(hdr & 0xFFFu) << 1;
                uint32_t ncoord = flag & 0x7FFu;
                uint32_t mult = 1u << (addl & 7u);
                d1_bgshape s; ZERO(s);
                s.frame = fi; s.shape_class = (d1_u8)sclass; s.type_code = (d1_u16)code;
                s.n_coords = (d1_u16)ncoord; s.mult_const = (d1_u16)mult;
                s.underground = (addl >> 9) & 1; s.pen_up = (addl >> 10) & 1;
                s.coord_first = (d1_u32)c->n[D1_T_BGCOORD];
                if (sclass) {
                    int32_t xc = region_coord(sx), yc = region_coord(sy);
                    uint64_t coff = poff + 12;
                    d1_bgcoord k; ZERO(k);
                    k.x = xc; k.y = yc; latlon(g, xc, yc, &k.lat, &k.lon);
                    put(c, D1_T_BGCOORD, &k);
                    for (uint32_t m = 0; m < ncoord; m++) {
                        NEED(coff + 2 * (uint64_t)m, 2);
                        xc += I8(coff + 2 * (uint64_t)m) * (int32_t)mult;
                        yc += I8(coff + 2 * (uint64_t)m + 1) * (int32_t)mult;
                        ZERO(k);
                        k.x = xc; k.y = yc; latlon(g, xc, yc, &k.lat, &k.lon);
                        put(c, D1_T_BGCOORD, &k);
                    }
                    s.coord_n = ncoord + 1;
                }
                poff += rec_len;
                s.raw_off = (d1_u32)start; s.raw_len = clip(start, poff - start, len);
                put(c, D1_T_BGSHAPE, &s);
            }
        }
    }
    return 0;
}

/* ------------------------------------------------------------- name (7.4) */

static int name(d1_ctx *c, const uint8_t *b, uint64_t len, const d1_bnd *g, int32_t fi,
                d1_frame *fr) {
    NEED(0, 2);
    uint32_t hraw = U16(0);
    uint64_t hlen = sws(hraw);
    fr->has_name = 1; fr->name_header_size_raw = (d1_u16)hraw; fr->name_size = (d1_u32)len;
    fr->nlist_first = (d1_u32)c->n[D1_T_NLIST]; fr->nrec_first = (d1_u32)c->n[D1_T_NREC];

    uint64_t off = 2;
    while (off < hlen) {
        NEED(off, 4);
        d1_nlist nl; ZERO(nl);
        nl.raw_offset_word = (d1_u16)U16(off); nl.raw_count_word = (d1_u16)U16(off + 2);
        uint64_t toff = sws(nl.raw_offset_word);
        uint32_t tnum = nl.raw_count_word;
        off += 4;
        nl.rec_first = (d1_u32)c->n[D1_T_NREC];
        if (toff == 0xFFFF) { put(c, D1_T_NLIST, &nl); continue; }

        for (uint32_t k = 0; k < tnum; k++) {
            uint64_t rs = toff;
            NEED(rs, 6);
            uint32_t na = U16(rs), attr1 = U16(rs + 2), attr2 = U16(rs + 4);
            uint64_t reclen = (uint64_t)(na & 0xFFFu) << 1;
            if (reclen == 0) return D1_ERR;     /* Python: ValueError, "cannot be a real record" */
            uint32_t st = (attr1 >> 8) & 7u;
            uint64_t body = rs + 6, tstart = 0, tlen = 0;
            d1_nrec r; ZERO(r);
            r.frame = fi; r.string_type = (d1_u8)st; r.type_code = (d1_u16)attr2;
            r.priority = attr1 & 0x3Fu; r.vertical = (attr1 >> 6) & 1;
            r.display_scale_flag = (d1_u8)(attr1 >> 11);
            if (st != 4) {
                NEED(body + 2, 4);
                int32_t xc = region_coord(U16(body + 2)), yc = region_coord(U16(body + 4));
                latlon(g, xc, yc, &r.lat, &r.lon);
                r.has_latlon = 1;
            }
            if (st == 1) {
                NEED(body + 6, 2);
                tlen = (uint64_t)U16(body + 6) * 2; tstart = body + 8;
            } else if (st == 4) {
                NEED(body, 2);
                uint32_t xc0 = U16(body);
                uint64_t p = body + 4 + 2 * (uint64_t)(xc0 & 0xFu);
                NEED(p, 2);
                tlen = (uint64_t)U16(p) * 2; tstart = p + 2;
            } else if (st == 5) {
                NEED(body + 6, 4);
                uint32_t ang = U16(body + 6);
                tlen = (uint64_t)U16(body + 8) * 2; tstart = body + 10;
                r.has_angle = 1; r.angle_deg = (int32_t)(ang & 0x1FFu) - 90;
                r.angle_flags = (d1_u8)(ang >> 9);
            } else if (st == 6) {
                NEED(body + 8, 2);
                tlen = (uint64_t)U16(body + 8) * 2; tstart = body + 10;
            }
            if (tlen) {                          /* _cstr: clip, then up to the first NUL */
                uint32_t avail = clip(tstart, tlen, len), z = 0;
                while (z < avail && b[tstart + z]) z++;
                r.text_off = (d1_u32)tstart; r.text_len = z;
            }
            toff = rs + reclen;
            r.raw_off = (d1_u32)rs; r.raw_len = clip(rs, reclen, len);
            put(c, D1_T_NREC, &r);
        }
        nl.rec_n = (d1_u32)(c->n[D1_T_NREC] - nl.rec_first);
        put(c, D1_T_NLIST, &nl);
    }
    return 0;
}

/* --------------------------------------------------------- Map Frame (7.1) */

/* Decode one leaf; on any failure the caller rolls the table counts back. */
static int frame(d1_ctx *c, const uint8_t *map, const d1_leaf *L, int32_t fi, d1_frame *fr) {
    const uint8_t *b = map;
    uint64_t len = L->len;
    if (len < 36) return D1_ST_SHORT;
    fr->llpid_lat = geo(b + 2); fr->llpid_lon = geo(b + 6);
    uint32_t llcode = U16(10);
    fr->llcode_cx = llcode & 0xFF; fr->llcode_cy = (llcode >> 8) & 0xFF;
    fr->nregion = (d1_u16)U16(34);
    uint64_t de_off = 36 + (uint64_t)fr->nregion * 4;
    fr->region_list_off = 36;
    fr->region_list_len = clip(36, de_off - 36, len);

    /* mfde table: _read_entry() is (0xFFFFFFFF, 0) past the buffer */
#define ENTRY(i, ro, rsz) do { uint64_t e_ = de_off + (uint64_t)(i) * 6; \
        if (e_ + 6 > len) { (ro) = 0xFFFFFFFFu; (rsz) = 0; } \
        else { (ro) = U32(e_); (rsz) = U16(e_ + 4); } } while (0)
    int have = 0;
    uint64_t table_end = 0;
    for (int i = 0; i < 3; i++) {
        uint32_t ro, rsz; ENTRY(i, ro, rsz);
        if (ro != 0xFFFFFFFFu) {
            uint64_t v = sws(ro);
            if (v < len && (!have || v < table_end)) { table_end = v; have = 1; }
        }
    }
    uint64_t total;
    if (have) {
        int64_t diff = (int64_t)table_end - (int64_t)de_off;      /* floor division */
        int64_t q = diff >= 0 ? diff / 6 : -1;                    /* any negative < n_basic_map */
        total = (uint64_t)(q > (int64_t)L->n_basic_map ? q : (int64_t)L->n_basic_map);
    } else {
        total = (uint64_t)L->n_basic_map + L->n_ext_map;
    }

    fr->mfde_first = (d1_u32)c->n[D1_T_MFDE]; fr->mfde_n = (d1_u32)total;
    uint64_t max_end = de_off + total * 6;
    uint64_t eoff[3] = {0xFFFFFFFFu, 0xFFFFFFFFu, 0xFFFFFFFFu}, esz[3] = {0, 0, 0};
    for (uint64_t i = 0; i < total; i++) {
        uint32_t ro, rsz; ENTRY(i, ro, rsz);
        d1_mfde m; ZERO(m);
        m.raw_off = ro; m.raw_size = (d1_u16)rsz;
        uint64_t o = 0xFFFFFFFFu, s = 0;
        if (ro != 0xFFFFFFFFu) { o = sws(ro); s = sws(rsz); }
        if (i < 3) { eoff[i] = o; esz[i] = s; }
        if (s && o != 0xFFFFFFFFu && o < len) {
            if (o + s > max_end) max_end = o + s;
            if (i >= 3) { m.has_ext = 1; m.ext_off = (d1_u32)o; m.ext_len = clip(o, s, len); }
        }
        put(c, D1_T_MFDE, &m);
    }
    fr->tail_off = (d1_u32)max_end; fr->tail_len = clip(max_end, len, len) ? (d1_u32)(len - max_end) : 0;
    if (max_end >= len) fr->tail_len = 0;

    fr->frame_size = L->len;
    d1_bnd g = {L->lat_lo, L->lat_hi, L->lon_lo, L->lon_hi, L->coord_range};
    /* sub-frame buffers are mapdata[off:off+size], clipped like Python slices */
#define SUB(i) (esz[i] && eoff[i] != 0xFFFFFFFFu)
#define SUBLEN(i) clip(eoff[i], esz[i], len)
    if (total > 1 && SUB(1)) {
        if (g.range <= 0) return D1_ST_NORANGE;
        fr->bg_base = (d1_u32)eoff[1];
        if (background(c, map + (eoff[1] < len ? eoff[1] : len), SUBLEN(1), &g, fi, fr)) return D1_ST_BG;
    }
    if (total > 0 && SUB(0)) {
        if (g.range <= 0) return D1_ST_NORANGE;
        fr->road_base = (d1_u32)eoff[0];
        if (road(c, map + (eoff[0] < len ? eoff[0] : len), SUBLEN(0), &g, fi, fr)) return D1_ST_ROAD;
    }
    if (total > 2 && SUB(2)) {
        if (g.range <= 0) return D1_ST_NORANGE;
        fr->name_base = (d1_u32)eoff[2];
        if (name(c, map + (eoff[2] < len ? eoff[2] : len), SUBLEN(2), &g, fi, fr)) return D1_ST_NAME;
    }
    return 0;
}

/* -------------------------------------------------------------- the entry */

static int64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static d1_ctx *ctx_new(void *const *bufs, const int64_t *caps) {
    d1_ctx *c = (d1_ctx *)calloc(1, sizeof *c);
    if (!c) return NULL;
    for (int t = 1; t < D1_NOUT; t++) { c->base[t] = (uint8_t *)bufs[t]; c->cap[t] = caps[t]; }
    return c;
}

/* Decode one Map Frame (all-or-nothing, like the Python raise) and append its
 * `frame` row; returns the frame status. */
static int decode_leaf(d1_ctx *c, const uint8_t *region, const d1_leaf *L, int32_t fi,
                       int64_t *failed) {
    int64_t start[D1_NOUT];
    memcpy(start, c->n, sizeof start);
    d1_frame fr; ZERO(fr);
    fr.off = L->off;
    int st = frame(c, region + L->off, L, fi, &fr);
    if (st) {
        memcpy(c->n, start, sizeof start);
        d1_frame bad; ZERO(bad);
        bad.off = L->off; bad.frame_size = L->len; bad.status = st;
        fr = bad; (*failed)++;
    } else {
        fr.mfde_n = (d1_u32)(c->n[D1_T_MFDE] - fr.mfde_first);
        fr.dclass_n = (d1_u32)(c->n[D1_T_DCLASS] - fr.dclass_first);
        fr.link_n = (d1_u32)(c->n[D1_T_LINK] - fr.link_first);
        fr.node_n = (d1_u32)(c->n[D1_T_NODE] - fr.node_first);
        fr.point_n = (d1_u32)(c->n[D1_T_POINT] - fr.point_first);
        fr.addl_n = (d1_u32)(c->n[D1_T_ADDL] - fr.addl_first);
        fr.bgelem_n = (d1_u32)(c->n[D1_T_BGELEM] - fr.bgelem_first);
        fr.bgunit_n = (d1_u32)(c->n[D1_T_BGUNIT] - fr.bgunit_first);
        fr.bgshape_n = (d1_u32)(c->n[D1_T_BGSHAPE] - fr.bgshape_first);
        fr.bgcoord_n = (d1_u32)(c->n[D1_T_BGCOORD] - fr.bgcoord_first);
        fr.nlist_n = (d1_u32)(c->n[D1_T_NLIST] - fr.nlist_first);
        fr.nrec_n = (d1_u32)(c->n[D1_T_NREC] - fr.nrec_first);
    }
    put(c, D1_T_FRAME, &fr);
    return st;
}

static int64_t finish(d1_ctx *c, int64_t *stats, int64_t nin, int64_t failed, int64_t t0) {
    int64_t rc = 0;
    stats[0] = nin;
    for (int t = 1; t < D1_NOUT; t++) {
        stats[t] = c->n[t];
        if (c->n[t] > c->cap[t]) rc = 1;
    }
    stats[D1_S_FAILED] = failed;
    free(c);
    stats[D1_S_NS] = now_ns() - t0;
    return rc;
}

int64_t kw_d1_frames(const uint8_t *region, int64_t region_len, const void *leaf,
                     int64_t nframes, void *const *bufs, const int64_t *caps, int64_t *stats) {
    int64_t t0 = now_ns();
    if (!region || region_len < 0 || nframes < 0 || (nframes && !leaf) || !bufs || !caps ||
        !stats)
        return -1;
    d1_ctx *c = ctx_new(bufs, caps);
    if (!c) return -1;
    int64_t failed = 0;
    for (int64_t i = 0; i < nframes; i++) {
        d1_leaf L;
        memcpy(&L, (const uint8_t *)leaf + (size_t)i * sizeof L, sizeof L);
        if (L.off > (uint64_t)region_len || (uint64_t)region_len - L.off < L.len) { free(c); return -2; }
        decode_leaf(c, region, &L, (int32_t)i, &failed);
    }
    return finish(c, stats, nframes, failed, t0);
}

/* ------------------------------------------------------------ block walker */

#define NO_DATA_DSA 0xFFFFFFFFu
#define MAX_DEPTH 6                   /* parcel_mgmt.MAX_SUBPARCEL_DEPTH */
#define L0_TILE 4                     /* mesh.L0_TILE */
#define BAND_NONE (-1)

typedef struct { double lat_lo, lat_hi, lon_lo, lon_hi; } bnds;

/* walk.py _lon_span / _block_base_bounds (same operation order) */
static bnds block_bounds(const d1_block *B) {
    double lon_span = B->cov_lon_hi - B->cov_lon_lo;
    if (lon_span < 0) lon_span = lon_span + 360.0;
    double lat_span = B->cov_lat_hi - B->cov_lat_lo;
    double mx = lon_span / (double)B->grid_nx;
    double my = lat_span / (double)B->grid_ny;
    int64_t npc_lng = 1 + B->npg0, npc_lat = 1 + B->npl0;
    int64_t nbl_lng = 1 + B->n_blocks_lng, nbl_lat = 1 + B->n_blocks_lat;
    int64_t base_ix = ((int64_t)B->bsx * nbl_lng + B->blx) * npc_lng;
    int64_t base_iy = ((int64_t)B->bsy * nbl_lat + B->bly) * npc_lat;
    double base_lon = B->cov_lon_lo + (double)base_ix * mx;
    double base_lat = B->cov_lat_lo + (double)base_iy * my;
    bnds r = {base_lat, base_lat + (double)npc_lat * my, base_lon, base_lon + (double)npc_lng * mx};
    return r;
}

/* mesh.narrow_bounds */
static bnds narrow(bnds b, int64_t gn_lat, int64_t gn_lng, int64_t idx) {
    int64_t lpy = idx / gn_lng, lpx = idx % gn_lng;
    double lon_step = (b.lon_hi - b.lon_lo) / (double)gn_lng;
    double lat_step = (b.lat_hi - b.lat_lo) / (double)gn_lat;
    double lon_lo = b.lon_lo + (double)lpx * lon_step;
    double lat_lo = b.lat_lo + (double)lpy * lat_step;
    bnds r = {lat_lo, lat_lo + lat_step, lon_lo, lon_lo + lon_step};
    return r;
}

/* mesh.tile_bounds */
static bnds tile(bnds b, int64_t gn_lat, int64_t gn_lng, int64_t idx) {
    int64_t ly = idx / gn_lng, lx = idx % gn_lng;
    int64_t ty = ly / L0_TILE * L0_TILE, tx = lx / L0_TILE * L0_TILE;
    double lon_step = (b.lon_hi - b.lon_lo) / (double)gn_lng;
    double lat_step = (b.lat_hi - b.lat_lo) / (double)gn_lat;
    double lat_lo = b.lat_lo + (double)ty * lat_step;
    double lon_lo = b.lon_lo + (double)tx * lon_step;
    bnds r = {lat_lo, lat_lo + (double)L0_TILE * lat_step, lon_lo, lon_lo + (double)L0_TILE * lon_step};
    return r;
}

static int64_t npl(const d1_block *B, int pt) {
    return 1 + (pt == 0 ? B->npl0 : pt == 1 ? B->npl1 : pt == 2 ? B->npl2 : B->npl3);
}
static int64_t npg(const d1_block *B, int pt) {
    return 1 + (pt == 0 ? B->npg0 : pt == 1 ? B->npg1 : pt == 2 ? B->npg2 : B->npg3);
}

typedef struct {
    const uint8_t *b;                 /* the block's record buffer */
    uint64_t len;
    const d1_block *B;
    int64_t root_k;                   /* entries of the root record */
    uint64_t root_eoff;               /* offset of the root record's first entry */
    int path_n;
    uint16_t path[MAX_DEPTH + 2];
} walkc;

/* parcel_mgmt.parse_parcel_mgmt_record's whole-tree check: 0 ok, else the err code */
static int validate(const uint8_t *b, uint64_t len, const d1_block *B, uint64_t off, int depth) {
    if (depth > MAX_DEPTH) return 2;
    if (off + 2 > len) return 3;
    uint32_t raw = U16(off);
    if (raw & 0xFFu) return 1;
    int pt = (int)((raw >> 8) & 3u);
    int64_t k = npl(B, pt) * npg(B, pt);
    for (int64_t idx = 0; idx < k; idx++) {
        uint64_t e = off + 4 + (uint64_t)idx * 6;
        if (e + 4 > len) return 3;
        uint32_t dsa = U32(e);
        if (e + 6 > len) return 3;
        uint32_t size = U16(e + 4);
        if (size == 0 && dsa != NO_DATA_DSA) {
            int r = validate(b, len, B, sws(dsa), depth + 1);
            if (r) return r;
        }
    }
    return 0;
}

/* mesh.is_sparse_tile on the root record */
static int sparse_tile(const walkc *w, int64_t idx) {
    const uint8_t *b = w->b;
    int64_t gn_lng = npg(w->B, 0);
    int64_t ly = idx / gn_lng, lx = idx % gn_lng;
    int64_t ty = ly / L0_TILE * L0_TILE, tx = lx / L0_TILE * L0_TILE;
    uint32_t d0 = 0, s0 = 0;
    for (int dy = 0; dy < L0_TILE; dy++)
        for (int dx = 0; dx < L0_TILE; dx++) {
            int64_t j = (ty + dy) * gn_lng + tx + dx;
            if (j >= w->root_k) return 0;
            uint64_t e = w->root_eoff + (uint64_t)j * 6;
            uint32_t dsa = U32(e), size = U16(e + 4);
            if (dsa == NO_DATA_DSA || !size) return 0;
            if (dy == 0 && dx == 0) { d0 = dsa; s0 = size; }
            else if (dsa != d0 || size != s0) return 0;
        }
    return 1;
}

typedef struct { int64_t rlo, rhi, bidx; bnds bb; const uint8_t *region; int64_t region_len;
                 int64_t *failed; int rc; } walkr;

static double fl(double x) { return floor(x); }

/* One leaf: frame rule, band filter, decode, walk row. */
static void emit_leaf(d1_ctx *c, walkr *R, walkc *w, int ptype, uint32_t dsa, uint32_t size,
                      bnds lb) {
    const d1_block *B = w->B;
    /* checker cell of the slot midpoint (quantisation_roundtrip.Lattice.gy / gx) */
    double mlat = (lb.lat_lo + lb.lat_hi) / 2, mlon = (lb.lon_lo + lb.lon_hi) / 2;
    double gy = (mlat - B->lat0) / B->cell_lat * 4096.0;
    int64_t iy = (int64_t)fl(gy / 4096.0);
    if (!(R->rlo <= iy && iy <= R->rhi)) return;
    double d = mlon - B->lon0;
    double m = fmod(d - B->wlo, 360.0);
    if (m != 0.0) { if (m < 0.0) m += 360.0; } else m = copysign(0.0, 360.0);
    double gx = (m + B->wlo) / B->cell_lon * 4096.0;
    int64_t ix = (int64_t)fl(gx / 4096.0);

    int depth = w->path_n;
    bnds fb = lb; int fcls = 0;
    int64_t gl0 = npl(B, 0), gg0 = npg(B, 0);
    if (ptype && depth > 1) { fb = narrow(R->bb, gl0, gg0, w->path[0]); fcls = 2; }
    else if (B->level == 0 && ptype == 0 && depth == 1 && sparse_tile(w, w->path[0])) {
        fb = tile(R->bb, gl0, gg0, w->path[0]); fcls = 1;
    }
    int32_t rng;
    if (ptype) rng = B->rng_divided;
    else if (fcls == 1) rng = B->rng_sparse;
    else rng = B->rng_normal;

    uint64_t moff = (uint64_t)(dsa >> 8) * B->sector_sz + (uint64_t)(dsa & 0x3Fu) * B->logical_sz;
    uint64_t mlen = (uint64_t)size * B->logical_sz;
    if (moff > (uint64_t)R->region_len) moff = (uint64_t)R->region_len;
    if (mlen > (uint64_t)R->region_len - moff) mlen = (uint64_t)R->region_len - moff;

    d1_leaf L; ZERO(L);
    L.off = moff; L.len = (d1_u32)mlen;
    L.lat_lo = fb.lat_lo; L.lat_hi = fb.lat_hi; L.lon_lo = fb.lon_lo; L.lon_hi = fb.lon_hi;
    L.coord_range = rng; L.n_basic_map = B->n_basic_map; L.n_ext_map = B->n_ext_map;
    int32_t fi = (int32_t)c->n[D1_T_FRAME];
    int st = decode_leaf(c, R->region, &L, fi, R->failed);

    d1_walk r; ZERO(r);
    r.lat_lo = lb.lat_lo; r.lat_hi = lb.lat_hi; r.lon_lo = lb.lon_lo; r.lon_hi = lb.lon_hi;
    r.flat_lo = fb.lat_lo; r.flat_hi = fb.lat_hi; r.flon_lo = fb.lon_lo; r.flon_hi = fb.lon_hi;
    r.off = moff; r.len = (d1_u32)mlen; r.dsa = dsa; r.size = (d1_u16)size;
    r.level = B->level; r.blockset_index = B->blockset_index; r.block_index = B->block_index;
    r.block = (int32_t)R->bidx; r.frame = fi; r.ix = (int32_t)ix; r.iy = (int32_t)iy;
    r.frame_range = rng > 0 ? rng : 0; r.status = st ? 2 : 0; r.err = 0;
    r.p0 = w->path[0]; r.p1 = w->path[1]; r.p2 = w->path[2]; r.p3 = w->path[3];
    r.p4 = w->path[4]; r.p5 = w->path[5]; r.p6 = w->path[6];
    r.depth = (d1_u8)depth; r.parcel_type = (d1_u8)ptype; r.frame_class = (d1_u8)fcls;
    put(c, D1_T_WALK, &r);
}

/* walk._iter_tree_leaves (the record is already validated) */
static void walk_rec(d1_ctx *c, walkr *R, walkc *w, uint64_t off, bnds bounds) {
    const uint8_t *b = w->b;
    int pt = (int)((U16(off) >> 8) & 3u);
    int64_t gn_lat = npl(w->B, pt), gn_lng = npg(w->B, pt), k = gn_lat * gn_lng;
    for (int64_t idx = 0; idx < k; idx++) {
        uint64_t e = off + 4 + (uint64_t)idx * 6;
        uint32_t dsa = U32(e), size = U16(e + 4);
        if (dsa == NO_DATA_DSA) continue;
        bnds cb = narrow(bounds, gn_lat, gn_lng, idx);
        w->path[w->path_n++] = (uint16_t)idx;
        if (size == 0) walk_rec(c, R, w, sws(dsa), cb);
        else emit_leaf(c, R, w, pt, dsa, size, cb);
        w->path_n--;
    }
}

int64_t kw_d1_blocks(const uint8_t *region, int64_t region_len, const void *blocks,
                     int64_t nblocks, int64_t rlo, int64_t rhi, void *const *bufs,
                     const int64_t *caps, int64_t *stats) {
    int64_t t0 = now_ns();
    if (!region || region_len < 0 || nblocks < 0 || (nblocks && !blocks) || !bufs || !caps ||
        !stats)
        return -1;
    d1_ctx *c = ctx_new(bufs, caps);
    if (!c) return -1;
    int64_t failed = 0;
    for (int64_t bi = 0; bi < nblocks; bi++) {
        d1_block B;
        memcpy(&B, (const uint8_t *)blocks + (size_t)bi * sizeof B, sizeof B);
        uint64_t boff = B.off > (uint64_t)region_len ? (uint64_t)region_len : B.off;
        uint64_t blen = B.len < (uint64_t)region_len - boff ? B.len : (uint64_t)region_len - boff;
        walkc w; memset(&w, 0, sizeof w);
        w.b = region + boff; w.len = blen; w.B = &B;
        walkr R = {rlo, rhi, bi, block_bounds(&B), region, region_len, &failed, 0};
        const uint8_t *b = w.b;
        int err = validate(b, blen, &B, 0, 0);
        if (err) {
            d1_walk r; ZERO(r);
            r.lat_lo = r.flat_lo = R.bb.lat_lo; r.lat_hi = r.flat_hi = R.bb.lat_hi;
            r.lon_lo = r.flon_lo = R.bb.lon_lo; r.lon_hi = r.flon_hi = R.bb.lon_hi;
            r.off = B.off; r.len = B.len;
            r.level = B.level; r.blockset_index = B.blockset_index; r.block_index = B.block_index;
            r.block = (int32_t)bi; r.frame = -1; r.status = 1; r.err = err;
            put(c, D1_T_WALK, &r);
            continue;
        }
        w.root_k = npl(&B, (int)((U16(0) >> 8) & 3u)) * npg(&B, (int)((U16(0) >> 8) & 3u));
        w.root_eoff = 4;
        walk_rec(c, &R, &w, 0, R.bb);
    }
    int64_t nframes = c->n[D1_T_FRAME];
    c->n[0] = 0;
    int64_t rc = finish(c, stats, nframes, failed, t0);
    stats[D1_S_BLOCKS] = nblocks;
    return rc;
}
