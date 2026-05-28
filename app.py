import os
from flask import Flask, render_template, request, redirect, jsonify
from dotenv import load_dotenv

from services.carfax_vercel import extraer_carfax_vercel
from services.marketcheck import buscar_marketcheck

load_dotenv()

app = Flask(__name__)


def money_to_number(value):
    try:
        return int(float(str(value).replace('$', '').replace(',', '').strip()))
    except Exception:
        return 0


def safe_int(value, default=0):
    num = money_to_number(value)
    return num if num else default


def build_vehicle(vin):
    carfax_error = ""
    market_error = ""

    try:
        carfax = extraer_carfax_vercel(vin)
    except Exception as e:
        carfax_error = str(e)
        carfax = {
            "vin": vin,
            "miles": "No encontrado",
            "carfax_value": 0,
            "title": "No encontrado",
            "branded_title": "No encontrado",
            "owners": "No encontrado",
            "accidents": "No encontrado",
            "service_records": "No encontrado",
            "engine": "No encontrado",
            "drive_type": "No encontrado",
            "body": "No encontrado",
            "pdf_url": "No encontrado",
        }

    try:
        market = buscar_marketcheck(vin)
    except Exception as e:
        market_error = str(e)
        market = {}

    carfax_value = money_to_number(carfax.get("carfax_value"))
    retail_value = carfax_value
    wholesale_value = int(carfax_value * 0.82) if carfax_value else 0

    market_value = money_to_number(market.get("market_value")) or retail_value
    colorado_average = money_to_number(market.get("colorado_average")) or market_value

    miles_num = money_to_number(carfax.get("miles"))
    title = str(carfax.get("title", ""))
    accidents = str(carfax.get("accidents", ""))

    risk_discount = 0
    risk_notes = []

    if any(x.lower() in title.lower() for x in ["total loss", "salvage", "rebuilt", "flood"]):
        risk_discount += 3500
        risk_notes.append("Título con riesgo alto")

    if accidents not in ["0", "No encontrado", "", "None"]:
        risk_discount += 1500
        risk_notes.append("Accidentes o daños reportados")

    if miles_num > 120000:
        risk_discount += 1200
        risk_notes.append("Millas altas")

    title_value = max(market_value - risk_discount, 0)
    estimated_repair = 2500
    if "Total Loss" in title or "Salvage" in title:
        estimated_repair = 4500
    if accidents not in ["0", "No encontrado", "", "None"]:
        estimated_repair += 1000

    max_bid = max(title_value - estimated_repair - 1200 - 500, 0)

    risk = "LOW"
    if risk_discount >= 2500:
        risk = "MEDIUM"
    if risk_discount >= 5000:
        risk = "HIGH"

    ai_decision = "BUY"
    if risk == "HIGH" or max_bid <= 0:
        ai_decision = "DO NOT BUY"

    reason_parts = risk_notes or ["Sin alertas fuertes detectadas"]
    ai_reason = (
        "Análisis basado en CARFAX/Vercel, MarketCheck, millas, título, accidentes y mercado de Colorado. "
        f"Riesgos: {', '.join(reason_parts)}. "
        f"Valor ajustado por título/riesgo: ${title_value:,}. "
        f"Oferta máxima recomendada: ${max_bid:,}."
    )

    vehicle = {
        "vin": vin,
        "carfax": {
            "miles": carfax.get("miles", "No encontrado"),
            "carfax_value": carfax_value,
            "retail_value": retail_value,
            "wholesale_value": wholesale_value,
            "title": carfax.get("title", "No encontrado"),
            "branded_title": carfax.get("branded_title") or carfax.get("title", "No encontrado"),
            "owners": carfax.get("owners", "No encontrado"),
            "accidents": carfax.get("accidents", "No encontrado"),
            "service_records": carfax.get("service_records", "No encontrado"),
            "drive_type": carfax.get("drive_type", "No encontrado"),
            "body": carfax.get("body", "No encontrado"),
            "engine": carfax.get("engine", "No encontrado"),
            "pdf_url": carfax.get("pdf_url", "No encontrado"),
        },
        "marketcheck": {
            "market_value": market_value,
            "colorado_average": colorado_average,
            "transmission": market.get("transmission", "No encontrado"),
            "drivetrain": market.get("drivetrain", carfax.get("drive_type", "No encontrado")),
            "engine": market.get("engine", carfax.get("engine", "No encontrado")),
            "miles": market.get("miles", carfax.get("miles", "No encontrado")),
            "accidents": market.get("accidents", carfax.get("accidents", "No encontrado")),
        },
        "financial": {
            "title_value": title_value,
            "max_bid": max_bid,
            "estimated_repair": estimated_repair,
            "risk": risk,
            "ai_decision": ai_decision,
            "ai_reason": ai_reason,
        },
        "debug": {
            "carfax_error": carfax_error,
            "market_error": market_error,
        },
    }
    return vehicle


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    vin = request.form.get("vin", "").upper().strip()
    if not vin:
        return redirect("/")
    return redirect(f"/lot/{vin}")


@app.route("/lot/<vin>")
def lot(vin):
    vehicle = build_vehicle(vin.upper().strip())
    return render_template("lot.html", vehicle=vehicle)


@app.route("/api/lot/<vin>")
def api_lot(vin):
    return jsonify(build_vehicle(vin.upper().strip()))


@app.route("/debug-carfax/<vin>")
def debug_carfax(vin):
    return jsonify(extraer_carfax_vercel(vin.upper().strip()))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "HERTAR AUTOMOTIVE"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
