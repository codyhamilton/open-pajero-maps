#!/usr/bin/env python3
"""
Deep cross-tab analysis of ambiguous highway=* buckets in the Australia OSM
extract, to build a defensible tag-based drivability classification instead
of assuming whole highway= buckets are in/out.

Single pass over the pbf with osmium, length computed via haversine on node
locations (using a location-caching node handler so we can compute way
lengths without a second pass / without a spatial db).
"""
import osmium
import math
import sys
from collections import defaultdict

PBF = "/home/codyh/workspace/open-pajero-maps/australia-260824.osm.pbf"

def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlambda/2)**2
    return 2*R*math.asin(min(1, math.sqrt(a)))

TRACK_BUCKET = {"track"}
UNCLASSIFIED_BUCKET = {"unclassified"}
SERVICE_BUCKET = {"service"}
NONMOTOR_BUCKET = {"path", "footway", "cycleway", "steps", "pedestrian"}
MAJOR_BUCKET = {"residential", "tertiary", "secondary", "primary", "trunk", "motorway",
                 "tertiary_link", "secondary_link", "primary_link", "trunk_link", "motorway_link"}

ALL_BUCKETS = TRACK_BUCKET | UNCLASSIFIED_BUCKET | SERVICE_BUCKET | NONMOTOR_BUCKET | MAJOR_BUCKET

class Handler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.count = 0
        # track crosstabs
        self.track_by_tracktype = defaultdict(lambda: [0, 0.0])  # [ways, km]
        self.track_by_access = defaultdict(lambda: [0, 0.0])
        self.track_smoothness = defaultdict(lambda: [0, 0.0])
        # unclassified crosstabs
        self.unc_by_surface = defaultdict(lambda: [0, 0.0])
        self.unc_by_access = defaultdict(lambda: [0, 0.0])
        # service crosstabs
        self.service_by_subtag = defaultdict(lambda: [0, 0.0])
        # nonmotor crosstabs
        self.nonmotor_by_motor = defaultdict(lambda: [0, 0.0])
        self.nonmotor_by_highway = defaultdict(lambda: [0, 0.0])
        # major buckets access check
        self.major_by_access = defaultdict(lambda: [0, 0.0])
        self.major_by_highway_access = defaultdict(lambda: [0, 0.0])

        self.total_ways_seen = 0
        self.total_km_seen = 0.0

    def way(self, w):
        self.count += 1
        if self.count % 2_000_000 == 0:
            print(f"...{self.count} ways processed", file=sys.stderr)

        tags = w.tags
        hw = tags.get("highway")
        if not hw or hw not in ALL_BUCKETS:
            return

        # compute length from node locations available on this way
        try:
            nodes = w.nodes
            length = 0.0
            prev = None
            valid = True
            for n in nodes:
                if not n.location.valid():
                    valid = False
                    break
                lon, lat = n.location.lon, n.location.lat
                if prev is not None:
                    length += haversine_km(prev[0], prev[1], lon, lat)
                prev = (lon, lat)
            if not valid:
                return
        except Exception:
            return

        self.total_ways_seen += 1
        self.total_km_seen += length

        access = tags.get("access")
        motor_vehicle = tags.get("motor_vehicle")
        vehicle = tags.get("vehicle")
        motorcar = tags.get("motorcar")

        def access_bucket():
            vals = [v for v in (access, motor_vehicle, vehicle, motorcar) if v]
            if not vals:
                return "unspecified"
            restrictive = {"no", "private"}
            permissive_like = {"permissive", "destination", "customers", "delivery", "agricultural", "forestry"}
            if any(v in restrictive for v in vals):
                return "restricted(no/private)"
            if any(v in permissive_like for v in vals):
                return "conditional(permissive/destination/etc)"
            if any(v == "yes" for v in vals):
                return "explicit_yes"
            return "other:" + ",".join(sorted(set(vals)))

        if hw in TRACK_BUCKET:
            tt = tags.get("tracktype", "untagged")
            self.track_by_tracktype[tt][0] += 1
            self.track_by_tracktype[tt][1] += length
            ab = access_bucket()
            self.track_by_access[ab][0] += 1
            self.track_by_access[ab][1] += length
            sm = tags.get("smoothness", "untagged")
            self.track_smoothness[sm][0] += 1
            self.track_smoothness[sm][1] += length

        elif hw in UNCLASSIFIED_BUCKET:
            surf = tags.get("surface", "untagged")
            # bucket surface into paved/unpaved/untagged
            paved = {"paved", "asphalt", "concrete", "concrete:plates", "concrete:lanes", "paving_stones", "sett", "cobblestone", "metal", "wood"}
            unpaved = {"unpaved", "gravel", "dirt", "sand", "ground", "grass", "earth", "mud", "compacted", "fine_gravel", "pebblestone", "woodchips", "clay", "rock", "ice", "salt", "snow"}
            if surf == "untagged":
                scat = "untagged"
            elif surf in paved:
                scat = "paved"
            elif surf in unpaved:
                scat = "unpaved"
            else:
                scat = "other:" + surf
            self.unc_by_surface[scat][0] += 1
            self.unc_by_surface[scat][1] += length
            ab = access_bucket()
            self.unc_by_access[ab][0] += 1
            self.unc_by_access[ab][1] += length

        elif hw in SERVICE_BUCKET:
            sv = tags.get("service", "untagged")
            self.service_by_subtag[sv][0] += 1
            self.service_by_subtag[sv][1] += length

        elif hw in NONMOTOR_BUCKET:
            vals = [v for v in (motor_vehicle, motorcar) if v]
            if any(v == "yes" for v in vals):
                cat = "motor_vehicle/motorcar=yes"
            elif vals:
                cat = "explicit_other:" + ",".join(sorted(set(vals)))
            else:
                cat = "untagged(non-motorized assumed)"
            self.nonmotor_by_motor[cat][0] += 1
            self.nonmotor_by_motor[cat][1] += length
            self.nonmotor_by_highway[hw][0] += 1
            self.nonmotor_by_highway[hw][1] += length

        elif hw in MAJOR_BUCKET:
            ab = access_bucket()
            self.major_by_access[ab][0] += 1
            self.major_by_access[ab][1] += length
            key = f"{hw}|{ab}"
            self.major_by_highway_access[key][0] += 1
            self.major_by_highway_access[key][1] += length


