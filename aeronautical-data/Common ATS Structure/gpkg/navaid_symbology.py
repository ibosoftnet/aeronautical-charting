"""AŞAMA 2B — `navaidSymbology_*`: sembol geometrisi için türetilmiş alanlar.

`navaidLabeling_*`'tan **ayrı bir ailedir**: o etiket metnini üretir, bu
sembolün nasıl çizileceğini besler. İkisi farklı sorulara cevap verdiği için
önekleri de ayrıdır.

Şu an tek alan var:

`navaidSymbology_GPAssociatedLOCTrueBrg`
    Glidepath sembolü haritada bir **hüzme** olarak çizilir ve bu hüzmenin bir
    yönü olmalıdır. Ama `GlidepathPropertyGroup`'ta yön alanı **yoktur**
    (frequency, slope, rdh, signalPerformance, courseQuality, integrityLevel).
    Yön, aynı ILS'in **Localizer** bileşenindeki `trueBearing`'dir; bu alan o
    değeri Glidepath satırına taşır.

`navaid_labeling` ile paylaşılan durum yoktur — modül kendi sorgusunu yapar.
`schema.finalize`'dan ÖNCE çalışmalıdır (sütunun B-tree index'i orada
kuruluyor).
"""

from gpkg import schema

#: Yönü taşıyan (kaynak) ve yönü devralan (hedef) ekipman türleri.
_SOURCE_KIND = "Localizer"
_TARGET_KIND = "Glidepath"

_BEARING_COLUMN = schema.equipment_column(_SOURCE_KIND, "trueBearing")


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
