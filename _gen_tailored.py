# -*- coding: utf-8 -*-
"""
One-off generator script: builds TMA-P tailored airspace features from
Turkiye AIP ENR 2.1.2/2.1.3 text data and appends them to
Common-Airspaces/data-sources/tailored/tailored.json.

For sectors whose lateral limit follows the FIR boundary ("ile FIR hattini
takip eder" / "and along (Turkish) FIR BDRY"), the connecting arc is spliced
in from the LTBB (ISTANBUL FIR) ring taken from
Airspaces/ICAO/FIR/fir-2021-ibosoft-tailored.json.
"""
import json
import math
import re

FIR_PATH = r"d:\ibosoft\aeronautical-charting\aeronautical-data\Airspaces\ICAO\FIR\fir-2021-ibosoft-tailored.json"
TAILORED_PATH = r"d:\ibosoft\aeronautical-charting\aeronautical-data\Airspaces\Common-Airspaces\data-sources\tailored\tailored.json"

with open(FIR_PATH, encoding="utf-8") as f:
    fir_data = json.load(f)

FIR_RINGS = {}
for feat in fir_data["features"]:
    code = feat["properties"].get("ICAOCODE")
    if code in ("LTAA", "LTBB") and code not in FIR_RINGS:
        FIR_RINGS[code] = feat["geometry"]["coordinates"][0]  # [ [lon,lat], ... ]


def dms_pair_to_lonlat(token):
    """Parse 'DDMMSSN-DDDMMSSE' -> (lon, lat) decimal degrees."""
    lat_s, lon_s = token.split("-")
    lat_deg = int(lat_s[0:2]); lat_min = int(lat_s[2:4]); lat_sec = int(lat_s[4:6])
    lat = lat_deg + lat_min / 60 + lat_sec / 3600
    if lat_s[-1] == "S":
        lat = -lat
    lon_deg = int(lon_s[0:3]); lon_min = int(lon_s[3:5]); lon_sec = int(lon_s[5:7])
    lon = lon_deg + lon_min / 60 + lon_sec / 3600
    if lon_s[-1] == "W":
        lon = -lon
    return [round(lon, 6), round(lat, 6)]


def parse_points(text):
    tokens = re.findall(r"\d{6}[NS]-\d{7}[EW]", text)
    return [dms_pair_to_lonlat(t) for t in tokens]


def haversine(a, b):
    lon1, lat1 = a; lon2, lat2 = b
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def nearest_index(ring, pt):
    best_i, best_d = 0, float("inf")
    for i, v in enumerate(ring):
        d = haversine(v, pt)
        if d < best_d:
            best_d, best_i = d, i
    return best_i, best_d


def fir_arc(fir_code, start_pt, end_pt):
    """Return list of ring points (inclusive of neither endpoint) tracing the
    shorter arc of the FIR ring from start_pt to end_pt."""
    ring = FIR_RINGS[fir_code]
    n = len(ring)
    i0, d0 = nearest_index(ring, start_pt)
    i1, d1 = nearest_index(ring, end_pt)
    # forward arc i0 -> i1
    fwd = (i1 - i0) % n
    bwd = (i0 - i1) % n
    if fwd <= bwd:
        idxs = [(i0 + k) % n for k in range(1, fwd)]
    else:
        idxs = [(i0 - k) % n for k in range(1, bwd)]
    return [ring[i] for i in idxs], d0, d1


def circle_polygon(center_lat_dms, center_lon_dms, radius_nm, n=72):
    lat0 = dms_pair_to_lonlat(f"{center_lat_dms}-{center_lon_dms}")[1]
    lon0 = dms_pair_to_lonlat(f"{center_lat_dms}-{center_lon_dms}")[0]
    R = 3440.065  # nm
    lat0r = math.radians(lat0)
    pts = []
    for i in range(n + 1):
        brg = math.radians(360 * i / n)
        lat1 = math.asin(math.sin(lat0r) * math.cos(radius_nm / R) +
                          math.cos(lat0r) * math.sin(radius_nm / R) * math.cos(brg))
        lon1 = math.radians(lon0) + math.atan2(
            math.sin(brg) * math.sin(radius_nm / R) * math.cos(lat0r),
            math.cos(radius_nm / R) - math.sin(lat0r) * math.sin(lat1))
        pts.append([round(math.degrees(lon1), 6), round(math.degrees(lat1), 6)])
    return pts