def fmt_table(d, title):
    print(f"\n=== {title} ===")
    items = sorted(d.items(), key=lambda kv: -kv[1][1])
    total_km = sum(v[1] for v in d.values())
    total_ways = sum(v[0] for v in d.values())
    print(f"{'key':40s} {'ways':>10s} {'km':>14s} {'% of bucket':>12s}")
    for k, (ways, km) in items:
        pct = 100.0 * km / total_km if total_km else 0
        print(f"{k:40s} {ways:10d} {km:14.1f} {pct:11.2f}%")
    print(f"{'TOTAL':40s} {total_ways:10d} {total_km:14.1f} {100.0:11.2f}%")


if __name__ == "__main__":
    import time
    t0 = time.time()
    h = Handler()
    # locations=True to attach node coords to ways cheaply via node cache
    h.apply_file(PBF, locations=True, idx='flex_mem')
    t1 = time.time()

    print(f"Processed {h.count} ways total; {h.total_ways_seen} ways in target buckets with valid geometry, {h.total_km_seen:.1f} km total.")
    print(f"Runtime: {t1-t0:.1f}s")

    fmt_table(h.track_by_tracktype, "track: by tracktype")
    fmt_table(h.track_by_access, "track: by access/motor_vehicle/vehicle/motorcar bucket")
    fmt_table(h.track_smoothness, "track: by smoothness")

    fmt_table(h.unc_by_surface, "unclassified: by surface category")
    fmt_table(h.unc_by_access, "unclassified: by access bucket")

    fmt_table(h.service_by_subtag, "service: by service= subtag")

    fmt_table(h.nonmotor_by_motor, "path/footway/cycleway/steps/pedestrian: by motor_vehicle/motorcar signal")
    fmt_table(h.nonmotor_by_highway, "path/footway/cycleway/steps/pedestrian: by highway= subtype (for reference)")

    fmt_table(h.major_by_access, "MAJOR (residential/tertiary/secondary/primary/trunk/motorway [+links]): by access bucket")
    fmt_table(h.major_by_highway_access, "MAJOR: by highway|access_bucket (detail)")
