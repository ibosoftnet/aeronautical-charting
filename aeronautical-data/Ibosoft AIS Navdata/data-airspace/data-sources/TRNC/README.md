# TRNC — elle düzenlenen AIXM kaynağı

`trnc-airspace-aixm.xml` bu kaynağın **kendisidir**: JSON ya da üretici yoktur, dosya elle
düzenlenir (kullanıcı kararı). Originator: KKTC SHD; 11 Airspace (ilk hâli eski
`Common Airspaces` tailored.json'dan üretildi).

## Düzenleme kuralları

- Biçim, alan sırası ve XML iskeletleri: [`../../docs/AIXM_Airspace_How_To_Add.md`](../../docs/AIXM_Airspace_How_To_Add.md).
- `gml:identifier` (UUID) **kalıcıdır**: mevcut kayıtta değiştirilmez; yeni
  kayda yeni bir UUID yazılır. `gml:id`'ler dosyada tekil olmalı.
- Her feature'ın TimeSlice'ının **sonunda** provenance kutusu
  (`ibosoftais:AirspaceDataProvenance`) bulunmalı; yoksa birleştirici durur.
- `name`/`localType` yalnız ASCII (Türkçe harf şemaya aykırı), ≤ 60 karakter.
- AIRAC değişince her kutudaki `ibosoftais:dataEffectivity` güncellenir
  (bugünkü değer: 06 AUG 2026 (AIRAC 2608)).
- Düzenlemeden sonra doğrulayın:

```bash
py ../../../common/data_build_common/validate_aixm.py trnc-airspace-aixm.xml
```
