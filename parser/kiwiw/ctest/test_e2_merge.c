/* Layer (b) C unit tests (plan 03, Contract T, 3C-07) for E2's cover ring
 * (`e2_cover_ring`) and merge (`e2_locate` + `e2_merge`) in `_e2.c`.
 * Expected values are hand-derived from each case's inputs, never taken
 * from running Python build code.
 *
 * No `main` (test_cenc_internals.c owns it): a constructor runs the cases
 * and prints "CASE <name> OK|FAIL", an atexit handler turns a failure into
 * exit status 1. */
#include <stdio.h>
#include <unistd.h>
#include "../_e2.c"

static int e2t_fail = 0;

static void e2t_report(const char *name, int ok, const char *why) {
    printf("CASE %s %s%s%s\n", name, ok ? "OK" : "FAIL", ok ? "" : ": ", ok ? "" : why);
    if (!ok) e2t_fail = 1;
}

/* Bounds lat 10..12, lon 100..104: margins 0.5 / 1.0, ring
 * (9.5,99) (9.5,105) (12.5,105) (12.5,99) (9.5,99). */
static void e2t_case_cover_ring(void) {
    double b4[4] = {10.0, 12.0, 100.0, 104.0}, lat[5], lon[5];
    static const double wl[5] = {9.5, 9.5, 12.5, 12.5, 9.5};
    static const double wn[5] = {99.0, 105.0, 105.0, 99.0, 99.0};
    e2_cover_ring(b4, lat, lon);
    int ok = memcmp(lat, wl, sizeof wl) == 0 && memcmp(lon, wn, sizeof wn) == 0;
    e2t_report("e2_cover_ring", ok, "ring differs from the quarter-cell grown bounds");
}

/* A descriptor view of COLS[] (what e2_parse_desc accepts). */
static void e2t_desc(e2_desc *D) {
    memset(D, 0, sizeof *D);
    D->n_cols = (uint32_t)kw_ncols();
    for (uint32_t c = 0; c < D->n_cols; c++) {
        D->csize[c] = (uint8_t)kw_col_size((int)c);
        D->ckey[c] = (uint8_t)kw_col_key((int)c);
    }
    D->c_ncoords = kw__col_index(0); D->c_llen = kw__col_index(1);
    D->c_blob = kw__col_index(2); D->c_nst = kw__col_index(3);
    D->c_lat = kw__col_index(4); D->c_lon = kw__col_index(5); D->c_class = kw__col_index(6);
    D->k_bg = D->ckey[D->c_nst]; D->k_coord = D->ckey[D->c_lat];
    D->k_blob = D->ckey[D->c_blob];
}

/* Build a record with counts `cnt`: every column element e of column c is
 * filled with byte (base + 16*c + e); b_nstored / b_label_len / coords /
 * blob then take the given values. */
static int64_t e2t_rec(const e2_desc *D, uint8_t *buf, const uint64_t *cnt, int base,
                       const int32_t *nst, const int32_t *llen, const double *lat,
                       const double *lon, const char *blob) {
    memcpy(buf, cnt, 72);
    int64_t pos = 72;
    for (uint32_t c = 0; c < D->n_cols; c++) {
        int64_t n = (int64_t)cnt[D->ckey[c]], sz = D->csize[c];
        uint8_t *p = buf + pos;
        for (int64_t e = 0; e < n; e++) memset(p + e * sz, base + 16 * (int)c + (int)e, sz);
        if ((int)c == D->c_nst) memcpy(p, nst, 4 * n);
        if ((int)c == D->c_llen) memcpy(p, llen, 4 * n);
        if ((int)c == D->c_lat) memcpy(p, lat, 8 * n);
        if ((int)c == D->c_lon) memcpy(p, lon, 8 * n);
        if ((int)c == D->c_blob) memcpy(p, blob, n);
        pos += n * sz;
        while (pos & 7) buf[pos++] = 0;
    }
    return pos;
}

/* Own cell: 1 background (3 coords, label "ab"). Source: 2 backgrounds,
 * nstored {2, 4}, labels "x" / "yzw". Borrowed: shape 0 as a cover row,
 * shape 1 as an edge row. Merged: 3 backgrounds, 3 + 5 + 4 = 12 coords,
 * label blob "ab" "x" "yzw"; b_nstored {3, 5, 4}; b_ncoords
 * {own, 4, source's}; coords own, ring, source shape 1's (2..5). */
