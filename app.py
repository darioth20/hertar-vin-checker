import os
from flask import Flask, render_template, jsonify, request, redirect, url_for
from dotenv import load_dotenv

from services.carfax_vercel import extraer_carfax_vercel
from services.marketcheck import buscar_marketcheck
from services.finance import build_financial

load_dotenv()

app = Flask(__name__)


def safe_report(vin):
    carfax = extraer_carfax_vercel(vin)
    market = buscar_marketcheck(vin, carfax)
    financial = build_financial(vin, carfax, market)
    return {
        "vin": vin,
        "carfax": carfax,
        "marketcheck": market,
        "financial": financial,
        "debug": {
            "market_error": market.get("error", ""),
            "carfax_error": carfax.get("error", ""),
        },
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    vin = request.form.get("vin", "").upper().strip()
    if not vin:
        return redirect(url_for("home"))
    return redirect(url_for("lot", vin=vin))


@app.route("/lot/<vin>")
def lot(vin):
    # carga rápida: NO ejecuta CARFAX aquí
    return render_template("lot.html", vin=vin.upper().strip())


@app.route("/api/full-report/<vin>")
def api_full_report(vin):
    try:
        return jsonify(safe_report(vin.upper().strip()))
    except Exception as e:
        vin = vin.upper().strip()
        return jsonify({
            "vin": vin,
            "carfax": {
                "miles": "No encontrado", "carfax_value": 0, "retail_value": 0, "wholesale_value": 0,
                "title": "No encontrado", "branded_title": "No encontrado", "owners": "No encontrado",
                "accidents": "No encontrado", "service_records": "No encontrado", "engine": "No encontrado",
                "drive_type": "No encontrado", "body": "No encontrado", "pdf_url": "No encontrado",
                "error": str(e)
            },
            "marketcheck": {
                "market_value": 0, "colorado_average": 0, "transmission": "No encontrado",
                "drivetrain": "No encontrado", "engine": "No encontrado", "miles": "No encontrado",
                "accidents": "No encontrado"
            },
            "financial": {
                "title_value": 0, "max_bid": 0, "estimated_repair": 2500, "risk": "Alto",
                "ai_decision": "DO NOT BUY", "ai_reason": f"Error generando reporte: {e}"
            },
            "debug": {"error": str(e)}
        }), 500


@app.route("/debug-carfax/<vin>")
def debug_carfax(vin):
    return jsonify(extraer_carfax_vercel(vin.upper().strip()))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
