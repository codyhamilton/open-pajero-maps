/* K1 -- the C checker core (plan 04, Phase 2, brief 2-03; DESIGN.md Contract
 * "K1 check", Determinism, Layout single-source).
 *
 * One call (`kw_k1_band`) per (block, row band): it decodes the band through D1
 * (`kw_d1_blocks`, in C), reads the spool cells of the block rectangle grown by
 * one cell, and checks every decoded item against them with the arithmetic of
 * `tools/quantisation_roundtrip.py` (the oracle). This unit owns the kinds
 * `range` (incl. background vertices), `step`, `road_node`, `road_point`,
 * `name_anchor` and the `explained` counters; the shape-based kinds are the
 * stubs `k1_bg_kinds` (2-04) and `k1_cmp_kinds` (2-05) in `_k1_bg.c` /
 * `_k1_cmp.c`, called from the band with the block context below.
 *
 * Accumulators. One `kind` row per kind (counts, worst passing error, the
 * number of kept samples), `K1_SAMPLE` `sample` rows per kind and one counter per
 * explained category. They merge by sums, max and "first N of the union": the
 * sample order (`k1_sample_cmp`) is total, so the result of any set of bands is
 * independent of their order and partition. Layouts are declared ONCE here as
 * X-macro field lists; `_k1.c` exports them through `kw_k1_*` accessors and
 * `kiwiw/cenc.py` mirrors them with a descriptor checked at load.
 *
 * Spool columns K1 reads are named in `K1_COLS`; Python maps each name to its
 * position in `kiwiw.spool._COLUMNS` and passes element sizes and count-key
 * indices for the whole column table (`kw_k1_band`'s `colmap`/`esz`/`ckey`).
 *
 * `kw_k1_band` returns 0, or < 0: -1 bad arguments, -2 D1 failed (a Map Frame
 * outside the region), -3 bad spool index/record, -4 out of memory. */
#ifndef KW_K1_H
#define KW_K1_H
#include "_d1.h"

#define K1_SAMPLE 10
#define K1_RAW 4096
#define K1_TOL 0.5
#define K1_EPS 1e-6
#define K1_INT_EPS 1e-3
#define K1_SEARCH 2.0
#define K1_SEG_BUCKET 64

#define K1_KINDS(X) X(range) X(step) X(road_node) X(road_point) X(name_anchor) \
    X(background) X(background_boundary) X(interior_cover) X(completeness)
#define K1_EXPLAINED(X) X(road_node_subcell_on_polyline) X(road_node_on_leaf_edge) \
    X(road_point_subcell_on_polyline) X(road_point_on_leaf_edge) X(name_anchor_halo)
#define K1_COLS(X) X(r_nstored) X(r_npts) X(n_lat) X(n_lon) X(p_lat) X(p_lon) X(b_class) \
    X(b_type) X(b_nstored) X(c_lat) X(c_lon) X(s_present) X(s_lat) X(s_lon)
#define K1_STATS(X) X(calls) X(leaves) X(failed_frames) X(d1_retries) X(cells) X(items) \
    X(rescues) X(ns) X(d1_ns)

#define K1_ENUM(n) K1_##n,
enum { K1_KINDS(K1_ENUM) K1_NKINDS };
enum { K1_EXPLAINED(K1_ENUM) K1_NEXPLAINED };
enum { K1_COLS(K1_ENUM) K1_NCOLS };
enum { K1_STATS(K1_ENUM) K1_NSTATS };
/* sample reasons */
enum { K1_R_RANGE = 0, K1_R_NO_SPOOL = 1, K1_R_STEP = 2, K1_R_NO_DECODE = 3,
       K1_R_BG = 4, K1_R_BG_BOUNDARY = 5, K1_R_COVER = 6 };

typedef uint8_t k1_u8;
typedef uint16_t k1_u16;
typedef uint32_t k1_u32;
typedef int32_t k1_i32;
typedef uint64_t k1_u64;
typedef double k1_f64;

#define K1_F_KIND(X, S) X(S, u64, checked) X(S, u64, failing) X(S, f64, worst) X(S, u32, nsamples)
/* `vx`/`vy`: the vertex's frame-raw integers (INT32_MIN: none); `code`: for
 * K1_R_NO_DECODE the D1 status (frame status, or 100 + err for a block record); `err`:
 * error in raw units, NaN for none; `depth`/`p0..p6`: the leaf path */
#define K1_F_SAMPLE(X, S) \
    X(S, f64, lat) X(S, f64, lon) X(S, f64, err) \
    X(S, i32, ix) X(S, i32, iy) X(S, i32, vx) X(S, i32, vy) X(S, i32, reason) X(S, i32, code) \
    X(S, u16, p0) X(S, u16, p1) X(S, u16, p2) X(S, u16, p3) X(S, u16, p4) X(S, u16, p5) \
    X(S, u16, p6) X(S, u8, depth)

#define K1_FIELD(S, T, N) k1_##T N;
#define K1_STRUCT(NAME, S) typedef struct { K1_F_##NAME(K1_FIELD, S) } S;
K1_STRUCT(KIND, k1_kind)
K1_STRUCT(SAMPLE, k1_sample)
enum { K1_T_KIND = 0, K1_T_SAMPLE, K1_NTABLES };

/* the accumulator a band adds into: K1_NKINDS kind rows, K1_NKINDS * K1_SAMPLE
 * sample rows, K1_NEXPLAINED counters, K1_NSTATS stats */