def build_polygon(points_text, close_via_fir=None):
    pts = parse_points(points_text)
    if close_via_fir:
        arc, d0, d1 = fir_arc(close_via_fir, pts[-1], pts[0])
        if max(d0, d1) > 15:
            print("WARNING large FIR snap distance", points_text[:30], d0, d1)
        pts = pts + arc
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    return [pts]


def vlim(upper, upper_uom, upper_ref, lower, lower_uom, lower_ref):
    return dict(upperLimit=upper, upperLimitUom=upper_uom, upperLimitReference=upper_ref,
                lowerLimit=lower, lowerLimitUom=lower_uom, lowerLimitReference=lower_ref)


def feature(designator, name, coords, vlims, annotation="", add_date="", controlType="APP"):
    props = {
        "type": "TMA",
        "designator": designator,
        "name": name,
        "localType": "TMA-P",
        "designatorICAO": "",
        "controlType": controlType,
        "classification": "",
    }
    props.update(vlims)
    props.update({
        "activity": "",
        "status": "",
        "purpose": "REMARK" if annotation else "",
        "annotation": annotation,
        "add_date": add_date,
    })
    return {"type": "Feature", "properties": props, "geometry": {"type": "Polygon", "coordinates": coords}}


AUG25 = "2025-08-07"
JUN25 = "2025-06-12"
MAR26 = "2026-03-19"

FIR_NOTE_TR = "Kapanis hatti Istanbul FIR (LTBB) sinirini takip eder."

features = []

# ---- MILAS APP (page 14, JUN25) ----
milas_pts = "373900N-0265827E, 373000N-0274243E, 372842N-0282418E, 372352N-0282617E, 371421N-0282817E, 370715N-0282343E, 370443N-0282204E, 365534N-0281323E, 364840N-0281025E, 364210N-0281005E, 363703N-0281108E, 363145N-0281305E"
features.append(feature("LTFEL", "MILAS APP LOWER SECTOR",
    build_polygon(milas_pts, close_via_fir="LTBB"),
    vlim("115", "FL", "STD", "0", "FT", "MSL"),
    "exclude CTRs. " + FIR_NOTE_TR, JUN25))
features.append(feature("LTFEU", "MILAS APP UPPER SECTOR",
    build_polygon(milas_pts, close_via_fir="LTBB"),
    vlim("245", "FL", "STD", "115", "FL", "STD"),
    FIR_NOTE_TR, JUN25))

# ---- DALAMAN APP (page 8, AUG25) ----
dalaman_n_pts = "370715N-0282343E, 371421N-0282817E, 372352N-0282617E, 372842N-0282418E, 374127N-0284355E, 371718N-0292922E, 365730N-0294435E, 364800N-0294516E, 364239N-0294541E, 364122N-0284655E, 364140N-0283755E"
features.append(feature("LTBSLN", "DALAMAN APP NORTH SECTOR",
    build_polygon(dalaman_n_pts),
    vlim("9500", "FT", "AMSL", "0", "FT", "MSL"),
    "", AUG25))

dalaman_s_pts = "363145N-0281305E, 363703N-0281108E, 364210N-0281005E, 364840N-0281025E, 365534N-0281323E, 370443N-0282204E, 370715N-0282343E, 364140N-0283755E, 364122N-0284655E, 364239N-0294541E, 360431N-0294833E"
features.append(feature("LTBSLS", "DALAMAN APP SOUTH SECTOR",
    build_polygon(dalaman_s_pts, close_via_fir="LTBB"),
    vlim("9500", "FT", "AMSL", "0", "FT", "MSL"),
    FIR_NOTE_TR, AUG25))

dalaman_u_pts = "363145N-0281305E, 363703N-0281108E, 364210N-0281005E, 364840N-0281025E, 365534N-0281323E, 370443N-0282204E, 370715N-0282343E, 371421N-0282817E, 372352N-0282617E, 372842N-0282418E, 374127N-0284355E, 371718N-0292922E, 365730N-0294435E, 364800N-0294516E, 364239N-0294541E, 360431N-0294833E"
features.append(feature("LTBSU", "DALAMAN APP UPPER SECTOR",
    build_polygon(dalaman_u_pts, close_via_fir="LTBB"),
    vlim("245", "FL", "STD", "9500", "FT", "AMSL"),
    FIR_NOTE_TR, AUG25))

with open(TAILORED_PATH, encoding="utf-8") as f:
    tailored = json.load(f)

tailored["features"].extend(features)

with open(TAILORED_PATH, "w", encoding="utf-8") as f:
    json.dump(tailored, f, ensure_ascii=False, indent=2)

print("Added", len(features), "features. Total now", len(tailored["features"]))
