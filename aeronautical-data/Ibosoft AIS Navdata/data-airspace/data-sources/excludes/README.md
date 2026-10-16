# data-airspace iptal kuralları

Kural biçimi (ortak): [`../../../common/README.md`](../../../common/README.md) — `match`,
`within`, `except`. Birleştirici kuralları **ana kaynaklar** yazılırken uygular;
ek kaynaklar iptal edilmez.

| Dosya | Poligon | Kural | İsabet (2026-10-15) |
|---|---|---|---:|
| `jeppesen-lt.json` | `lt-fir.geojson` — ANKARA (LTAA) + İSTANBUL (LTBB) FIR | `provider = Jeppesen`, merkez poligon içinde, adında `FREE RT` geçen hariç | 490 (+1 istisna) |
| `icao-fir-lt.json` | — | `provider = ICAO GIS`, `type = FIR`, `designator` = `LTAA` / `LTBB`. Bu iki FIR `tailored-LT` kaynağında AIP bilgileriyle elle tutulur (aynı geometri) | 2 (beklenen) |
| `jeppesen-lh.json` | `lh-fir.geojson` — BUDAPEST (LHCC) FIR | `provider = Jeppesen`, merkez poligon içinde, adında `FREE RT` geçen hariç | 162 (+1 istisna) |
| `jeppesen-p-gaza.json` | `p-gaza.geojson` — Gazze kutusu (34.10–34.70 E × 31.10–31.70 N) | `provider = Jeppesen`, `type = P`, `designator = 19`, merkez kutu içinde (Jeppesen'de P/19 12 saha var, kutu yalnız Gazze'dekini seçer) | 1 (beklenen) |
| `jeppesen-p-cyprus.json` | `p-cyprus.geojson` — Kıbrıs kutusu (32.00–34.90 E × 34.30–36.00 N) | `provider = Jeppesen`, `type = P`, `designator = 1`, merkez kutu içinde (P/1 72 saha). Yerine `tailored-LC` kaynağındaki LCP1 gelir | 1 (beklenen) |

## Köken

Eski `Common Airspaces/sources/jeppesen.py`, Jeppesen sahalarını üretirken
`data-sources/jeppesen/fir-exclude.json` (3 FIR poligonu) içinde merkezi kalan
sahaları atıyordu; adında `FREE RT` geçenleri koruyordu. Gerekçe: Türkiye ve
Macaristan sahaları kendi kaynaklarından (LT + tailored-LT, LH) gelir, Jeppesen
kopyaları çift kayıt olurdu.

Yeni sistemde bu kural üreticiden çıkarıldı ve birleştiricide iki iptal
kuralına dönüştü (kullanıcı kararı):
- Poligonlar eski `fir-exclude.json`'dan **değiştirilmeden** ikiye bölündü
  (`ICAOCODE` LTAA+LTBB → `lt-fir.geojson`, LHCC → `lh-fir.geojson`).
- Merkez, eski kodla aynı yöntemle (antimeridyen güvenli geometrinin
  `centroid`'i) hesaplanır.
- Toplam isabet **652** = eski kodun elediği sayı (ölçüldü: eski kod
  fir-exclude olmadan 36.354, ile 35.702).

## Yeni kural eklerken

1. Hangi sahaların düşeceğini önce ölçün (kural kısmi eşleşir; tek kural çok
   kayıt eleyebilir).
2. Airspace'ler arasında bugün referans yok, ama bir saha başka bir sahaya
   `contributorAirspace` ile bağlanırsa iptal `remap` üretmediği için referans
   kırılır — önce sayın.
3. Birleştirici özetinde kural başına isabet ve istisna sayıları basılır.
