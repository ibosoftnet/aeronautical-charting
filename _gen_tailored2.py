# -*- coding: utf-8 -*-
"""Second batch: Yesilkoy (South+North), Antalya, Menderes, Ankara TMA."""
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
        FIR_RINGS[code] = feat["geometry"]["coordinates"][0]


def dms_pair_to_lonlat(token):
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
    ring = FIR_RINGS[fir_code]
    n = len(ring)
    i0, d0 = nearest_index(ring, start_pt)
    i1, d1 = nearest_index(ring, end_pt)
    fwd = (i1 - i0) % n
    bwd = (i0 - i1) % n
    if fwd <= bwd:
        idxs = [(i0 + k) % n for k in range(1, fwd)]
    else:
        idxs = [(i0 - k) % n for k in range(1, bwd)]
    return [ring[i] for i in idxs], d0, d1


def build_polygon(points_text, close_via_fir=None):
    pts = parse_points(points_text)
    if close_via_fir:
        arc, d0, d1 = fir_arc(close_via_fir, pts[-1], pts[0])
        if max(d0, d1) > 15:
            print("WARNING large FIR snap distance", points_text[:40], d0, d1)
        pts = pts + arc
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    return [pts]


def circle_polygon(dms_center_lat, dms_center_lon, radius_nm, n=72):
    lon0, lat0 = dms_pair_to_lonlat(f"{dms_center_lat}-{dms_center_lon}")
    R = 3440.065
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