static void e2t_case_merge(void) {
    e2_desc D;
    e2t_desc(&D);
    static uint8_t own_b[4096], src_b[4096];
    uint64_t oc[9] = {0}, sc[9] = {0};
    oc[D.k_bg] = 1; oc[D.k_coord] = 3; oc[D.k_blob] = 2;
    sc[D.k_bg] = 2; sc[D.k_coord] = 6; sc[D.k_blob] = 4;
    int32_t onst[1] = {3}, ollen[1] = {2}, snst[2] = {2, 4}, sllen[2] = {1, 3};
    double olat[3] = {1, 2, 3}, olon[3] = {4, 5, 6};
    double slat[6] = {10, 11, 12, 13, 14, 15}, slon[6] = {20, 21, 22, 23, 24, 25};
    int64_t ol = e2t_rec(&D, own_b, oc, 1, onst, ollen, olat, olon, "ab");
    int64_t sl = e2t_rec(&D, src_b, sc, 100, snst, sllen, slat, slon, "xyzw");
    e2_rec own, src;
    int ok = e2_parse_rec(&D, own_b, (uint64_t)ol, 1, &own) == 0 &&
             e2_parse_rec(&D, src_b, (uint64_t)sl + 64, 0, &src) == 0 && src.len == (uint64_t)sl;
    e2_item it[2];
    it[0].src = 0; it[0].cover = 1;
    it[1].src = 0; it[1].cover = 0;
    ok = ok && e2_locate(&D, &src, 0, &it[0]) == 0 && e2_locate(&D, &src, 1, &it[1]) == 0;
    ok = ok && it[1].cstart == 2 && it[1].n == 4 && it[1].lstart == 1 && it[1].llen == 3;
    if (!ok) { e2t_report("e2_merge", 0, "record parse / shape walk failed"); return; }
    double b4[4] = {10.0, 12.0, 100.0, 104.0}, rl[5], rn[5];
    e2_cover_ring(b4, rl, rn);
    e2_buf out = {0};
    int64_t m = e2_merge(&D, &own, it, 2, &src, rl, rn, &out);
    e2_rec mr;
    ok = m > 0 && e2_parse_rec(&D, out.p, (uint64_t)m, 1, &mr) == 0;
    ok = ok && mr.cnt[D.k_bg] == 3 && mr.cnt[D.k_coord] == 12 && mr.cnt[D.k_blob] == 6;
    if (ok) {
        int32_t nst[3], nco[3];
        memcpy(nst, mr.col[D.c_nst], 12);
        memcpy(nco, mr.col[D.c_ncoords], 12);
        int32_t own_nco, src_nco1;
        memcpy(&own_nco, own.col[D.c_ncoords], 4);
        memcpy(&src_nco1, src.col[D.c_ncoords] + 4, 4);
        ok = nst[0] == 3 && nst[1] == 5 && nst[2] == 4 && nco[0] == own_nco && nco[1] == 4 &&
             nco[2] == src_nco1;
        double lat[12];
        memcpy(lat, mr.col[D.c_lat], sizeof lat);
        ok = ok && memcmp(lat, olat, 24) == 0 && memcmp(lat + 3, rl, 40) == 0 &&
             memcmp(lat + 8, slat + 2, 32) == 0;
        ok = ok && memcmp(mr.col[D.c_blob], "abxyzw", 6) == 0;
        /* a plain background column: own element, source elements 0 then 1 */
        int cz = D.csize[D.c_class];
        ok = ok && memcmp(mr.col[D.c_class], own.col[D.c_class], cz) == 0 &&
             memcmp(mr.col[D.c_class] + cz, src.col[D.c_class], 2 * cz) == 0;
    }
    free(out.p);
    e2t_report("e2_merge", ok, "merged record differs from own + cover(0) + edge(1)");
}


/* ---- 3C-09: division (assign, split chains, keep-order, halo text order,
 * column names). Values are hand-derived from the inputs. ---- */

const char *kw_col_name(int i);

