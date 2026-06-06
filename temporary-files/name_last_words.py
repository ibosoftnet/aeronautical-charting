import sqlite3
from collections import Counter

db = r"d:/ibosoft/aeronautical-charting/aeronautical-data/Jeppesen Data/jeppesen.sqlite"
c = sqlite3.connect(db)
names = [r[0] for r in c.execute(
    "SELECT DISTINCT name FROM boundary WHERE name IS NOT NULL AND type NOT IN ('P','R','DA','W','TR') AND name NOT LIKE '%FREE%'"
)]
c.close()

last_words = Counter()
for name in names:
    parts = name.strip().split()
    if len(parts) > 1:
        last_words[parts[-1]] += 1

out = ["# Boundary Name — Son Kelimeler (P, R, DA, W, TR hariç)\n"]
out.append(f"Toplam distinct çok-kelimeli isim: **{sum(last_words.values())}**  ")
out.append(f"Distinct son kelime sayısı: **{len(last_words)}**\n")
out.append("| Son kelime | Adet |")
out.append("|---|---|")
for word, cnt in last_words.most_common():
    out.append(f"| `{word}` | {cnt} |")

dst = r"d:/ibosoft/aeronautical-charting/temporary-files/name_last_words.md"
with open(dst, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"Yazıldı: {dst}  ({len(last_words)} satır)")
