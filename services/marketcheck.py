import os
import requests


def money_to_number(value):
    try:
        return int(float(str(value).replace('$', '').replace(',', '').strip()))
    except Exception:
        return 0


def buscar_marketcheck(vin):
    key = os.getenv("MARKETCHECK_API_KEY", "")

    # Fallback base. La app no se rompe si no hay API key o si MarketCheck falla.
    fallback = {
        "market_value": 0,
        "colorado_average": 0,
        "transmission": "No encontrado",
        "drivetrain": "No encontrado",
        "engine": "No encontrado",
        "miles": "No encontrado",
        "accidents": "No encontrado",
    }

    if not key:
        return fallback

    try:
        url = f"https://api.marketcheck.com/v2/decode/car/{vin}/specs"
        r = requests.get(url, params={"api_key": key}, timeout=20)
        if r.status_code != 200:
            return fallback
        data = r.json()
        build = data.get("build", {}) or data.get("specs", {}) or data
        return {
            "market_value": money_to_number(data.get("price") or data.get("market_value") or 0),
            "colorado_average": money_to_number(data.get("price") or data.get("market_value") or 0),
            "transmission": build.get("transmission") or build.get("transmission_name") or "Automatic",
            "drivetrain": build.get("drivetrain") or build.get("drive_type") or "No encontrado",
            "engine": build.get("engine") or build.get("engine_description") or "No encontrado",
            "miles": data.get("miles") or "No encontrado",
            "accidents": data.get("accidents") or "No encontrado",
        }
    except Exception:
        return fallback
