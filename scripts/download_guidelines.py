import urllib.request
from pathlib import Path

GUIDELINES = {
    "nice_ng122_lung_cancer.pdf": "https://www.nice.org.uk/guidance/ng122/resources/lung-cancer-diagnosis-and-management-pdf-66141655525573",
    "nice_ng136_hypertension.pdf": "https://www.nice.org.uk/guidance/ng136/resources/hypertension-in-adults-diagnosis-and-management-pdf-66141722710213",
}

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "guidelines"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in GUIDELINES.items():
        dest = RAW_DIR / filename
        print(f"Downloading {url} -> {dest}")
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request) as response, dest.open("wb") as f:
            f.write(response.read())


if __name__ == "__main__":
    main()