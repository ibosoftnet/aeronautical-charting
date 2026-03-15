# IBOSOFT

import xml.etree.ElementTree as ET

vrt_path = 'srtm-1arcsec-metre-merged.vrt'
output_path = 'srtm-1arcsec-foot-merged.vrt'

# VRT dosyasını yükle
tree = ET.parse(vrt_path)
root = tree.getroot()

# ICAO Annex 5 e göre dönüşüm (1/0.3048)
feet_scale = str(1 / 0.3048)

# Her bir band (VRTRasterBand) için Scale değerini ayarla
for band in root.findall('VRTRasterBand'):
    # Eğer halihazırda bir Scale etiketi varsa güncelle, yoksa yeni oluştur
    scale_elem = band.find('Scale')
    if scale_elem is None:
        scale_elem = ET.SubElement(band, 'Scale')
    
    scale_elem.text = feet_scale
    
    # Veri tipini de ondalıklı (Float32) yap
    band.set('dataType', 'Float32')

# Yeni dosyayı kaydet
tree.write(output_path, encoding='UTF-8', xml_declaration=True)

print(f"İşlem tamam! Yeni dosya: {output_path}")