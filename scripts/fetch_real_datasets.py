"""Download Real-World Production and Attack API/HTTP Datasets.

Fetches authentic real-world HTTP/API traffic logs from verified research
and industry repositories for model training and real-time inference.
"""

from pathlib import Path
import sys
import httpx

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "real_datasets"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = {
    "real_production_access.log": "https://raw.githubusercontent.com/linuxacademy/content-elastic-log-samples/master/access.log",
    "real_web_attacks_netsparker.log": "https://raw.githubusercontent.com/ocatak/apache-http-logs/master/netsparker.txt",
    "real_web_attacks_acunetix.log": "https://raw.githubusercontent.com/ocatak/apache-http-logs/master/acunetix.txt",
    "real_web_attacks_w3af.log": "https://raw.githubusercontent.com/ocatak/apache-http-logs/master/w3af.txt",
}


def download_datasets():
    print("=" * 70)
    print(" SentinelAPI Real-World Dataset Fetcher")
    print("=" * 70)

    for filename, url in DATASETS.items():
        out_file = DATA_DIR / filename
        if out_file.exists() and out_file.stat().st_size > 1000:
            print(f"[+] {filename} already exists ({out_file.stat().st_size / 1024:.1f} KB). Skipping.")
            continue

        print(f"[*] Downloading {filename} from {url}...")
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                res = client.get(url)
                if res.status_code == 200 and len(res.text) > 100:
                    out_file.write_text(res.text, encoding="utf-8")
                    lines = [l for l in res.text.splitlines() if l.strip()]
                    print(f"    [OK] Saved {len(lines)} records ({len(res.content) / 1024:.1f} KB)")
                else:
                    print(f"    [FAIL] HTTP {res.status_code}")
        except Exception as e:
            print(f"    [ERROR] {e}")

    print("\n[+] Real datasets ready in data/real_datasets/.")


if __name__ == "__main__":
    download_datasets()