/* Sub-grid over lat 10..12, lon 100..104, 2 x 2: cells are 1 deg of latitude
 * by 2 deg of longitude; cell = row * 2 + col. */
static void e2t_grid(dv_state *X) {
    memset(X, 0, sizeof *X);
    X->b4[0] = 10.0; X->b4[1] = 12.0; X->b4[2] = 100.0; X->b4[3] = 104.0;
    X->nx = 2; X->ncell = 4;
    X->lat_span = 2.0; X->lon_span = 4.0; X->cell_lat = 1.0; X->cell_lon = 2.0;
}

static void e2t_free_chains(dv_state *X) {
    free(X->rr); free(X->cpl); free(X->cpo); free(X->fc[0]); free(X->fi[0]);
}

static void e2t_case_div_assign(void) {
    dv_state X;
    e2t_grid(&X);
    int ok = dv_assign(&X, 10.5, 101.0) == 0 && dv_assign(&X, 10.5, 103.0) == 1 &&
             dv_assign(&X, 11.5, 101.0) == 2 && dv_assign(&X, 11.5, 103.0) == 3 &&
             dv_assign(&X, 10.0, 100.0) == 0 &&   /* the lower edge belongs to the cell */
             dv_assign(&X, 12.0, 101.0) == -1 &&  /* dlat == span: outside */
             dv_assign(&X, 9.9, 101.0) == -1 &&
             dv_assign(&X, 11.5, 104.0) == 3 &&   /* delta == span is not wrapped; clamped */
             dv_assign(&X, 10.5, 460.0) == 0 &&   /* delta 360 wraps to 0 */
             dv_assign(&X, 10.5, 99.0) == 0;      /* delta -1 -> 359 -> -1, clamped to 0 */
    e2t_report("e2_div_assign", ok, "assign_to_parcel cell index differs");
}

/* Lat 10.5, lon 101 -> 103 crosses from cell 0 into cell 1 at lon 102. The
 * bisection stops at depth 18: the first half [101,102] keeps halving its
 * right child, which is a leaf at depths 2..17 (16 leaves) and two leaves at
 * depth 18; the last of them is assigned to cell 0 by its start and so ends
 * exactly at 102. Chain 0 is 101, 101.5, 101.75, ... , 102 (19 points);
 * chain 1 is the single leaf [102,103], 2 points. */
static void e2t_case_div_split(void) {
    dv_state X;
    e2t_grid(&X);
    dv_sp S = {&X, 7, -1, 0, 0};
    int rc = dv_split(&S, 10.5, 101.0, 10.5, 103.0, 0) || dv_finish(&S);
    int ok = rc == 0 && X.nrr == 2 && X.ncp == 21 && X.rr[0].cell == 0 && X.rr[1].cell == 1 &&
             X.rr[0].par == 7 && X.rr[1].par == 7 && X.rr[0].len == 19 && X.rr[1].len == 2;
    if (ok) {
        const double *o0 = X.cpo + X.rr[0].start, *o1 = X.cpo + X.rr[1].start;
        ok = o0[0] == 101.0 && o0[1] == 101.5 && o0[2] == 101.75 && o0[3] == 101.875 &&
             o0[18] == 102.0 && o1[0] == 102.0 && o1[1] == 103.0 &&
             X.cpl[X.rr[0].start] == 10.5 && X.cpl[X.rr[1].start + 1] == 10.5;
    }
    e2t_free_chains(&X);
    /* a chain wholly outside the parent is dropped: nothing linked, points released */
    dv_state Y;
    e2t_grid(&Y);
    dv_sp T = {&Y, 3, -1, 0, 0};
    rc = dv_split(&T, 20.0, 101.0, 20.5, 101.5, 0) || dv_finish(&T);
    ok = ok && rc == 0 && Y.nrr == 0 && Y.ncp == 0;
    e2t_free_chains(&Y);
    e2t_report("e2_div_split", ok, "split chains differ from the bisection at lon 102");
}

static void e2t_sorted(int (*cmp)(const void *, const void *), dv_key *K, int n, const char *want,
                       int *ok) {
    qsort(K, (size_t)n, sizeof *K, cmp);
    for (int i = 0; i < n; i++)
        if ((char)('A' + K[i].item) != want[i]) *ok = 0;
}

