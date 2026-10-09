#!/usr/bin/env python3
"""Plan 62: census_join.tsv.gz -> phase23 identity format (plan-46 corrected producer per row)."""
import csv, gzip, io, sys

COLS = ("kind", "row_index", "level", "ix", "iy", "depth", "p0", "p1", "p2", "shape", "vert", "code", "vx", "vy",
        "producer_class", "producer_raw", "producer_hx", "producer_hy", "producer_ri", "mechanism")


def main(src, out):
    with gzip.open(src, "rt") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    rows.sort(key=lambda r: int(r["s46_row_index"]))
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", lineterminator="\n")
    w.writerow(COLS)
    for r in rows:
        w.writerow(["background", r["s46_row_index"], r["level"], r["ix"], r["iy"], r["depth"], r["p0"], r["p1"],
                    r["p2"], r["shape"], r["vert"], r["code"], r["s46_vx"], r["s46_vy"], r["s46_producer_class"],
                    r["s46_producer_raw"], r["s46_producer_hx"], r["s46_producer_hy"], r["s46_producer_ri"],
                    r["s46_mechanism"]])
    with open(out, "wb") as fo, gzip.GzipFile(filename="", mode="wb", fileobj=fo, mtime=0) as gz:
        gz.write(buf.getvalue().encode())
    print(len(rows))


if __name__ == "__main__":
    main(*sys.argv[1:3])
