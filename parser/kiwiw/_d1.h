/* D1 -- the C frame decoders (plan 04, Phase 2, brief 2-01; DESIGN.md Domain
 * "libkiwiw", Contract "D1 decode").
 *
 * Row layouts, declared ONCE here. Every table is an X-macro field list
 * `D1_F_<NAME>(X, S)` with `X(S, type, name)`; the C structs and the exported
 * layout (`kw_d1_*` accessors in `_d1.c`) are both generated from it, and
 * `kiwiw/cenc.py` mirrors it with a checked Python descriptor (a mismatch
 * raises at load). Rows are little-endian, naturally aligned, padding zeroed.
 * Fields are listed widest first.
 *
 * Input: the mapped disc region (bytes of ALLDATA.KWI, G or R) plus a
 * leaf-frame table, one `leaf` row per Map Frame (2-02's block walker emits
 * it). Output: one row array per table below, in leaf-frame order (the
 * on-disc order within a frame); a frame the Python decoder would raise on
 * gets a `frame` row with `status != 0` and contributes no other rows.
 *
 * Offsets. `frame.off` is the frame's absolute offset in the region. Every
 * other `*_off` is relative to the buffer the Python decoder slices it from:
 * the Map Frame for `mfde`/`region_list`/`tail`/header, the road / background
 * / name sub-frame for `link`/`dclass`/`addl`/`bgshape`/`nrec` (their base is
 * `frame.road_base` etc., relative to the Map Frame). A raw field is the
 * region slice [frame.off + base + off, + len) and is clipped like Python's
 * slicing (never past the sub-frame's buffer). `*_first`/`*_n` pairs index
 * the named table's rows (global within the call).
 *
 * Status codes (`frame.status`): 0 ok; 1 Map Frame shorter than its 36-byte
 * header; 2 background frame did not decode; 3 road frame did not decode;
 * 4 name frame did not decode; 5 a sub-frame is present but the leaf has no
 * coord_range. (Python raises, in this order of decode: background, road,
 * name.)
 *
 * `kw_d1_frames` return: 0 ok, 1 an output table was too small (stats[t]
 * holds the rows needed per table; nothing past a table's capacity was
 * written; grow and call again), < 0: -1 bad arguments, -2 a leaf row lies
 * outside the region. */
#ifndef KW_D1_H
#define KW_D1_H
#include <stddef.h>
#include <stdint.h>

typedef uint8_t d1_u8;
typedef uint16_t d1_u16;
typedef uint32_t d1_u32;
typedef int32_t d1_i32;
typedef uint64_t d1_u64;
typedef double d1_f64;

enum {
    D1_T_LEAF = 0,   /* input */
    D1_T_FRAME, D1_T_MFDE, D1_T_DCLASS, D1_T_ADDL, D1_T_LINK, D1_T_NODE, D1_T_POINT,
    D1_T_BGELEM, D1_T_BGUNIT, D1_T_BGSHAPE, D1_T_BGCOORD, D1_T_NLIST, D1_T_NREC,
    D1_NTABLES
};
/* stats slots: [0] leaf frames in, [t] rows needed for table t (1..13),
 * [14] failed frames, [15] C nanoseconds */
#define D1_NSTATS 16
#define D1_S_FAILED 14
#define D1_S_NS 15

#define D1_ST_SHORT 1
#define D1_ST_BG 2
#define D1_ST_ROAD 3
#define D1_ST_NAME 4
#define D1_ST_NORANGE 5

/* leaf-frame table row (input): where the frame is and its coordinate frame.
 * coord_range <= 0 means "none" (Python's BoundingBox.coord_range is None). */
#define D1_F_LEAF(X, S) \
    X(S, u64, off) \
    X(S, f64, lat_lo) X(S, f64, lat_hi) X(S, f64, lon_lo) X(S, f64, lon_hi) \
    X(S, u32, len) X(S, i32, coord_range) X(S, u16, n_basic_map) X(S, u16, n_ext_map)

/* one per frame: the Map Frame header, the directory counts, and the row
 * ranges the frame contributed to every other table */
#define D1_F_FRAME(X, S) \
    X(S, f64, llpid_lat) X(S, f64, llpid_lon) X(S, u64, off) \
    X(S, u32, frame_size) X(S, u32, region_list_off) X(S, u32, region_list_len) \
    X(S, u32, tail_off) X(S, u32, tail_len) \
    X(S, u32, road_base) X(S, u32, road_size) X(S, u32, bg_base) X(S, u32, bg_size) \
    X(S, u32, name_base) X(S, u32, name_size) \
    X(S, u32, mfde_first) X(S, u32, mfde_n) X(S, u32, dclass_first) X(S, u32, dclass_n) \
    X(S, u32, link_first) X(S, u32, link_n) X(S, u32, node_first) X(S, u32, node_n) \
    X(S, u32, point_first) X(S, u32, point_n) X(S, u32, addl_first) X(S, u32, addl_n) \
    X(S, u32, bgelem_first) X(S, u32, bgelem_n) X(S, u32, bgunit_first) X(S, u32, bgunit_n) \
    X(S, u32, bgshape_first) X(S, u32, bgshape_n) X(S, u32, bgcoord_first) X(S, u32, bgcoord_n) \
    X(S, u32, nlist_first) X(S, u32, nlist_n) X(S, u32, nrec_first) X(S, u32, nrec_n) \
    X(S, i32, status) \
    X(S, u16, nregion) X(S, u16, n_intersections) X(S, u16, road_header_size_raw) \
    X(S, u16, lvl_field_raw) X(S, u16, bg_header_size_raw) X(S, u16, name_header_size_raw) \
    X(S, u8, llcode_cx) X(S, u8, llcode_cy) \
    X(S, u8, has_road) X(S, u8, n_display_classes) X(S, u8, n_additional_data) \
    X(S, u8, route_planning_level) X(S, u8, has_bg) X(S, u8, has_name)

