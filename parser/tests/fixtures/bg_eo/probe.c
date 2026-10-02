/* Test-only access to the hidden shared division-probe/final-emit clipper. */
#include "../../../kiwiw/_cenc.c"
int64_t probe_bg(const double *lat, const double *lon, int64_t n,
                 const double *rect, uint8_t *out, int64_t room, int64_t *nrec) {
    const double b4[4] = {0,4096,0,4096};
    return kw__bg_shape(lat,lon,n,1,1,288,0,b4,rect,4096,out,room,nrec);
}
