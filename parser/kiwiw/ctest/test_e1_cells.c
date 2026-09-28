/* Layer (b) C unit tests (plan 03, Contract T, 3C-06) for E1's per-shape
 * cell geometry (`e1_shape_cells` in `_e1.c`). Expected cells are
 * hand-derived from each case's drawing in cell units, never taken from
 * running Python build code.
 *
 * cbuild links every ctest/*.c into ONE executable and
 * `test_cenc_internals.c` owns `main`, so this file has no `main`: a
 * constructor runs the cases and prints "CASE <name> OK|FAIL" lines, and an
 * atexit handler turns any failure into exit status 1 (see the 3C-06
 * brief's amendment). */
#include <stdio.h>
#include <unistd.h>
#include "../_e1.c"

static int e1_fail = 0;

static void e1_report(const char *name, int ok, const char *why) {
    printf("CASE %s %s%s%s\n", name, ok ? "OK" : "FAIL", ok ? "" : ": ", ok ? "" : why);
    if (!ok) e1_fail = 1;
}

/* keys (iy<<32|ix) of `want` pairs, which must be listed in (iy, ix) order */
static int e1_same(const e1_keys *got, const int (*want)[2], int n) {
    if (got->n != n) return 0;
    for (int i = 0; i < n; i++)
        if (got->v[i] != e1_key(want[i][0], want[i][1])) return 0;
    return 1;
}

static int e1_run(e1_scratch *s, const double *px, const double *py, int n, int closed) {
    double gx[16], gy[16];
    memcpy(gx, px, sizeof(double) * n);
    memcpy(gy, py, sizeof(double) * n);
    return e1_shape_cells(s, gx, gy, n, closed, 64, 64);
}

/* A long shallow segment (0.5,0.5)->(2.5,1.5), slope 1/2: over column 0
 * it spans y 0.5..0.75, column 1 y 0.75..1.25 (crossing row line y=1),
 * column 2 y 1.25..1.5: cells (0,0), (1,0), (1,1), (2,1). */
static void e1_case_long_segment(e1_scratch *s) {
    double x[] = {0.5, 2.5}, y[] = {0.5, 1.5};
    static const int want[][2] = {{0, 0}, {1, 0}, {1, 1}, {2, 1}};
    int rc = e1_run(s, x, y, 2, 0);
    e1_report("e1_long_segment", rc == 0 && e1_same(&s->edge, want, 4) && s->cover.n == 0,
              "edge cells differ from {(0,0),(1,0),(1,1),(2,1)}");
}

/* A short diagonal through the corner point (1,1): every cell of the 2x2
 * block meets the EPS-grown footprint. */
static void e1_case_corner(e1_scratch *s) {
    double x[] = {0.5, 1.5}, y[] = {0.5, 1.5};
    static const int want[][2] = {{0, 0}, {1, 0}, {0, 1}, {1, 1}};
    int rc = e1_run(s, x, y, 2, 0);
    e1_report("e1_corner_diagonal", rc == 0 && e1_same(&s->edge, want, 4),
              "want the full 2x2 block");
}

/* Square ring 1.25..4.75 (closed, not repeated): edge = border of the
 * 1..4 block (12 cells); interior = (2,2) (3,2) (2,3) (3,3). The same
 * points as an open line give the same edge minus the closing side's
 * column-1 cells (1,2) (1,3) and no interior. */
static void e1_case_square(e1_scratch *s) {
    double x[] = {1.25, 4.75, 4.75, 1.25}, y[] = {1.25, 1.25, 4.75, 4.75};
    static const int edge[][2] = {{1, 1}, {2, 1}, {3, 1}, {4, 1}, {1, 2}, {4, 2}, {1, 3},
                                  {4, 3}, {1, 4}, {2, 4}, {3, 4}, {4, 4}};
    static const int inner[][2] = {{2, 2}, {3, 2}, {2, 3}, {3, 3}};
    int rc = e1_run(s, x, y, 4, 1);
    e1_report("e1_square_closed", rc == 0 && e1_same(&s->edge, edge, 12) &&
              e1_same(&s->cover, inner, 4), "closed square edge/interior differ");
    static const int open_edge[][2] = {{1, 1}, {2, 1}, {3, 1}, {4, 1}, {4, 2}, {4, 3},
                                       {1, 4}, {2, 4}, {3, 4}, {4, 4}};
    rc = e1_run(s, x, y, 4, 0);
    e1_report("e1_square_open", rc == 0 && e1_same(&s->edge, open_edge, 10) &&
              s->cover.n == 0, "open line must have no interior");
}

/* Off-grid parts are clipped: a vertical segment x=0.5 from y=-3 to 1.5
 * keeps only rows 0 and 1. A single point is its own cell. */
static void e1_case_clip_and_point(e1_scratch *s) {
    double x[] = {0.5, 0.5}, y[] = {-3.0, 1.5};
    static const int want[][2] = {{0, 0}, {0, 1}};
    int rc = e1_run(s, x, y, 2, 0);
    e1_report("e1_clip_to_grid", rc == 0 && e1_same(&s->edge, want, 2), "want (0,0),(0,1)");
    double px[] = {7.5}, py[] = {9.5};
    static const int pt[][2] = {{7, 9}};
    rc = e1_run(s, px, py, 1, 1);
    e1_report("e1_single_point", rc == 0 && e1_same(&s->edge, pt, 1) && s->cover.n == 0,
              "want the point's own cell only");
}

static void e1_atexit(void) { if (e1_fail) { fflush(stdout); _exit(1); } }

__attribute__((constructor)) static void e1_cases(void) {
    e1_scratch s;
    memset(&s, 0, sizeof s);
    e1_case_long_segment(&s);
    e1_case_corner(&s);
    e1_case_square(&s);
    e1_case_clip_and_point(&s);
    free(s.edge.v); free(s.cover.v); free(s.rx);
    fflush(stdout);
    atexit(e1_atexit);
}
