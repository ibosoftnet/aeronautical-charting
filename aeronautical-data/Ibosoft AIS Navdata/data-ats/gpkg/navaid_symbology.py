"""AŞAMA 2B — `navaidSymbology_*`: sembol geometrisi için türetilmiş alanlar.

`navaidLabeling_*`'tan **ayrı bir ailedir**: o etiket metnini üretir, bu
sembolün nasıl çizileceğini besler. İkisi farklı sorulara cevap verdiği için
önekleri de ayrıdır.

İki alan var:

`navaidSymbology_GPAssociatedLOCTrueBrg` (yalnızca `navaidComponents`)
    Glidepath sembolü haritada bir **hüzme** olarak çizilir ve bu hüzmenin bir
    yönü olmalıdır. Ama `GlidepathPropertyGroup`'ta yön alanı **yoktur**
    (frequency, slope, rdh, signalPerformance, courseQuality, integrityLevel).
    Yön, aynı ILS'in **Localizer** bileşenindeki `trueBearing`'dir; bu alan o
    değeri Glidepath satırına taşır.

`navaidSymbology_declination` (`navaids` ve `navaidComponents`)
    Pusula gülü (compass rose) sembolünün DÖNDÜRME AÇISI. Yalnızca VOR/TACAN
    bileşenlerinin AIXM'de kendi `declination` alanı vardır; bileşen
    düzeyinde değer o bileşenin KENDİ sütunundan (`navaidComponents_VOR_` /
    `_TACAN_declination`) birebir devralınır. `navaids` düzeyinde yalnızca
    VOR/VOR_DME/TACAN/VORTAC türlerinde doldurulur (kullanıcı kararı);
    VORTAC'ta VOR bileşeninin değeri varsa o, yoksa TACAN'ınki kullanılır
    (kullanıcı kararı — bugün veride ikisi hiç aynı anda dolu değil, ama
    kural gelecekteki veri için de geçerli).

`navaid_labeling` ile paylaşılan durum yoktur — modül kendi sorgusunu yapar.
`schema.finalize`'dan ÖNCE çalışmalıdır (sütunların B-tree index'i orada
kuruluyor).
"""

from gpkg import schema

#: Yönü taşıyan (kaynak) ve yönü devralan (hedef) ekipman türleri.
_SOURCE_KIND = "Localizer"
_TARGET_KIND = "Glidepath"

_BEARING_COLUMN = schema.equipment_column(_SOURCE_KIND, "trueBearing")

#: `declination` tasiyan tek iki alt-tur (Localizer'in de declination'i AIXM'de
#: var ama pusula gulu kapsaminda DEGIL — yalnizca VOR/TACAN/VORTAC/VOR_DME
#: navaid turleri istendi, kullanici karari).
_DECLINATION_EQUIPMENT = ("VOR", "TACAN")

#: `navaids_type` -> hangi bilesen(ler)den declination alinacagi, SIRAYLA
#: denenir; ilk DEGERI DOLU olan kazanir. `VOR_DME` icin DME'nin AIXM'de
#: declination alani yok, tek kaynak VOR'dur. `VORTAC` icin VOR varsa VOR,
#: yoksa TACAN (kullanici karari).
_DECLINATION_SOURCE = {
    "VOR": ("VOR",),
    "VOR_DME": ("VOR",),
    "TACAN": ("TACAN",),
    "VORTAC": ("VOR", "TACAN"),
}


def _parse_ids(value):
    """`"550,2181"` → `[550, 2181]`. Boş/None → boş liste.

    `associatedNavaid` virgüllü bir LİSTEDİR: bir ekipman birden fazla Navaid
    tarafından paylaşılabiliyor.
    """
    if not value:
        return []
    out = []
    for part in str(value).split(schema.LIST_SEPARATOR):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def compute(con, log=None):
    """`navaidSymbology_*` alanlarının tamamını türetir (iki bağımsız alan)."""
    gp = _compute_gp_bearing(con, log)
    decl = _compute_declination(con, log)
    return {**gp, **decl}


