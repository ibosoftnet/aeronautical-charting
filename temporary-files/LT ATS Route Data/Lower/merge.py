import os
import json
from collections import defaultdict

def merge_json_files(directory):
    merged_features = []

    for file in os.listdir(directory):
        if file.endswith(".json"):
            with open(os.path.join(directory, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                if "features" in data:
                    merged_features.extend(data["features"])

    return merged_features


def deduplicate_points(features):
    """
    Aynı isim (hi) ve aynı koordinata sahip pointleri teke indirir.
    """
    unique_points = {}
    new_features = []

    for feature in features:
        geom = feature.get("geometry", {})
        props = feature.get("properties", {})

        if geom.get("type") != "Point":
            new_features.append(feature)
            continue

        name = props.get("hi")
        coords = tuple(geom.get("coordinates", []))

        key = (name, coords)

        if key not in unique_points:
            unique_points[key] = feature
            new_features.append(feature)
        else:
            # duplicate point → ignore
            continue

    return new_features


def enrich_points_from_lines(features):

    point_updates = defaultdict(lambda: {
        "ais_REPORTING_ATC": set(),
        "ais_NAVIGATION_TYPE": set()
    })

    # 1️⃣ LineString'lerden veriyi topla
    for feature in features:
        if feature.get("geometry", {}).get("type") != "LineString":
            continue

        props = feature.get("properties", {})

        start_name = props.get("ais_START_POINT_NAME")
        end_name = props.get("ais_END_POINT_NAME")

        start_reporting = props.get("ais_START_POINT_REPORTING_ATC")
        end_reporting = props.get("ais_END_POINT_REPORTING_ATC")
        nav_type = props.get("ais_NAVIGATION_TYPE")

        if start_name:
            if start_reporting:
                point_updates[start_name]["ais_REPORTING_ATC"].add(start_reporting)
            if nav_type:
                point_updates[start_name]["ais_NAVIGATION_TYPE"].add(nav_type)

        if end_name:
            if end_reporting:
                point_updates[end_name]["ais_REPORTING_ATC"].add(end_reporting)
            if nav_type:
                point_updates[end_name]["ais_NAVIGATION_TYPE"].add(nav_type)

    # 2️⃣ Mevcut noktaları güncelle
    for feature in features:
        if feature.get("geometry", {}).get("type") != "Point":
            continue

        props = feature.get("properties", {})
        name = props.get("hi")

        if name in point_updates:

            reporting_values = sorted(point_updates[name]["ais_REPORTING_ATC"])
            nav_values = sorted(point_updates[name]["ais_NAVIGATION_TYPE"])

            if reporting_values:
                props["ais_REPORTING_ATC"] = "/".join(reporting_values)

            if nav_values:
                props["ais_NAVIGATION_TYPE"] = "/".join(nav_values)

    return features


def main():
    directory = "."

    merged = merge_json_files(directory)

    deduplicated = deduplicate_points(merged)

    enriched = enrich_points_from_lines(deduplicated)

    output = {
        "type": "FeatureCollection",
        "features": enriched
    }

    with open("merged.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)

    print("✔ merged.json oluşturuldu")
    print("✔ Aynı isim + koordinatlı noktalar tekilleştirildi")
    print("✔ LineString bilgileri mevcut noktalara işlendi")


if __name__ == "__main__":
    main()