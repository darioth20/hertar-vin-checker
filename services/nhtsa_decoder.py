import requests


def decode_vin(vin):
    try:
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
        r = requests.get(url, timeout=12)
        data = r.json().get("Results", [])
        out = {}
        for item in data:
            key = item.get("Variable")
            val = item.get("Value")
            if val:
                out[key] = val
        return {
            "year": out.get("Model Year", "No encontrado"),
            "make": out.get("Make", "No encontrado"),
            "model": out.get("Model", "No encontrado"),
            "trim": out.get("Trim", "No encontrado"),
            "engine": out.get("Engine Model", out.get("Displacement (L)", "No encontrado")),
            "body": out.get("Body Class", "No encontrado"),
            "drive_type": out.get("Drive Type", "No encontrado"),
            "transmission": out.get("Transmission Style", "No encontrado"),
        }
    except Exception as e:
        return {"error": str(e)}
