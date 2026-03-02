import os
import re

# 🔥 Script'in bulunduğu klasör
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔥 Bir üst dizine çık ve SVG klasörüne gir
SOURCE_FOLDER = os.path.join(CURRENT_DIR, "..", "ICAO Annex 4 SVG Symbols")
SOURCE_FOLDER = os.path.abspath(SOURCE_FOLDER)


def normalize_hex(hex_code):
    hex_code = hex_code.upper()
    if not hex_code.startswith("#"):
        hex_code = "#" + hex_code
    return hex_code


def recolor_all_colors(content, new_hex):
    content = re.sub(r'#([0-9a-fA-F]{3,6})', new_hex, content)
    content = re.sub(r'rgb\s*\([^)]+\)', new_hex, content)
    content = re.sub(r'fill="[^"]+"', f'fill="{new_hex}"', content)
    content = re.sub(r'stroke="[^"]+"', f'stroke="{new_hex}"', content)
    return content


def process_svgs(color_list):

    if not os.path.exists(SOURCE_FOLDER):
        print(f"Klasör bulunamadı: {SOURCE_FOLDER}")
        return

    svg_files = [
        f for f in os.listdir(SOURCE_FOLDER)
        if f.lower().endswith(".svg")
    ]

    print(f"{len(svg_files)} adet SVG bulundu.")

    for color in color_list:

        new_hex = normalize_hex(color)
        hex_clean = new_hex.replace("#", "")

        # 🔥 Script klasöründe çıktı klasörü oluştur
        output_folder = os.path.join(CURRENT_DIR, hex_clean)
        os.makedirs(output_folder, exist_ok=True)

        for filename in svg_files:

            source_path = os.path.join(SOURCE_FOLDER, filename)

            with open(source_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            new_content = recolor_all_colors(original_content, new_hex)

            # 🔥 Dosya adını ayır
            name, ext = os.path.splitext(filename)

            # 🔥 Sonuna -HEXCODE ekle
            new_filename = f"{name}-{hex_clean}{ext}"

            output_path = os.path.join(output_folder, new_filename)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(new_content)

        print(f"{hex_clean} klasörü oluşturuldu ve dosyalar işlendi.")


if __name__ == "__main__":

    # 🔥 BURAYA İSTEDİĞİN KADAR RENK EKLE
    colors = [
        "#000000",
        "#5e5e5e",
        "#41ddf0",
    ]

    process_svgs(colors)