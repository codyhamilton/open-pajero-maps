/* Test-only access to E2's static divided-leaf cell assignment (plan 67).
 * Compiled together with _cenc.c and _e1.c; calls the encoder's own dv_assign. */
#include "../../../kiwiw/_e2.c"
int probe_dv_assign(const double *b4, int ptype, double lat, double lon) {
    dv_state X;
    memset(&X, 0, sizeof X);
    for (int i = 0; i < 4; i++) X.b4[i] = b4[i];
    X.ptype = ptype; X.nx = ptype == 1 ? 2 : 4; X.ncell = X.nx * X.nx;
    X.lat_span = X.b4[1] - X.b4[0];
    X.lon_span = X.b4[3] - X.b4[2];
    X.cell_lat = X.lat_span / X.nx;
    X.cell_lon = X.lon_span / X.nx;
    return dv_assign(&X, lat, lon);
}
