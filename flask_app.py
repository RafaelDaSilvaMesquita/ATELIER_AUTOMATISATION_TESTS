from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COUNTRIES_CACHE_FILE = os.path.join(BASE_DIR, "qos", "countries_cache.json")
QOS_HISTORY_FILE = os.path.join(BASE_DIR, "qos", "history.json")


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _compute_metrics(history):
    if not history:
        return {
            "total_runs": 0,
            "last_run_at": None,
            "global_success_rate": None,
            "avg_latency_ms": None,
            "runs": [],
        }

    all_checks = [check for run in history for check in run["checks"]]
    passed_checks = [c for c in all_checks if c.get("passed")]
    latencies = [c["duration_ms"] for c in all_checks if "duration_ms" in c]

    runs_summary = []
    for run in history:
        checks = run["checks"]
        run_latencies = [c["duration_ms"] for c in checks if "duration_ms" in c]
        runs_summary.append({
            "timestamp": run["timestamp"],
            "success_rate": round(100 * len([c for c in checks if c.get("passed")]) / len(checks), 1)
            if checks else None,
            "avg_latency_ms": round(sum(run_latencies) / len(run_latencies), 1)
            if run_latencies else None,
        })

    return {
        "total_runs": len(history),
        "last_run_at": history[-1]["timestamp"],
        "global_success_rate": round(100 * len(passed_checks) / len(all_checks), 1)
        if all_checks else None,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "runs": runs_summary,
    }


@app.get("/")
def consignes():
    return render_template("consignes.html")


@app.get("/countries")
def countries():
    cache = _load_json(COUNTRIES_CACHE_FILE, {"fetched_at": None, "count": 0, "countries": []})
    return render_template(
        "countries.html",
        countries=cache.get("countries", []),
        fetched_at=cache.get("fetched_at"),
        count=cache.get("count", 0),
    )


@app.get("/dashboard")
def dashboard():
    history = _load_json(QOS_HISTORY_FILE, [])
    metrics = _compute_metrics(history)
    return render_template("dashboard.html", metrics=metrics, history=history)


@app.get("/api/qos")
def api_qos():
    """Endpoint JSON brut : pratique pour un monitoring externe."""
    history = _load_json(QOS_HISTORY_FILE, [])
    return jsonify(_compute_metrics(history))


if __name__ == "__main__":
    # utile en local uniquement
    app.run(host="0.0.0.0", port=5000, debug=True)
