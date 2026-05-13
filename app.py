# app.py


from flask import Flask, request
from flask import send_file
from reportlab.pdfgen import canvas
import requests

app = Flask(__name__)

API_KEY = "2TCIi74NzmAfNDwdccW9Hy2ihmgFxooa"


def pedir(url):
    r = requests.get(url)

    try:
        return r.json()
    except:
        return {}

def crear_pdf(reporte):

    nombre = f"{reporte['vin']}.pdf"

    c = canvas.Canvas(nombre)

    y = 800

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "HERTAR AUTOMOTIVE REPORT")

    y -= 50

    c.setFont("Helvetica", 12)

    for clave, valor in reporte.items():

        if clave != "fotos":

            c.drawString(50, y, f"{clave}: {valor}")

            y -= 25

    c.save()

    return nombre

@app.route("/", methods=["GET", "POST"])
def home():

    reporte = None

    if request.method == "POST":

        vin = request.form.get("vin", "").strip().upper()

        decode_url = f"https://api.marketcheck.com/v2/decode/car/{vin}/specs?api_key={API_KEY}"

        history_url = f"https://api.marketcheck.com/v2/history/car/{vin}?api_key={API_KEY}"

        auction_url = f"https://api.marketcheck.com/v2/search/car/auction/active?api_key={API_KEY}&vin={vin}"

        
        decode = pedir(decode_url)
        history = pedir(history_url)
        auction = pedir(auction_url)

        year = decode.get("year", "")
        make = decode.get("make", "")
        model = decode.get("model", "")

        market_url = f"https://api.marketcheck.com/v2/search/car/active?api_key={API_KEY}&year={year}&make={make}&model={model}&rows=20"
        market = pedir(market_url)

        fotos = []
        auction_link = "No encontrada"
        millas = "N/A"
        source = "N/A"

        if auction.get("num_found", 0) > 0:

            carro = auction["listings"][0]

            millas = carro.get("miles", "N/A")
            source = carro.get("source", "N/A")
            auction_link = carro.get("vdp_url", "No encontrada")
            fotos = carro.get("media", {}).get("photo_links", [])

        salvage = "NO DETECTADO"

        if isinstance(history, list):

            for item in history:

                texto = str(item).lower()

                if "salvage" in texto or "auction" in texto or "copart" in texto:
                    salvage = "POSIBLE SALVAGE / SUBASTA"
                    break

        valor_mercado = 0
        oferta_maxima = 0

        precios = []

        if market.get("num_found", 0) > 0:

            for item in market.get("listings", []):

                precio = item.get("price")

                if precio:
                    precios.append(precio)

        if precios:

            valor_mercado = round(sum(precios) / len(precios), 2)

            reparacion = 3000
            fees = 1200
            transporte = 600
            ganancia_deseada = 3000

            oferta_maxima = (
                valor_mercado
                - reparacion
                - fees
                - transporte
                - ganancia_deseada
            )

        reporte = {
            "vin": vin,
            "year": decode.get("year", "N/A"),
            "make": decode.get("make", "N/A"),
            "model": decode.get("model", "N/A"),
            "trim": decode.get("trim", "N/A"),
            "engine": decode.get("engine", "N/A"),
            "transmission": decode.get("transmission", "N/A"),
            "drivetrain": decode.get("drivetrain", "N/A"),
            "millas": millas,
            "source": source,
            "auction_link": auction_link,
            "fotos": fotos,
            "historial": len(history) if isinstance(history, list) else 0,
            "salvage": salvage,
            "valor_mercado": valor_mercado,
            "oferta_maxima": round(oferta_maxima, 2)
        }

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>HERTAR VIN CHECKER</title>

    <style>

        body {{
            font-family: Arial;
            background: #111827;
            color: white;
            padding: 30px;
        }}

        .box {{
            background: #1f2937;
            padding: 25px;
            border-radius: 15px;
            max-width: 900px;
            margin: auto;
        }}

        input {{
            width: 70%;
            padding: 15px;
            border-radius: 10px;
            border: none;
            font-size: 18px;
        }}

        button {{
            padding: 15px 25px;
            border: none;
            border-radius: 10px;
            background: #22c55e;
            color: white;
            font-size: 18px;
            cursor: pointer;
        }}

        .card {{
            background: #374151;
            margin-top: 20px;
            padding: 20px;
            border-radius: 15px;
        }}

        img {{
            max-width: 300px;
            border-radius: 12px;
            margin: 10px;
        }}

        a {{
            color: #38bdf8;
        }}

        .alert {{
            color: #facc15;
            font-weight: bold;
        }}

    </style>

</head>

<body>

    <div class="box">

        <h1>🔥 HERTAR VIN CHECKER</h1>

        <form method="POST">
            <input name="vin" placeholder="Escribe VIN" required>
            <button type="submit">Consultar</button>
        </form>

        {mostrar_reporte(reporte)}

    </div>

</body>
</html>
"""


def mostrar_reporte(r):

    if not r:
        return ""

    fotos_html = ""

    for foto in r["fotos"]:
        fotos_html += f'<img src="{foto}">'

    return f"""

    <div class="card">

        <h2>Reporte del Vehículo</h2>

        <p><b>VIN:</b> {r["vin"]}</p>
        <p><b>Año:</b> {r["year"]}</p>
        <p><b>Marca:</b> {r["make"]}</p>
        <p><b>Modelo:</b> {r["model"]}</p>
        <p><b>Trim:</b> {r["trim"]}</p>
        <p><b>Motor:</b> {r["engine"]}</p>
        <p><b>Transmisión:</b> {r["transmission"]}</p>
        <p><b>Drivetrain:</b> {r["drivetrain"]}</p>
        <p><b>Millas:</b> {r["millas"]}</p>
        <p><b>Historial:</b> {r["historial"]} registros</p>

        <p class="alert">
            <b>Salvage Check:</b> {r["salvage"]}
        </p>

        <p><b>Valor Mercado:</b> ${r["valor_mercado"]}</p>

        <p>
            <b>Oferta Máxima Recomendada:</b>
            ${r["oferta_maxima"]}
        </p>

        <p><b>Subasta:</b> {r["source"]}</p>

        <p>
            <b>Link:</b>
            <a href="{r["auction_link"]}" target="_blank">
                Abrir subasta
            </a>
        </p>
        <br><br>

<a href="/pdf/{r['vin']}" target="_blank">
    <button>Descargar PDF</button>
</a>

    </div>

    <div class="card">

        <h2>Fotos Copart / Subasta</h2>

        {fotos_html if fotos_html else "No hay fotos disponibles"}

    </div>

    """
@app.route("/pdf/<vin>")
def pdf(vin):

    reporte = {
        "vin": vin,
        "estado": "Reporte generado",
    }

    archivo = crear_pdf(reporte)

    return send_file(
        archivo,
        as_attachment=True
    )

if __name__ == "__main__":
    app.run(debug=True)

