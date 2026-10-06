/* Plan 38 witness: production bg_shape (kw__bg_shape) on cell-local raw coords,
 * b4 = {0,4096,0,4096}, cr 4096, with the spool record's type/mult/flags. */
#include "parser/kiwiw/_cenc.c"  /* -I<repo root> supplied by witness_246.py */
int64_t probe246(const double *y, const double *x, int64_t n, int64_t mc, int64_t tc, int64_t fl,
                 const double *rect, uint8_t *out, int64_t room, int64_t *nrec) {
    const double b4[4] = {0, 4096, 0, 4096};
    return kw__bg_shape(y, x, n, 1, mc, tc, fl, b4, rect, 4096, out, room, nrec);
}