# ================= YESILKOY SOUTH CONFIGURATION (page 9-11, AUG25) =================
sc_scf = "414215N-0283630E, 414230N-0285218E, 414020N-0290036E, 414000N-0284716E, 413550N-0284403E, 411700N-0284423E, 411657N-0284304E, 413455N-0284244E, 413730N-0284002E, 413808N-0282152E"
features.append(feature("LTFMSSCF", "YESILKOY SOUTH APP CENTER FINAL SCF", build_polygon(sc_scf),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

sc_sef = "411700N-0284423E, 411705N-0284702E, 412934N-0284654E, 412949N-0285356E, 414020N-0290036E, 414000N-0284716E, 413550N-0284403E"
features.append(feature("LTFMSSEF", "YESILKOY SOUTH APP EAST FINAL SEF", build_polygon(sc_sef),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

sc_sed = "414020N-0290036E, 414339N-0293138E, 413223N-0293142E, 412358N-0292817E, 411704N-0292203E, 410938N-0290951E, 412949N-0285356E"
features.append(feature("LTFMSSED", "YESILKOY SOUTH APP EAST DIRECTORY SED", build_polygon(sc_sed),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

sc_swf = "411657N-0284304E, 411648N-0283906E, 412728N-0283835E, 412726N-0282800E, 413808N-0282152E, 413730N-0284002E, 413455N-0284244E"
features.append(feature("LTFMSSWF", "YESILKOY SOUTH APP WEST FINAL SWF", build_polygon(sc_swf),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "", AUG25))

sc_swd = "413808N-0282152E, 412726N-0282800E, 410743N-0281106E, 411632N-0275830E, 412230N-0275323E, 413100N-0275026E, 414229N-0275106E"
features.append(feature("LTFMSSWD", "YESILKOY SOUTH APP WEST DIRECTORY SWD", build_polygon(sc_swd),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

sc_sag = "410235N-0293118E, 410350N-0293934E, 412713N-0294916E, 412302N-0300032E, 411759N-0300753E, 411133N-0301238E, 410422N-0301446E, 405403N-0300941E, 405904N-0294923E, 405243N-0293130E, 404331N-0290901E, 404944N-0290716E, 405152N-0290300E"
features.append(feature("LTFMSSAG", "YESILKOY SOUTH APP GOKCEN SAG", build_polygon(sc_sag),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

sc_sad = "405257N-0280805E, 404445N-0283011E, 404539N-0284340E, 405118N-0290752E, 410938N-0290351E, 411256N-0290350E, 411722N-0290349E, 412949N-0285356E, 412934N-0284654E, 411705N-0284702E, 411700N-0284306E, 411304N-0284312E, 411008N-0283901E"
features.append(feature("LTFMSSAD", "YESILKOY SOUTH APP EAST DEPARTURE SAD", build_polygon(sc_sad),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

sc_sbd = "411648N-0283906E, 412728N-0283835E, 412726N-0282800E, 411227N-0281509E, 410903N-0281822E, 411008N-0283901E, 411700N-0284306E"
features.append(feature("LTFMSSBD", "YESILKOY SOUTH APP WEST DEPARTURE SBD", build_polygon(sc_sbd),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

sc_sec = "410422N-0301446E, 405403N-0300941E, 404700N-0300000E, 404231N-0290901E, 404554N-0284147E, 410315N-0283910E, 411257N-0283907E, 411256N-0290349E, 411304N-0292335E, 412200N-0300211E, 411036N-0304446E, 410717N-0304354E, 410328N-0304258E"
features.append(feature("LTFMSSEC", "YESILKOY SOUTH APP EAST CENTER SEC", build_polygon(sc_sec),
    vlim("185", "FL", "STD", "0", "FT", "MSL"), "Exclude CTRs, TMAs, MTMAs and SED, SAD, SAG sectors", AUG25))

sc_ses = "404554N-0284147E, 404331N-0290901E, 404700N-0300000E, 405403N-0300941E, 410422N-0301446E, 411500N-0304600E, 405156N-0303958E, 403753N-0304241E, 402859N-0304423E, 401848N-0304620E, 395456N-0295558E, 395453N-0295212E, 395325N-0294307E, 395434N-0293232E, 395424N-0292242E, 395356N-0285958E, 401556N-0285958E, 402710N-0284400E"
features.append(feature("LTFMSSES", "YESILKOY SOUTH APP EAST SOUTH SES", build_polygon(sc_ses),
    vlim("185", "FL", "STD", "0", "FT", "MSL"), "Exclude CTRs, TMAs, MTMAs", AUG25))

sc_sen = "411257N-0283907E, 411648N-0283906E, 411657N-0284304E, 414101N-0284233E, 420332N-0284207E, 420700N-0290000E, 422150N-0293727E, 422128N-0294125E, 420609N-0303212E, 415952N-0303418E, 414512N-0303725E, 413528N-0304027E, 411036N-0304446E, 412200N-0300211E, 411304N-0292335E, 411256N-0290349E"
features.append(feature("LTFMSSEN", "YESILKOY SOUTH APP EAST NORTH SEN", build_polygon(sc_sen, close_via_fir="LTBB"),
    vlim("245", "FL", "STD", "0", "FT", "MSL"), "Exclude CTRs, TMAs, MTMAs and SED, SEF, SWF, SAD, SAG sectors. " + FIR_NOTE_TR, AUG25))

sc_seu = "404554N-0284147E, 410315N-0283910E, 411257N-0283907E, 411256N-0290349E, 411304N-0292335E, 412200N-0300211E, 411036N-0304446E, 410717N-0304354E, 410328N-0304258E, 405156N-0303958E, 403753N-0304241E, 402859N-0304423E, 401848N-0304620E, 395456N-0295558E, 395453N-0295212E, 395325N-0294307E, 395434N-0293232E, 395424N-0292242E, 395356N-0285958E, 401556N-0285958E, 402710N-0284400E"
features.append(feature("LTFMSSEU", "YESILKOY SOUTH APP EAST UPPER SEU", build_polygon(sc_seu),
    vlim("245", "FL", "STD", "185", "FL", "STD"), "Exclude CTRs, TMAs, MTMAs", AUG25))

sc_swn = "411556N-0262432E, 411809N-0272156E, 411603N-0273655E, 411257N-0283907E, 411648N-0283906E, 411657N-0284304E, 414101N-0284233E, 420332N-0284207E"
features.append(feature("LTFMSSWN", "YESILKOY SOUTH APP WEST NORTH SWN", build_polygon(sc_swn, close_via_fir="LTBB"),
    vlim("185", "FL", "STD", "0", "FT", "MSL"), "Exclude CTRs, TMAs, MTMAs and SWD, SWF, SAD sectors. " + FIR_NOTE_TR, AUG25))

sc_sws = "403945N-0255630E, 401300N-0270900E, 401255N-0271637E, 401256N-0272812E, 401256N-0273158E, 395056N-0273158E, 395156N-0275943E, 395622N-0281100E, 395356N-0285958E, 401556N-0285958E, 402710N-0284400E, 404554N-0284147E, 410315N-0283910E, 411257N-0283907E, 411603N-0273655E, 411809N-0272156E, 411556N-0262432E"
features.append(feature("LTFMSSWS", "YESILKOY SOUTH APP WEST SOUTH SWS", build_polygon(sc_sws, close_via_fir="LTBB"),
    vlim("185", "FL", "STD", "0", "FT", "MSL"), "Exclude CTRs, TMAs, MTMAs and SWD, SAD sectors. " + FIR_NOTE_TR, AUG25))

sc_swu = "403945N-0255630E, 401300N-0270900E, 401255N-0271637E, 401256N-0272812E, 401256N-0273158E, 395056N-0273158E, 395156N-0275943E, 395622N-0281100E, 395356N-0285958E, 401556N-0285958E, 402710N-0284400E, 404554N-0284147E, 410315N-0283910E, 411648N-0283906E, 411657N-0284304E, 414101N-0284233E, 420332N-0284207E"
features.append(feature("LTFMSSWU", "YESILKOY SOUTH APP WEST UPPER SWU", build_polygon(sc_swu, close_via_fir="LTBB"),
    vlim("245", "FL", "STD", "185", "FL", "STD"), "Exclude CTRs, TMAs, MTMAs. " + FIR_NOTE_TR, AUG25))

# ================= YESILKOY NORTH CONFIGURATION (page 11-13) =================
nc_scf = "411659N-0284423E, 411657N-0284304E, 405836N-0284304E, 405630N-0284108E, 405257N-0280805E, 404445N-0283011E, 404539N-0284340E, 405118N-0290752E, 405245N-0285018E, 405751N-0284510E"
features.append(feature("LTFMNSCF", "YESILKOY NORTH APP CENTER FINAL SCF", build_polygon(nc_scf),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

nc_sef = "405118N-0290752E, 405245N-0285018E, 405751N-0284510E, 411659N-0284423E, 411705N-0284702E, 410333N-0284729E, 410938N-0290351E"
features.append(feature("LTFMNSEF", "YESILKOY NORTH APP EAST FINAL SEF", build_polygon(nc_sef),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

nc_sed = "410347N-0285404E, 412454N-0290912E, 411704N-0292203E, 411047N-0292751E, 410235N-0293118E, 405243N-0293130E, 405152N-0290300E"
features.append(feature("LTFMNSED", "YESILKOY NORTH APP EAST DIRECTORY SED", build_polygon(nc_sed),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

nc_swf = "405836N-0284319E, 405630N-0284108E, 405257N-0280805E, 410903N-0281822E, 410307N-0283537E, 410315N-0283910E, 411648N-0283906E, 411657N-0284304E"
features.append(feature("LTFMNSWF", "YESILKOY NORTH APP WEST FINAL SWF", build_polygon(nc_swf),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

nc_swd = "410633N-0282832E, 405544N-0282230E, 405110N-0275210E, 410246N-0275129E, 411103N-0275418E, 411632N-0275830E, 412613N-0281135E"
features.append(feature("LTFMNSWD", "YESILKOY NORTH APP WEST FINAL SWD", build_polygon(nc_swd),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

nc_sag = "404331N-0290901E, 403559N-0291104E, 402224N-0291533E, 402108N-0285912E, 402227N-0285052E, 403835N-0282745E, 404226N-0282640E, 405152N-0290300E, 410235N-0293118E, 405243N-0293130E"
features.append(feature("LTFMNSAG", "YESILKOY NORTH APP GOKCEN SAG", build_polygon(nc_sag),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

nc_sad = "414215N-0283630E, 414230N-0285218E, 414020N-0290036E, 412949N-0285356E, 411722N-0290349E, 410938N-0290351E, 410333N-0284729E, 411705N-0284702E, 411657N-0284304E, 412329N-0284304E, 413828N-0282424E"
features.append(feature("LTFMNSAD", "YESILKOY NORTH APP EAST DEPARTURE SAD", build_polygon(nc_sad),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

nc_sbd = "411657N-0284304E, 411648N-0283906E, 410315N-0283910E, 410307N-0283537E, 410903N-0281822E, 411227N-0281509E, 412726N-0282800E, 413808N-0282152E, 413828N-0282424E, 412329N-0284304E"
features.append(feature("LTFMNSBD", "YESILKOY NORTH APP WEST DEPARTURE SBD", build_polygon(nc_sbd),
    vlim("11500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTRs", AUG25))

nc_sec = "411036N-0304446E, 410717N-0304354E, 410328N-0304258E, 405156N-0303958E, 403753N-0304241E, 402344N-0304523E, 402330N-0302130E, 402326N-0301043E, 402200N-0295900E, 403300N-0294600E, 402710N-0284400E, 404554N-0284147E, 410315N-0283910E, 411257N-0283907E, 411256N-0290349E, 411304N-0292335E, 412200N-0300211E"
features.append(feature("LTFMNSEC", "YESILKOY NORTH APP EAST CENTER SEC", build_polygon(nc_sec),
    vlim("185", "FL", "STD", "0", "FT", "MSL"), "Exclude CTRs, TMAs, MTMAs and SED, SAD, SAG, SEF, SWF sectors", AUG25))

nc_ses = "402326N-0301043E, 402330N-0302130E, 402344N-0304523E, 401328N-0304258E, 395456N-0295558E, 395453N-0295212E, 395325N-0294307E, 395434N-0293232E, 395424N-0292242E, 395356N-0285958E, 401556N-0285958E, 402710N-0284400E, 403300N-0294600E, 402200N-0295958E"
features.append(feature("LTFMNSES", "YESILKOY NORTH APP EAST SOUTH SES", build_polygon(nc_ses),
    vlim("185", "FL", "STD", "0", "FT", "MSL"), "Exclude CTRs, TMAs, MTMAs and SAG sector", AUG25))

nc_sen = "411257N-0283907E, 411648N-0283906E, 411657N-0284304E, 414101N-0284233E, 420332N-0284207E, 420700N-0290000E, 422150N-0293727E, 422128N-0294125E, 420609N-0303212E, 415952N-0303418E, 414512N-0303725E, 413528N-0304027E, 411036N-0304446E, 412200N-0300211E, 411304N-0292335E, 411256N-0290349E"
features.append(feature("LTFMNSEN", "YESILKOY NORTH APP EAST NORTH SEN", build_polygon(nc_sen, close_via_fir="LTBB"),
    vlim("245", "FL", "STD", "0", "FT", "MSL"), "Exclude CTRs, TMAs, MTMAs and SED, SEF, SAD sectors. " + FIR_NOTE_TR, AUG25))

nc_seu = "404554N-0284147E, 410315N-0283910E, 411257N-0283907E, 411256N-0290349E, 411304N-0292335E, 412200N-0300211E, 411036N-0304446E, 410717N-0304354E, 410328N-0304258E, 405156N-0303958E, 403753N-0304241E, 402859N-0304423E, 401848N-0304620E, 395456N-0295558E, 395453N-0295212E, 395325N-0294307E, 395434N-0293232E, 395424N-0292242E, 395356N-0285958E, 401556N-0285958E, 402710N-0284400E"
features.append(feature("LTFMNSEU", "YESILKOY NORTH APP EAST UPPER SEU", build_polygon(nc_seu),
    vlim("245", "FL", "STD", "185", "FL", "STD"), "Exclude CTRs, TMAs, MTMAs", AUG25))

nc_swn = "411556N-0262432E, 411809N-0272156E, 411603N-0273655E, 411257N-0283907E, 411648N-0283906E, 411657N-0284304E, 414101N-0284233E, 420332N-0284207E"
features.append(feature("LTFMNSWN", "YESILKOY NORTH APP WEST NORTH SWN", build_polygon(nc_swn, close_via_fir="LTBB"),
    vlim("185", "FL", "STD", "0", "FT", "MSL"), "Exclude CTRs, TMAs, MTMAs and SWD, SWF, SAD sectors. " + FIR_NOTE_TR, JUN25))

nc_sws = "403945N-0255630E, 401300N-0270900E, 401255N-0271637E, 401256N-0272812E, 401256N-0273158E, 395056N-0273158E, 395156N-0275943E, 395622N-0281100E, 395356N-0285958E, 401556N-0285958E, 402710N-0284400E, 404554N-0284147E, 410315N-0283910E, 411257N-0283907E, 411603N-0273655E, 411809N-0272156E, 411556N-0262432E"
features.append(feature("LTFMNSWS", "YESILKOY NORTH APP WEST SOUTH SWS", build_polygon(nc_sws, close_via_fir="LTBB"),
    vlim("185", "FL", "STD", "0", "FT", "MSL"), "Exclude CTRs, TMAs, MTMAs and SWD, SAD sectors. " + FIR_NOTE_TR, JUN25))

nc_swu = "403945N-0255630E, 401300N-0270900E, 401255N-0271637E, 401256N-0272812E, 401256N-0273158E, 395056N-0273158E, 395156N-0275943E, 395622N-0281100E, 395356N-0285958E, 401556N-0285958E, 402710N-0284400E, 404554N-0284147E, 410315N-0283910E, 411648N-0283906E, 411657N-0284304E, 414101N-0284233E, 420332N-0284207E"
features.append(feature("LTFMNSWU", "YESILKOY NORTH APP WEST UPPER SWU", build_polygon(nc_swu, close_via_fir="LTBB"),
    vlim("245", "FL", "STD", "185", "FL", "STD"), "Exclude CTRs, TMAs, MTMAs. " + FIR_NOTE_TR, AUG25))

# ================= ANTALYA APP (page 7 MAR26 / page 8 AUG25) =================
an_ycr = "364737N-0294516E, 364239N-0294541E, 360433N-0294837E, 360412N-0300000E, 364916N-0300000E, 380934N-0303721E, 380649N-0300322E, 375918N-0300359E, 375422N-0300008E, 372950N-0300428E, 365730N-0294435E"
features.append(feature("LTAIYCR", "ANTALYA APP CARDAK UPPER YCR", build_polygon(an_ycr),
    vlim("245", "FL", "STD", "0", "FT", "AMSL"), "exclude CTR, MTMA", MAR26))

an_yem_yeu = "375351N-0313225E, 373422N-0320416E, 365305N-0320633E, 365249N-0322015E, 365240N-0322839E, 365200N-0323540E, 355814N-0323648E, 360010N-0315539E, 360226N-0304928E, 360248N-0304214E, 362337N-0304127E, 364137N-0304039E, 365416N-0304020E, 370150N-0304130E, 373500N-0304000E, 380934N-0303721E, 381926N-0311614E"
features.append(feature("LTAIYEM", "ANTALYA APP EAST MIDDLE YEM", build_polygon(an_yem_yeu),
    vlim("185", "FL", "STD", "0", "FT", "AMSL"), "exclude CTRs and Lower North, Lower Southwest, Lower Southeast sectors", MAR26))
features.append(feature("LTAIYEU", "ANTALYA APP EAST UPPER YEU", build_polygon(an_yem_yeu),
    vlim("245", "FL", "STD", "185", "FL", "STD"), "", MAR26))

an_ynl = "365416N-0304125E, 365403N-0304803E, 365352N-0305353E, 370200N-0305730E, 373300N-0310600E, 373500N-0304000E, 370150N-0304130E, 365416N-0304020E"
features.append(feature("LTAIYNL", "ANTALYA APP NORTH LOWER YNL", build_polygon(an_ynl),
    vlim("11500", "FT", "AMSL", "0", "FT", "AMSL"),
    "exclude CTRs. Used as Final Approach Directory Sector when landing direction is 18; used as DEPARTURE Sector when landing direction is 36", MAR26))

an_ywm_ywu = "364137N-0304039E, 362337N-0304127E, 360248N-0304214E, 360412N-0300000E, 364916N-0300000E, 380934N-0303721E, 373500N-0304000E, 370150N-0304130E, 365416N-0304020E"
features.append(feature("LTAIYWM", "ANTALYA APP WEST MIDDLE YWM", build_polygon(an_ywm_ywu),
    vlim("185", "FL", "STD", "0", "FT", "AMSL"), "exclude CTR", MAR26))
features.append(feature("LTAIYWU", "ANTALYA APP WEST UPPER YWU", build_polygon(an_ywm_ywu),
    vlim("245", "FL", "STD", "185", "FL", "STD"), "", MAR26))

an_ywl = "365416N-0304125E, 365403N-0304803E, 370200N-0304900E, 370150N-0304130E, 365416N-0304020E"
features.append(feature("LTAIYWL", "ANTALYA APP SOUTHWEST LOWER YWL", build_polygon(an_ywl),
    vlim("11500", "FT", "AMSL", "0", "FT", "AMSL"),
    "exclude CTRs. Used as Final Approach Directory Sector when landing direction is 36 combined with SOUTHEAST LOWER sector; used as DEPARTURE Sector when landing direction is 18 combined with SOUTHEAST LOWER sector", AUG25))

an_yel = "365352N-0305353E, 365403N-0304803E, 370200N-0304900E, 370200N-0305730E"
features.append(feature("LTAIYEL", "ANTALYA APP SOUTHEAST LOWER YEL", build_polygon(an_yel),
    vlim("11500", "FT", "AMSL", "0", "FT", "AMSL"),
    "exclude CTRs. Used as Final Approach Directory Sector when landing direction is 36 combined with SOUTHWEST LOWER sector; used as DEPARTURE Sector when landing direction is 18 combined with SOUTHWEST LOWER sector", AUG25))

# ================= MENDERES APP (page 13, JUN25) =================
me_final = "383837N-0264258E, 384711N-0270334E, 384438N-0272611E, 382000N-0273130E, 375612N-0273647E, 374805N-0271704E, 375047N-0270126E, 375500N-0265300E, 381500N-0264830E"
features.append(feature("LTBJF", "MENDERES APP FINAL SECTOR", build_polygon(me_final),
    vlim("9500", "FT", "AMSL", "0", "FT", "MSL"), "exclude CTR. See note (9) re Cigli approach restrictions", JUN25))

me_lower = "391658N-0263154E, 392956N-0271328E, 395056N-0273158E, 395156N-0275943E, 395622N-0281100E, 395356N-0285958E, 390457N-0285953E, 383753N-0290711E, 380416N-0291931E, 372842N-0282418E, 373000N-0274243E, 373900N-0265827E"
features.append(feature("LTBJL", "MENDERES APP LOWER SECTOR", build_polygon(me_lower, close_via_fir="LTBB"),
    vlim("155", "FL", "STD", "0", "FT", "MSL"), "exclude CTRs, MTMA and Final Sector. " + FIR_NOTE_TR, JUN25))

me_upper_e = "395056N-0273158E, 395156N-0275943E, 395622N-0281100E, 395356N-0285958E, 390457N-0285953E, 383753N-0290711E, 380416N-0291931E, 372842N-0282418E, 373000N-0274243E, 375445N-0272515E, 380657N-0272453E, 381843N-0272905E, 382900N-0273300E, 383900N-0272000E, 395056N-0273158E"
features.append(feature("LTBJUE", "MENDERES APP UPPER EAST", build_polygon(me_upper_e),
    vlim("245", "FL", "STD", "155", "FL", "STD"), "exclude CTR, MTMA", JUN25))

me_upper_w = "391658N-0263154E, 392335N-0265300E, 392956N-0271328E, 395056N-0273158E, 383900N-0272000E, 382900N-0273300E, 381843N-0272905E, 380657N-0272453E, 375445N-0272515E, 373000N-0274243E, 373900N-0265827E"
features.append(feature("LTBJUW", "MENDERES APP UPPER WEST", build_polygon(me_upper_w, close_via_fir="LTBB"),
    vlim("245", "FL", "STD", "155", "FL", "STD"), "exclude MTMA. " + FIR_NOTE_TR, JUN25))

# ================= ANKARA TMA (page 7, MAR26) - circular =================
features.append(feature("LTACL", "ANKARA TMA LOWER", circle_polygon("400340N", "0325558E", 42),
    vlim("145", "FL", "STD", "4500", "FT", "AMSL"), "Merkezi 400340N-0325558E, Yaricapi 42 NM", MAR26, "APP"))
features.append(feature("LTACU", "ANKARA TMA UPPER", circle_polygon("400340N", "0325558E", 42),
    vlim("245", "FL", "STD", "145", "FL", "STD"), "Merkezi 400340N-0325558E, Yaricapi 42 NM", MAR26, "APP"))

print("prepared", len(features), "features")

with open(TAILORED_PATH, encoding="utf-8") as f:
    tailored = json.load(f)

existing_designators = {ft["properties"].get("designator") for ft in tailored["features"]}
added = 0
for ft in features:
    d = ft["properties"]["designator"]
    if d in existing_designators:
        print("SKIP duplicate", d)
        continue
    tailored["features"].append(ft)
    added += 1

with open(TAILORED_PATH, "w", encoding="utf-8") as f:
    json.dump(tailored, f, ensure_ascii=False, indent=2)

print("Added", added, "features. Total now", len(tailored["features"]))
