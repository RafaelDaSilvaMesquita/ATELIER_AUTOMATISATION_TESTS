"""
Recupere la liste complete des pays via l'API CountryLayer et la sauvegarde
localement (qos/countries_cache.json) afin que l'application Flask puisse
l'afficher SANS dependre d'un appel reseau sortant en direct depuis
PythonAnywhere (les comptes gratuits limitent les appels sortants a une
liste blanche de domaines qui n'inclut pas api.countrylayer.com).

Ce script est execute par la CI (GitHub Actions), jamais par le serveur
Flask lui-meme.
"""
import json
import os
import sys
from datetime import datetime, timezone

import requests

BASE_URL = "https://api.countrylayer.com/v2"
API_KEY = os.environ.get("COUNTRYLAYER_API_KEY")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "qos", "countries_cache.json")


def main():
    if not API_KEY:
        print("COUNTRYLAYER_API_KEY manquant : cache non mis a jour.", file=sys.stderr)
        sys.exit(1)

    response = requests.get(f"{BASE_URL}/all", params={"access_key": API_KEY}, timeout=15)
    response.raise_for_status()
    countries = response.json()

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(countries),
        "countries": countries,
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Cache mis a jour : {len(countries)} pays enregistres.")


if __name__ == "__main__":
    main()

