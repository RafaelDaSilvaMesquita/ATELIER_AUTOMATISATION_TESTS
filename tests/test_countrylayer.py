"""
Tests automatises de qualite de service (QoS) pour l'API CountryLayer.

Chaque test :
  - appelle l'API CountryLayer,
  - verifie la disponibilite (code HTTP), le temps de reponse et la
    structure/qualite des donnees renvoyees,
  - enregistre sa mesure via la fixture qos_record (voir conftest.py) afin
    d'alimenter le tableau de bord QoS (/dashboard).

Variable d'environnement requise : COUNTRYLAYER_API_KEY
(definie en secret GitHub Actions, ou en local via un fichier .env / export)
"""
import os

import pytest
import requests

BASE_URL = "https://api.countrylayer.com/v2"
API_KEY = os.environ.get("COUNTRYLAYER_API_KEY")
TIMEOUT_SECONDS = 10
MAX_ACCEPTABLE_LATENCY_MS = 3000

pytestmark = pytest.mark.skipif(
    not API_KEY, reason="COUNTRYLAYER_API_KEY non defini dans l'environnement"
)


def _call_all_countries():
    return requests.get(
        f"{BASE_URL}/all", params={"access_key": API_KEY}, timeout=TIMEOUT_SECONDS
    )


def test_all_countries_endpoint_is_available(qos_record):
    """Verifie que l'endpoint /v2/all repond avec un statut HTTP 200."""
    with qos_record("GET /v2/all - disponibilite") as ctx:
        response = _call_all_countries()
        ctx["status_code"] = response.status_code
        assert response.status_code == 200


def test_all_countries_response_time(qos_record):
    """Verifie que le temps de reponse reste sous un seuil acceptable."""
    with qos_record("GET /v2/all - temps de reponse") as ctx:
        response = _call_all_countries()
        latency_ms = response.elapsed.total_seconds() * 1000
        ctx["latency_ms"] = round(latency_ms, 1)
        assert latency_ms < MAX_ACCEPTABLE_LATENCY_MS

def test_all_countries_payload_structure(qos_record):
    """Verifie que la reponse est une liste de pays avec les champs attendus."""
    with qos_record("GET /v2/all - structure des donnees") as ctx:
        response = _call_all_countries()
        data = response.json()
        ctx["country_count"] = len(data) if isinstance(data, list) else 0

        assert isinstance(data, list)
        assert len(data) > 190  # ~250 pays/territoires references par l'API

        sample = data[0]
        for field in ("name", "capital", "region", "population", "flag"):
            assert field in sample


def test_all_countries_minimum_data_quality(qos_record):
    """Verifie qu'une grande majorite des pays ont une population renseignee."""
    with qos_record("GET /v2/all - qualite des donnees") as ctx:
        response = _call_all_countries()
        data = response.json()

        missing_population = [c.get("name") for c in data if not c.get("population")]
        ctx["countries_missing_population"] = len(missing_population)

        assert len(missing_population) < len(data) * 0.1
