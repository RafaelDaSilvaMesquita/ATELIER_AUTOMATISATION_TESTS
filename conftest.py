"""
conftest.py

Plugin pytest qui capture les metriques de qualite de service (QoS) de
chaque test utilisant la fixture `qos_record`, et les persiste a la fin
de la session dans qos/history.json (historique glissant).

Ce fichier n'est pas un test : il fournit l'infrastructure de mesure
utilisee par tests/test_countrylayer.py.
"""
import json
import os
import time
from datetime import datetime, timezone

import pytest

QOS_DIR = os.path.join(os.path.dirname(__file__), "qos")
HISTORY_FILE = os.path.join(QOS_DIR, "history.json")
HISTORY_MAX_RUNS = 50  # nombre de campagnes de test conservees dans l'historique

_current_run_checks = []


@pytest.fixture
def qos_record():
    """
    A utiliser dans les tests pour mesurer et enregistrer un appel API.

    Usage:
        def test_x(qos_record):
            with qos_record("nom du check") as ctx:
                response = requests.get(...)
                ctx["status_code"] = response.status_code
                assert response.status_code == 200
    """

    class _Check:
        def __init__(self, name):
            self.name = name
            self.data = {"name": name}

        def __enter__(self):
            self._start = time.perf_counter()
            return self.data

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration_ms = round((time.perf_counter() - self._start) * 1000, 1)
            self.data["duration_ms"] = duration_ms
            self.data["passed"] = exc_type is None
            if exc_type is not None:
                self.data["error"] = str(exc_val)
            _current_run_checks.append(self.data)
            # On ne "mange" pas l'exception : pytest doit voir l'echec du test
            return False

    def _recorder(name):
        return _Check(name)

    return _recorder


def pytest_sessionfinish(session, exitstatus):
    """Ecrit l'historique QoS a la fin de la session de tests."""
    if not _current_run_checks:
        return  # aucun test QoS n'a tourne (ex : cle API absente -> tests skip)

    os.makedirs(QOS_DIR, exist_ok=True)

    run_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": _current_run_checks,
    }

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, OSError):
            history = []

    history.append(run_entry)
    history = history[-HISTORY_MAX_RUNS:]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