static void e2t_case_div_order(void) {
    int ok = 1;
    /* road key (k1 type rank, k2 -length, k3 way, k4 ordinal, then position):
     * A worst rank; B shorter than C/D/E; C, D, E tie on k1..k3 and split on k4
     * (C = 0 first), D before E by position */
    dv_key R[5] = {{.k1 = 2, .k2 = -5, .item = 0, .pos = 0}, {.k1 = 1, .k2 = -3, .k3 = 7, .item = 1, .pos = 1},
                   {.k1 = 1, .k2 = -9, .k3 = 8, .k4 = 0, .item = 2, .pos = 2},
                   {.k1 = 1, .k2 = -9, .k3 = 8, .k4 = 1, .item = 3, .pos = 3},
                   {.k1 = 1, .k2 = -9, .k3 = 8, .k4 = 1, .item = 4, .pos = 4}};
    e2t_sorted(dv_cmp_road, R, 5, "CDEBA", &ok);
    /* background key (f = -area, k2 = -vertex count, position): B largest area;
     * C more vertices than A and D; A before D by position */
    dv_key B[4] = {{.f = -4.0, .k2 = -3, .item = 0, .pos = 0}, {.f = -9.0, .k2 = -2, .item = 1, .pos = 1},
                   {.f = -4.0, .k2 = -7, .item = 2, .pos = 2}, {.f = -4.0, .k2 = -3, .item = 3, .pos = 3}};
    e2t_sorted(dv_cmp_bg, B, 4, "BCAD", &ok);
    /* name key (k1 rank, position) */
    dv_key N[4] = {{.k1 = 1, .item = 0, .pos = 0}, {.k1 = 0, .item = 1, .pos = 1},
                   {.k1 = 1, .item = 2, .pos = 2}, {.k1 = 0, .item = 3, .pos = 3}};
    e2t_sorted(dv_cmp_name, N, 4, "BDAC", &ok);
    e2t_report("e2_div_order", ok, "keep-order comparators sort differently");
}

/* Halo texts compare like Python strings (a proper prefix sorts first) and
 * the slot table finds a repeated text. Blob "abcababd" = "abc" "ab" "abd". */
static void e2t_case_div_text(void) {
    dv_state X;
    memset(&X, 0, sizeof X);
    static uint8_t txt[] = "abcababd";
    int64_t toff[4] = {0, 3, 5, 8};
    X.toff = toff; X.ltxt = txt;
    int ok = dv_text_cmp(&X, 1, 0) < 0 && dv_text_cmp(&X, 0, 2) < 0 &&
             dv_text_cmp(&X, 2, 1) > 0 && dv_text_cmp(&X, 0, 0) == 0;
    int64_t tab[16];
    for (int i = 0; i < 16; i++) tab[i] = -1;
    int found = 1;
    int64_t sl = dv_tfind(&X, tab, 16, 0, &found);
    ok = ok && !found;
    tab[sl] = 0;
    ok = ok && dv_tfind(&X, tab, 16, 0, &found) == sl && found;
    dv_tfind(&X, tab, 16, 1, &found);
    ok = ok && !found;  /* "ab" is not "abc" */
    e2t_report("e2_div_text", ok, "halo text comparison / table lookup differs");
}

/* E2 addresses spool columns by enum and checks the names against `_cenc.c`'s
 * table: every name maps back to its own index; an unknown name is refused. */
static void e2t_case_col_names(void) {
    int ok = kw_ncols() == 43 && kw__col_named("r_display_class") == 0 &&
             kw__col_named("r_road_type") == 1 && kw__col_named("no_such_column") == -1 &&
             kw_col_name(kw_ncols()) == NULL;
    for (int i = 0; ok && i < kw_ncols(); i++) ok = kw__col_named(kw_col_name(i)) == i;
    e2t_report("e2_col_names", ok, "column name table is not a bijection");
}

static void e2t_exit(void) {
    fflush(stdout);
    if (e2t_fail) _exit(1);
}

__attribute__((constructor)) static void e2t_run(void) {
    e2t_case_cover_ring();
    e2t_case_merge();
    e2t_case_div_assign();
    e2t_case_div_split();
    e2t_case_div_order();
    e2t_case_div_text();
    e2t_case_col_names();
    atexit(e2t_exit);
}
