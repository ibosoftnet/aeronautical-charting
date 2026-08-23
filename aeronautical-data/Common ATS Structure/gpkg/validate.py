"""AŞAMA 2B — satır doğrulama ve severity politikası.

Politika (plan kararı):
  * Enum ihlali / tip uyumsuzluğu → `error`, alan **null'lanır**, kayıt yine yazılır
  * Serbest metin `max_length` aşımı → `warning`, değer kırpılır, tam değer logda
  * Kaynağın hiç sağlamadığı alanlar → hiç loglanmaz (boş değer ihlal değildir)

Böylece görünür boşluk bırakılır, sessizce bozuk veri yazılmaz.
"""

from .validation_rules import OTHER_RE, RULES


def _check_enum(value, rule):
    if value in rule.enum:
        return True
    return bool(rule.allow_other and OTHER_RE.match(value))


def validate_row(layer: str, row: dict, log, identifier: str) -> dict:
    """Satırı yerinde düzeltir; ihlalleri loglar ve düzeltilmiş satırı döner."""
    rules = RULES.get(layer)
    if not rules:
        return row

    for column, rule in rules.items():
        value = row.get(column)
        if value is None or value == "":
            continue                              # kaynakta yok — ihlal değil

        if rule.kind == "enum":
            if not _check_enum(str(value), rule):
                log.error("2B", layer, identifier, column, value,
                          "enum_disi_deger")
                row[column] = None

        elif rule.kind == "number":
            try:
                number = float(value)
            except (TypeError, ValueError):
                log.error("2B", layer, identifier, column, value,
                          "sayisal_olmayan_deger")
                row[column] = None
                continue
            if ((rule.minimum is not None and number < rule.minimum)
                    or (rule.maximum is not None and number > rule.maximum)):
                log.error("2B", layer, identifier, column, value,
                          "aralik_disi_deger")
                row[column] = None

        elif rule.max_length and len(str(value)) > rule.max_length:
            log.warning("2B", layer, identifier, column, value,
                        "uzunluk_asildi_kirpildi")
            row[column] = str(value)[:rule.max_length]

    # NOT: `type`/`class` icin eskiden burada calisma-zamani dallanmasi vardi
    # (`equipmentType`'a bakip dogru enum'u secmek icin). Artik gerekmiyor:
    # bu alanlar `navaidComponents_<AltTur>_<alan>` seklinde AYRI SUTUNLARDA
    # duruyor ve her sutun kendi enum kuralini `RULES` icinden aliyor.
    return row