typedef struct { k1_kind *kind; k1_sample *smp; int64_t *expl; int64_t *stats; } k1_acc;

void k1_add(k1_acc *a, int kind, int64_t checked, int64_t failing, double worst);
void k1_push_sample(k1_acc *a, int kind, const k1_sample *s);
int k1_sample_cmp(const k1_sample *a, const k1_sample *b);

/* a decoded leaf in the checker's lattice (`Decoded` in the oracle) */
typedef struct {
    int64_t x0, x1, y0, y1;       /* leaf rectangle, raw lattice integers */
    int32_t ix, iy;               /* its cell */
    double flo, fla, fwo, fwa, rng; /* frame origin, extent, range */
    int ok;                       /* the leaf decoded (frame row with status 0) */
} k1_leaf;

typedef struct { double lat0, lon0, cell_lat, cell_lon, wlo; } k1_lat;
struct k1_region;

/* The spool background shapes a block band sees (2-04): the shapes of the cell ring around
 * the block rectangle plus the "tall" shapes (bounding box leaving their home cell grown by
 * one cell) that meet the rectangle grown by SEARCH + 1; local shapes that are themselves
 * tall are dropped when any tall shape is selected (they are in both sets). Coordinates are
 * global raw floats (`gx` / `gy` of the spool lat/lon), `off` has `n + 1` entries. A shape
 * with no stored coordinates is absent. */
typedef struct {
    int64_t n, ncoord, ncap, ccap;
    int32_t *type, *cls;
    uint8_t *tall;                /* local shape is tall (builder scratch) */
    int64_t *off;
    double *x, *y;
} k1_shapes;

/* the level's tall shapes (`kw_k1_tall` output) and their per-shape coordinate offsets
 * (`n + 1`) and bounding boxes (x0, x1, y0, y1 per shape), cached by Python per spool */
typedef struct { int32_t type, cls, n, hx, hy; } k1_tallrow;
typedef struct {
    const k1_tallrow *rows; const double *xy; const int64_t *off; const double *bb; int64_t n;
} k1_tallset;

/* the block context a kind group sees: the band's D1 tables (`walk[i]` <->
 * `leaf[i]`), the lattice and the spool region. `k1_region` is opaque here; 2-04
 * and 2-05 extend `_k1.c` with the shape accessors they need. */
typedef struct {
    const d1_block *block;
    k1_lat lat;
    int64_t nwalk;
    const d1_walk *walk;
    const k1_leaf *leaf;
    const d1_frame *frame;
    const d1_bgshape *bgshape;
    const d1_bgcoord *bgcoord;
    const struct k1_region *region;
    k1_acc *acc;
    const k1_shapes *shapes;      /* the band's spool background shapes (2-04) */
} k1_ctx;

/* shared by `_k1.c` and the kind groups: the frame-raw position of a lat/lon in a leaf, a
 * sample row (for the background kinds `code` carries the shape type), and `_cheb_seg` of
 * one point and one segment */
double k1_gx(const k1_lat *L, double lon);
double k1_gy(const k1_lat *L, double lat);
void k1_frame_raw(const k1_leaf *lf, double lat, double lon, double *fx, double *fy);
k1_sample k1_make_sample(const d1_walk *w, const k1_leaf *lf, double lat, double lon,
                         int32_t vx, int32_t vy, int reason, int code, double err);
double k1_cheb_pt_seg(double px, double py, double x1, double y1, double x2, double y2);

/* kind-group stubs (2-04: background, background_boundary, interior_cover,
 * completeness; 2-05: the comparison kinds). Return 0 or < 0. */
int k1_bg_kinds(k1_ctx *c);
int k1_cmp_kinds(k1_ctx *c);

/* layout accessors */
int kw_k1_ntables(void);
const char *kw_k1_table_name(int t);
int kw_k1_row_size(int t);
int kw_k1_nfields(int t);
const char *kw_k1_field_name(int t, int i);
const char *kw_k1_field_kind(int t, int i);
int kw_k1_field_off(int t, int i);
int kw_k1_sample_n(void);
int kw_k1_count(int what);            /* 0 kinds, 1 explained, 2 cols, 3 stats */
const char *kw_k1_name(int what, int i);

int64_t kw_k1_band(const uint8_t *region, int64_t region_len, const void *block,
                   int64_t rlo, int64_t rhi, const uint8_t *idx, int64_t idx_len,
                   const uint8_t *data, int64_t data_len, const int32_t *colmap,
                   const int32_t *esz, const int32_t *ckey, int64_t ncols,
                   void *kinds, void *samples, int64_t *expl, int64_t *stats,
                   const k1_tallrow *trows, const double *txy, const int64_t *toff,
                   const double *tbb, int64_t ntall);

/* The tall-shape pass: spool shapes whose bounding box leaves their home cell grown
 * by one cell, for spool index rows [a, b) of one level. Output: shape rows
 * (type, class, ncoords, home ix, iy) and their coordinates (global raw floats).
 * Returns 0, 1 (a table was too small: need[0], need[1] hold the rows needed; grow,
 * call again) or < 0. */
int64_t kw_k1_tall(const uint8_t *idx, int64_t idx_len, const uint8_t *data, int64_t data_len,
                   const int32_t *colmap, const int32_t *esz, const int32_t *ckey, int64_t ncols,
                   const double *lat5, int64_t a, int64_t b, k1_tallrow *rows, int64_t rows_cap,
                   double *xy, int64_t xy_cap, int64_t *need);
#endif
