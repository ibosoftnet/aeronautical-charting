"""Diagnose antimeridian geometry output."""
import sqlite3, struct
from shapely.wkb import loads as wkb_loads
from shapely.geometry import Polygon, MultiPolygon

SRC = r"d:/ibosoft/aeronautical-charting/aeronautical-data/Jeppesen Data/jeppesen.sqlite"
DST = r"d:/ibosoft/aeronautical-charting/aeronautical-data/Airspaces/Jeppesen/jeppesen_airspaces.gpkg"

# --- raw blob for a few crossing cases ------------------------------------
import math
def _unroll_coords(coords):
    result = [coords[0]]
    for lon, lat in coords[1:]:
        prev = result[-1][0]
        while lon - prev > 180: lon -= 360
        while prev - lon > 180: lon += 360
        result.append((lon, lat))
    return result

def _norm_lon(lon):
    return ((lon + 180) % 360) - 180

print("=== make_geometry trace for AUCKLAND id=6 ===")
src = sqlite3.connect(SRC)
blob = src.execute("SELECT geometry FROM boundary WHERE boundary_id=6").fetchone()[0]
n = struct.unpack(">I", blob[:4])[0]
pts = struct.unpack(f">{n*2}f", blob[4:4+n*8])
coords = list(zip(pts[0::2], pts[1::2]))
coords.append(coords[0])  # close

print(f"  raw n={n}, lons range [{min(x for x,y in coords):.2f}, {max(x for x,y in coords):.2f}]")

# detect crossings
for i in range(len(coords)-1):
    d = coords[i+1][0] - coords[i][0]
    if abs(d) > 180:
        print(f"  crossing [{i}]->[{i+1}]: {coords[i][0]:.2f} -> {coords[i+1][0]:.2f}  delta={d:.2f}")

unrolled = _unroll_coords(coords)
ul = [x for x,y in unrolled]
print(f"  unrolled lon range: [{min(ul):.2f}, {max(ul):.2f}]")
print(f"  unrolled first 8 lons: {[f'{x:.2f}' for x in ul[:8]]}")
print(f"  unrolled last 8 lons:  {[f'{x:.2f}' for x in ul[-8:]]}")

# find meridians
min_lon, max_lon = min(ul), max(ul)
first_am = math.ceil((min_lon - 180) / 360) * 360 + 180
meridians = [first_am + 360*k for k in range(100) if min_lon < first_am + 360*k < max_lon]
print(f"  antimeridian lines to clip at: {meridians}")

from shapely.geometry import box as _box
p = Polygon(unrolled)
print(f"  unrolled polygon valid={p.is_valid}, area={p.area:.4f}, bounds={[f'{v:.2f}' for v in p.bounds]}")
boundaries = [min_lon - 1] + meridians + [max_lon + 1]
for i in range(len(boundaries)-1):
    clip = _box(boundaries[i], -90, boundaries[i+1], 90)
    piece = p.intersection(clip)
    strip_center = (boundaries[i] + boundaries[i+1]) / 2
    shift = round(strip_center / 360) * 360
    print(f"  strip [{boundaries[i]:.1f}, {boundaries[i+1]:.1f}]  center={strip_center:.1f} shift={shift}")
    print(f"    piece: {piece.geom_type}, empty={piece.is_empty}, bounds={[f'{v:.2f}' for v in piece.bounds] if not piece.is_empty else 'N/A'}")
    if not piece.is_empty:
        norm_bounds = [_norm_lon(piece.bounds[0]-shift), piece.bounds[1], _norm_lon(piece.bounds[2]-shift), piece.bounds[3]]
        print(f"    normalized bounds: {[f'{v:.2f}' for v in norm_bounds]}")

src.close()

# --- Check produced GPKG: find MultiPolygon features ----------------------
print("\n=== GPKG: antimeridian features (boundary_id IN [6,7,9085,9088]) ===")
g = sqlite3.connect(DST)
rows = g.execute("""
    SELECT fid, name, type, boundary_id, geom FROM airspaces
    WHERE boundary_id IN (6, 7, 9085, 9088, 9086, 9087, 9147)
""").fetchall()
for fid, name, t, bid, blob in rows:
    wkb = blob[8:]
    bo = wkb[0]
    if bo == 1:
        gtype = struct.unpack("<I", wkb[1:5])[0]
    else:
        gtype = struct.unpack(">I", wkb[1:5])[0]
    type_name = {1:"Point",2:"LineString",3:"Polygon",6:"MultiPolygon"}.get(gtype, f"type={gtype}")
    try:
        geom = wkb_loads(wkb)
        bounds = geom.bounds
        if geom.geom_type == "MultiPolygon":
            parts_info = [(f"({p.bounds[0]:.1f},{p.bounds[1]:.1f},{p.bounds[2]:.1f},{p.bounds[3]:.1f})") for p in geom.geoms]
        else:
            parts_info = [f"({bounds[0]:.1f},{bounds[1]:.1f},{bounds[2]:.1f},{bounds[3]:.1f})"]
        print(f"  bid={bid} {name!r} type={t} -> WKB={type_name}  bounds={[f'{v:.2f}' for v in bounds]}")
        for pi in parts_info:
            print(f"    part: {pi}")
    except Exception as e:
        print(f"  bid={bid}: ERROR {e}")
g.close()
