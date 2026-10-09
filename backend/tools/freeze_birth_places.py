"""Build the attributed, frozen mainland-China gazetteer (never used at runtime)."""
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile


def main():
    url = "https://download.geonames.org/export/dump/CN.zip"
    archive = urlopen(url, timeout=120).read()
    rows = []
    with ZipFile(io.BytesIO(archive)) as source:
        for line in source.read("CN.txt").decode("utf-8").splitlines():
            fields = line.split("\t")
            if fields[6] not in {"A", "P"} or fields[7] not in {"ADM1", "ADM2", "ADM3", "PPLA", "PPLA2", "PPLA3", "PPLC"}:
                continue
            # CN includes SAR entries; automatic support is mainland only.
            if fields[10] in {"HK", "MO", "TW"} or fields[17] not in {"Asia/Shanghai", "Asia/Urumqi"}:
                continue
            names = sorted(set([fields[1], fields[2], *fields[3].split(",")]) - {""})
            rows.append({"id": int(fields[0]), "name": fields[1], "aliases": names,
                         "latitude": float(fields[4]), "longitude": float(fields[5]),
                         "feature": fields[7], "admin1": fields[10], "admin2": fields[11],
                         "modified": fields[18]})
    destination = Path(__file__).resolve().parents[1] / "app/domains/reports/generation/data"
    destination.mkdir(parents=True, exist_ok=True)
    payload = {"version": "geonames-cn-2026-10-07", "source": url,
               "archive_sha256": hashlib.sha256(archive).hexdigest(),
               "license": "CC BY 4.0", "attribution": "GeoNames (https://www.geonames.org), CC BY 4.0",
               "precision": "行政区或城市代表点，不代表具体出生医院", "places": rows}
    (destination / "birth_places_cn.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Frozen {len(rows)} places")


if __name__ == "__main__":
    main()
