import csv
import random
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/eshza/medicalTranscriptsKaggle/master/mtsamples.csv"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "mtsamples"
KEEP_SPECIALTIES = {"Radiology", "Discharge Summary"}
SAMPLE_SIZE = 80
RANDOM_SEED = 42


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    full_csv_path = RAW_DIR / "mtsamples_full.csv"

    print(f"Downloading {SOURCE_URL} -> {full_csv_path}")
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request) as response, full_csv_path.open("wb") as f:
        f.write(response.read())

    with full_csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = [row for row in reader if row["medical_specialty"].strip() in KEEP_SPECIALTIES]

    random.seed(RANDOM_SEED)
    sampled = random.sample(rows, min(SAMPLE_SIZE, len(rows)))

    filtered_path = RAW_DIR / "mtsamples_filtered.csv"
    with filtered_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sampled)

    full_csv_path.unlink()
    print(f"Wrote {len(sampled)} filtered reports to {filtered_path}")


if __name__ == "__main__":
    main()