def _compute_gp_bearing(con, log=None):
    """Glidepath satırlarına kardeş Localizer'ın `trueBearing`'ini taşır."""
    cur = con.cursor()

    # ── 1. ebeveyn navaid → Localizer trueBearing haritası ──────────────────
    cur.execute(
        f'SELECT associatedNavaid, "{_BEARING_COLUMN}", aixm_gml_id'
        ' FROM navaidComponents WHERE navaidComponents_equipmentType = ?',
        (_SOURCE_KIND,))
    by_navaid, cakisma = {}, 0
    for navaid_ids, bearing, gml_id in cur.fetchall():
        if bearing is None:
            continue
        for parent in _parse_ids(navaid_ids):
            if parent in by_navaid:
                # Bir navaid'in birden fazla Localizer'i olursa ILKI alinir.
                # Veride boyle bir kayit yok; olursa gorunur olsun diye
                # loglanir — sessizce birini secmeyelim.
                cakisma += 1
                if log is not None:
                    log.warning("2B", "navaidComponents", gml_id,
                                "navaidSymbology_GPAssociatedLOCTrueBrg",
                                bearing, "navaidde_birden_fazla_localizer")
                continue
            by_navaid[parent] = bearing

    # ── 2. Glidepath satırlarına yaz ────────────────────────────────────────
    cur.execute(
        'SELECT id, associatedNavaid FROM navaidComponents'
        ' WHERE navaidComponents_equipmentType = ?', (_TARGET_KIND,))
    payload, hedef, eksik = [], 0, 0
    for row_id, navaid_ids in cur.fetchall():
        hedef += 1
        bearing = None
        for parent in _parse_ids(navaid_ids):
            if parent in by_navaid:
                bearing = by_navaid[parent]
                break
        if bearing is None:
            # Kardes Localizer VAR ama `trueBearing` bos: bazi ulkeler bu
            # alani raporlamiyor. HATA DEGILDIR (kullanici teyidi), bu yuzden
            # `errored-features.csv`'ye satir yazilmaz, yalnizca sayilir.
            #
            # Manyetik->gercek cevrimi YAPILMAZ: `magneticBearing` +
            # `magneticVariation` ile birkac yuz satir daha doldurulabilirdi
            # ama istenen alan `trueBearing`'dir ve izinsiz fallback kurulmaz.
            eksik += 1
            if log is not None:
                log.info_count("gp_loc_true_bearing_kaynakta_yok")
            continue
        payload.append((bearing, row_id))

    if payload:
        cur.executemany(
            'UPDATE "navaidComponents"'
            ' SET "navaidSymbology_GPAssociatedLOCTrueBrg" = ? WHERE id = ?',
            payload)
    con.commit()

    print(f"    Glidepath={hedef} LOC yonu yazilan={len(payload)} "
          f"(kaynakta yon yok={eksik})")
    return {"glidepath": hedef, "yazilan": len(payload),
            "yon_yok": eksik, "cakisma": cakisma}


def _compute_declination(con, log=None):
    """`navaidSymbology_declination` — pusula gülü döndürme açısı.

    İki geçiş: önce `navaidComponents` (kendi alt-tür sütunundan birebir
    kopya, VOR/TACAN dışında dokunulmaz), sonra `navaids` (VOR/VOR_DME/
    TACAN/VORTAC türleri, `_DECLINATION_SOURCE` sırasına göre bileşenden
    devralınır).
    """
    cur = con.cursor()
    vor_col = schema.equipment_column("VOR", "declination")
    tacan_col = schema.equipment_column("TACAN", "declination")

    # ── 1. navaidComponents: kendi alt-türünün declination'ı, birebir ───────
    cur.execute(
        f'SELECT id, navaidComponents_equipmentType, "{vor_col}", "{tacan_col}",'
        ' associatedNavaid FROM navaidComponents'
        ' WHERE navaidComponents_equipmentType IN (?, ?)', _DECLINATION_EQUIPMENT)
    payload, by_navaid = [], {}
    for row_id, kind, vor_decl, tacan_decl, navaid_ids in cur.fetchall():
        value = vor_decl if kind == "VOR" else tacan_decl
        if value is not None:
            payload.append((value, row_id))
        for parent in _parse_ids(navaid_ids):
            by_navaid.setdefault(parent, {})[kind] = value

    if payload:
        cur.executemany(
            'UPDATE "navaidComponents" SET "navaidSymbology_declination" = ?'
            ' WHERE id = ?', payload)

    # ── 2. navaids: VOR/VOR_DME/TACAN/VORTAC, bileşenden devral ─────────────
    cur.execute(
        'SELECT id, navaids_type, aixm_gml_id FROM navaids'
        ' WHERE navaids_type IN (?, ?, ?, ?)', tuple(_DECLINATION_SOURCE))
    nav_payload, bilesen_yok, kaynakta_yok = [], 0, 0
    for row_id, nav_type, gml_id in cur.fetchall():
        components = by_navaid.get(row_id, {})
        value, kaynak_var = None, False
        for kind in _DECLINATION_SOURCE[nav_type]:
            if kind in components:
                kaynak_var = True
                if components[kind] is not None:
                    value = components[kind]
                    break
        if value is not None:
            nav_payload.append((value, row_id))
        elif not kaynak_var:
            # Beklenen VOR/TACAN bileseni navaid'e HIC bagli degil — veri
            # butunlugu sorunu, sessizce gecilmez.
            bilesen_yok += 1
            if log is not None:
                log.warning("2B", "navaids", gml_id,
                            "navaidSymbology_declination", None,
                            "declination_bileseni_yok")
        else:
            # Bilesen var ama declination kaynakta raporlanmamis. HATA
            # DEGILDIR (Glidepath/trueBearing ile ayni durum) — bazi
            # ulkeler bu alani vermiyor.
            kaynakta_yok += 1
            if log is not None:
                log.info_count("declination_kaynakta_yok")

    if nav_payload:
        cur.executemany(
            'UPDATE "navaids" SET "navaidSymbology_declination" = ?'
            ' WHERE id = ?', nav_payload)

    con.commit()
    print(f"    declination: navaidComponents={len(payload)} "
          f"navaids={len(nav_payload)} (bilesen yok={bilesen_yok}, "
          f"kaynakta yok={kaynakta_yok})")
    return {"declination_navaidComponents": len(payload),
            "declination_navaids": len(nav_payload),
            "declination_bilesen_yok": bilesen_yok,
            "declination_kaynakta_yok": kaynakta_yok}
