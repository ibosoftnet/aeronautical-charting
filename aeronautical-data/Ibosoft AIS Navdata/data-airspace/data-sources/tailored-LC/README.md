# tailored-LC — elle düzenlenen AIXM kaynağı

`tailored-lc-airspace-aixm.xml` bu kaynağın **kendisidir**: JSON ya da üretici yoktur, dosya elle
düzenlenir (kullanıcı kararı). Provider ve originator: Ibosoft AIS; şu an 1 Airspace (LCP1).

## Düzenleme kuralları

- Biçim, alan sırası ve XML iskeletleri: [`../../docs/AIXM_Airspace_How_To_Add.md`](../../docs/AIXM_Airspace_How_To_Add.md).
- `gml:identifier` (UUID) **kalıcıdır**: mevcut kayıtta değiştirilmez; yeni
  kayda yeni bir UUID yazılır. `gml:id`'ler dosyada tekil olmalı ve `TAIL_LC_`
  önekini taşır.
- Her feature'ın TimeSlice'ının **sonunda** provenance kutusu
  (`ibosoftais:AirspaceDataProvenance`) bulunmalı; yoksa birleştirici durur.
- `name`/`localType` yalnız ASCII, ≤ 60 karakter.
- Düzenlemeden sonra doğrulayın:

```bash
py ../../../common/data_build_common/validate_aixm.py tailored-lc-airspace-aixm.xml
```

## LCP1 (P, elle eklendi)

- Kaynak: AIP Cyprus ENR 5.1-1, 09 JUL 2026 (AIRAC AIP AMDT 003/26) —
  DISCLAIMER notunda; AIP Türkiye SUP 09/25 navigational warning'i — WARNING
  notunda (tek not, paragraflar satır sonuyla ayrılır; metin verildiği gibi,
  yalnız satır sonları birleştirildi).
- `type` `P`, `designator` `LCP1`, `name` yok (kullanıcı kararı).
- Dikey sınırlar: `UNL` – `GND` (AIP'de SFC).
- Çalışma: H24 → `activation` (Timesheet `UTC` / `ANY` / 00:00–24:00,
  `status` `ACTIVE`).
- Geometri: AIP'deki 142 nokta (ilk = son, 351805N 0322140E), DMS → ondalık
  derece, 5 basamak; dış halka saat yönünün tersi (RFC 7946).
- Notlar: REMARK (havayolu / FRA kısıtı), DISCLAIMER (AIP Cyprus referansı),
  WARNING (SUP 09/25).
- Provenance: Ibosoft AIS / Ibosoft AIS / `17 OCT 2026 (Non-AIRAC)`.
- UUID: uuid5(`TailoredLcAirspace:P:LCP1`) → `5936CCBC-CE85-5DB5-9FB4-A2EC37E19732`;
  `gml:id` `TAIL_LC_AS_P_LCP1`.
- Jeppesen'deki karşılığı (P `1`, adsız, GND–UNL) birleştiricide
  [`../excludes/jeppesen-p-cyprus.json`](../excludes/jeppesen-p-cyprus.json) ile düşer.
