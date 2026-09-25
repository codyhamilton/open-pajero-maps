/* Layer (b) C unit tests (plan 03, Contract T, 3C-02) for `_cenc.c`
 * internals the boundary reaches poorly: rectangle detection
 * (`rect_mult_for`) and the 3-11 edge-step split for coarse `mult_const`
 * rectangles (`emit_rect_piece`). Expected values below are hand-computed
 * (see the brief's report for the derivation), never taken from running
 * any Python build code.
 *
 * `#include`s the extension source directly so its `static` internals are
 * reachable without exporting them (Contract T (b)); built by
 * `kiwiw/cbuild.py` into one executable per `ctest/*.c`, run from pytest
 * (`test_c_units.py`). Prints one "CASE <name> OK|FAIL: <detail>" line per
 * case and exits non-zero if any case failed. */
#include <stdio.h>
#include "../_cenc.c"

static int g_fail = 0;

#define CASE(name) static void name(void)
#define OK(name) do { printf("CASE %s OK\n", #name); } while (0)
#define FAIL(name, ...) do { \
    printf("CASE %s FAIL: ", #name); printf(__VA_ARGS__); printf("\n"); \
    g_fail = 1; } while (0)
#define CHECK(name, cond, ...) do { \
    if (cond) { OK(name); } else { FAIL(name, __VA_ARGS__); } } while (0)

static Pt corner(double x, double y) { Pt p; p.x = x; p.y = y; p.k = KO; return p; }

/* A square whose edges (256) are exactly 2 x 128: rect_mult_for must pick
 * the largest candidate in {128,...,1} that divides both edges. */
CASE(rect_mult_for_square) {
    double R[4] = {0, 0, 256, 256};
    Pt pts[4] = {corner(0, 0), corner(256, 0), corner(256, 256), corner(0, 256)};
    int64_t mult = -1;
    int ok = rect_mult_for(pts, 4, R, &mult);
    CHECK(rect_mult_for_square, ok == 1 && mult == 128,
          "ok=%d mult=%lld (want ok=1 mult=128)", ok, (long long)mult);
}

/* 192 x 256: 128 does not divide 192 (192 % 128 == 64), so the largest
 * common candidate is 64. */
CASE(rect_mult_for_non_power_edge) {
    double R[4] = {0, 0, 192, 256};
    Pt pts[4] = {corner(0, 0), corner(192, 0), corner(192, 256), corner(0, 256)};
    int64_t mult = -1;
    int ok = rect_mult_for(pts, 4, R, &mult);
    CHECK(rect_mult_for_non_power_edge, ok == 1 && mult == 64,
          "ok=%d mult=%lld (want ok=1 mult=64)", ok, (long long)mult);
}

/* A triangle (n != 4) is never a whole-cell/sub-cell rectangle fill. */
CASE(rect_mult_for_rejects_non_quad) {
    double R[4] = {0, 0, 256, 256};
    Pt pts[3] = {corner(0, 0), corner(256, 0), corner(256, 256)};
    int64_t mult = -1;
    int ok = rect_mult_for(pts, 3, R, &mult);
    CHECK(rect_mult_for_rejects_non_quad, ok == 0, "ok=%d (want 0)", ok);
}

/* Four points, but not R's four corners (one is off by 1): not a fill. */
CASE(rect_mult_for_rejects_off_corner) {
    double R[4] = {0, 0, 256, 256};
    Pt pts[4] = {corner(0, 0), corner(255, 0), corner(256, 256), corner(0, 256)};
    int64_t mult = -1;
    int ok = rect_mult_for(pts, 4, R, &mult);
    CHECK(rect_mult_for_rejects_off_corner, ok == 0, "ok=%d (want 0)", ok);
}

static inline int64_t rd_u16be(const uint8_t *o, int64_t pos) {
    return ((int64_t)o[pos] << 8) | o[pos + 1];
}

/* The 3-11 edge-step split, hand-traced for R = [0,0,16384,16512],
 * mult=128 (mult_exp=7): two edges of length 16384 (16384/128=128 units,
 * lim=127*128=16256 -> k=2, 128/2=64 units/step, no remainder) and two of
 * length 16512 (129 units -> k=2, 129/2=64 units/step, remainder 1 unit
 * landing on the final, implicit-endpoint step: 64 then 65, not dumped
 * asymmetrically the other way). This exercises the "distribute the
 * remainder over the last r steps" rule, not just the common no-remainder
 * case. */
CASE(emit_rect_piece_edge_step_split) {
    double R[4] = {0, 0, 16384, 16512};
    Pt pts[4] = {corner(0, 0), corner(16384, 0), corner(16384, 16512), corner(0, 16512)};
    uint8_t *out = malloc(8192);
    Emit e; e.out = out; e.room = 8192; e.len = 0; e.nrec = 0;
    e.mc = 0; e.mult_exp = 0; e.tc = 5; e.fl = 0; e.closed = 1; e.R = R;
    int rc = emit_rect_piece(&e, pts, 128);
    if (rc != 0 || e.nrec != 1 || e.len != 28) {
        FAIL(emit_rect_piece_edge_step_split,
             "rc=%d nrec=%lld len=%lld (want rc=0 nrec=1 len=28)",
             rc, (long long)e.nrec, (long long)e.len);
        free(out);
        return;
    }
    int64_t rec_len_half = rd_u16be(out, 0), ndl = rd_u16be(out, 2);
    int64_t tc = rd_u16be(out, 4), flags_word = rd_u16be(out, 6);
    int64_t x0 = rd_u16be(out, 8), y0 = rd_u16be(out, 10);
    static const int expect_dx[8] = {64, 64, 0, 0, -64, -64, 0, 0};
    static const int expect_dy[8] = {0, 0, 64, 65, 0, 0, -64, -65};
    int mismatch = rec_len_half != 14 || ndl != 8 || tc != 5 || flags_word != 7 ||
                   x0 != 0 || y0 != 0;
    for (int k = 0; k < 8 && !mismatch; k++) {
        int8_t dx = (int8_t)out[12 + 2 * k], dy = (int8_t)out[12 + 2 * k + 1];
        if (dx != expect_dx[k] || dy != expect_dy[k]) mismatch = 1;
    }
    if (mismatch) {
        FAIL(emit_rect_piece_edge_step_split,
             "rec_len/2=%lld ndl=%lld tc=%lld flags=%lld x0=%lld y0=%lld deltas mismatch",
             (long long)rec_len_half, (long long)ndl, (long long)tc,
             (long long)flags_word, (long long)x0, (long long)y0);
    } else {
        OK(emit_rect_piece_edge_step_split);
    }
    free(out);
}

int main(void) {
    rect_mult_for_square();
    rect_mult_for_non_power_edge();
    rect_mult_for_rejects_non_quad();
    rect_mult_for_rejects_off_corner();
    emit_rect_piece_edge_step_split();
    return g_fail ? 1 : 0;
}