/* Map Frame directory (mfde) entry; ext_* is `ext_frame_raw[i]` (i >= 3) */
#define D1_F_MFDE(X, S) \
    X(S, u32, raw_off) X(S, u32, ext_off) X(S, u32, ext_len) \
    X(S, u16, raw_size) X(S, u8, has_ext)

/* road display-class table entry; flags_* is `display_class_flags[dc]` */
#define D1_F_DCLASS(X, S) \
    X(S, u32, flags_off) X(S, u16, raw_offset_word) X(S, u16, raw_count_word) \
    X(S, u8, has_flags) X(S, u8, flags_len)

/* road additional-data table entry; data_* is `additional_data_raw[i]` */
#define D1_F_ADDL(X, S) \
    X(S, u32, data_off) X(S, u32, data_len) X(S, u16, raw_offset_word) \
    X(S, u16, raw_size_word) X(S, u8, has_raw)

/* one road multilink */
#define D1_F_LINK(X, S) \
    X(S, i32, frame) X(S, u32, raw_off) X(S, u32, raw_len) X(S, u32, node_first) \
    X(S, u32, point_first) X(S, u32, n_points) X(S, u16, n_nodes) \
    X(S, u8, display_class) X(S, u8, road_type) X(S, u8, altitude_flag) \
    X(S, u8, route_type_guidance_flag) X(S, u8, pseudo3d_updown) \
    X(S, u8, route_planning_tag) X(S, u8, link_id_flag) X(S, u8, selected_link_flag) \
    X(S, u8, toll_flag) X(S, u8, route_number_flag) X(S, u8, infra_link_flag) \
    X(S, u8, link_id_number_flag)

#define D1_F_NODE(X, S) \
    X(S, f64, lat) X(S, f64, lon) X(S, i32, x) X(S, i32, y) \
    X(S, u8, oneway) X(S, u8, planned) X(S, u8, tunnel) X(S, u8, bridge)

/* every polyline vertex of a link, nodes included (RoadLink.points) */
#define D1_F_POINT(X, S) X(S, f64, lat) X(S, f64, lon) X(S, i32, x) X(S, i32, y)

/* background distribution-header element and its type-unit table */
#define D1_F_BGELEM(X, S) \
    X(S, u32, unit_first) X(S, u32, unit_n) \
    X(S, u16, raw_offset_word) X(S, u16, raw_size_word) X(S, u16, n_raw)
#define D1_F_BGUNIT(X, S) X(S, u16, boff_word) X(S, u16, val)

/* one background shape; coord_* are its vertices (none for a point shape) */
#define D1_F_BGSHAPE(X, S) \
    X(S, i32, frame) X(S, u32, raw_off) X(S, u32, raw_len) X(S, u32, coord_first) \
    X(S, u32, coord_n) X(S, u16, type_code) X(S, u16, n_coords) X(S, u16, mult_const) \
    X(S, u8, shape_class) X(S, u8, underground) X(S, u8, pen_up)
#define D1_F_BGCOORD(X, S) X(S, f64, lat) X(S, f64, lon) X(S, i32, x) X(S, i32, y)

/* name list (7.4.1 table entry) and name record; text_* is the record's
 * string up to its first NUL (latin-1 bytes); lat/lon valid iff has_latlon
 * (string_type != 4), angle_deg iff has_angle (string_type 5) */
#define D1_F_NLIST(X, S) \
    X(S, u32, rec_first) X(S, u32, rec_n) X(S, u16, raw_offset_word) X(S, u16, raw_count_word)
#define D1_F_NREC(X, S) \
    X(S, f64, lat) X(S, f64, lon) X(S, i32, frame) X(S, u32, raw_off) X(S, u32, raw_len) \
    X(S, u32, text_off) X(S, u32, text_len) X(S, i32, angle_deg) X(S, u16, type_code) \
    X(S, u8, string_type) X(S, u8, priority) X(S, u8, vertical) \
    X(S, u8, display_scale_flag) X(S, u8, angle_flags) X(S, u8, has_latlon) X(S, u8, has_angle)

#define D1_FIELD(S, T, N) d1_##T N;
#define D1_STRUCT(NAME, S) typedef struct { D1_F_##NAME(D1_FIELD, S) } S;
D1_STRUCT(LEAF, d1_leaf)
D1_STRUCT(FRAME, d1_frame)
D1_STRUCT(MFDE, d1_mfde)
D1_STRUCT(DCLASS, d1_dclass)
D1_STRUCT(ADDL, d1_addl)
D1_STRUCT(LINK, d1_link)
D1_STRUCT(NODE, d1_node)
D1_STRUCT(POINT, d1_point)
D1_STRUCT(BGELEM, d1_bgelem)
D1_STRUCT(BGUNIT, d1_bgunit)
D1_STRUCT(BGSHAPE, d1_bgshape)
D1_STRUCT(BGCOORD, d1_bgcoord)
D1_STRUCT(NLIST, d1_nlist)
D1_STRUCT(NREC, d1_nrec)

/* layout accessors (exported from _d1.c, for the Python descriptor check) */
int kw_d1_ntables(void);
const char *kw_d1_table_name(int t);
int kw_d1_row_size(int t);
int kw_d1_nfields(int t);
const char *kw_d1_field_name(int t, int i);
const char *kw_d1_field_kind(int t, int i);
int kw_d1_field_off(int t, int i);

int64_t kw_d1_frames(const uint8_t *region, int64_t region_len, const void *leaf,
                     int64_t nframes, void *const *bufs, const int64_t *caps,
                     int64_t *stats);

#endif
