"""Read-only: decode boundary geometry blob format."""
import sqlite3, struct

db = r"d:/ibosoft/aeronautical-charting/aeronautical-data/Jeppesen Data/jeppesen.sqlite"
c = sqlite3.connect(db)
cur = c.cursor()

# Pick a few diverse rows
rows = cur.execute("""
SELECT boundary_id, name, type, min_lonx, min_laty, max_lonx, max_laty,
       LENGTH(geometry) AS gl, geometry
FROM boundary
WHERE name IN ('TAHITI','OCEAN REEF CLUB') OR boundary_id IN (1,2,3,1000,5000,30000)
ORDER BY boundary_id
LIMIT 8
""").fetchall()

for bid, name, t, minx, miny, maxx, maxy, gl, blob in rows:
    print(f"\n=== id={bid}  name={name!r}  type={t}  bbox=({minx},{miny})..({maxx},{maxy})  len={gl} ===")
    n = struct.unpack(">I", blob[:4])[0]
    print(f"  header u32_be = {n}    (so payload_pred = 4 + {n}*8 = {4+n*8})")
    # Try BE float32 pairs
    payload = blob[4:]
    if len(payload) == n * 8:
        pts = struct.unpack(f">{n*2}f", payload)
        coords = list(zip(pts[0::2], pts[1::2]))
        print(f"  -> BE float32 pairs OK, first 4: {coords[:4]}, last: {coords[-1]}")
        # bbox check
        lons = [x for x,y in coords]
        lats = [y for x,y in coords]
        print(f"  decoded bbox: lon=({min(lons)},{max(lons)})  lat=({min(lats)},{max(lats)})")
        print(f"  closed? first==last: {coords[0] == coords[-1]}")
    else:
        # Maybe per-point type byte?
        print(f"  payload {len(payload)} bytes != {n*8} bytes; trying per-node typed format")
        # BGL Little Navmap format: per node 9 bytes (1 type + 8 coords)?
        if len(payload) == n * 9:
            print(f"  -> looks like per-node typed (9 bytes/node)")
            for i in range(min(n, 5)):
                off = i * 9
                ntype = payload[off]
                lon, lat = struct.unpack(">ff", payload[off+1:off+9])
                print(f"    node {i}: type={ntype}  lon={lon}  lat={lat}")
        else:
            print("  unknown format")
            print(f"  first 64 bytes hex: {blob[:64].hex()}")
