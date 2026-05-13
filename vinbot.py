import requests
import urllib.request

API_KEY = "2TCIi74NzmAfNDwdccW9Hy2ihmgFxooa"

VIN = input("ESCRIBE VIN: ").strip().upper()

def pedir(url):
    r = requests.get(url)
    print("STATUS:", r.status_code)
    try:
        return r.json()
    except:
        return {"error": r.text}

decode_url = f"https://api.marketcheck.com/v2/decode/car/{VIN}/specs?api_key={API_KEY}"
history_url = f"https://api.marketcheck.com/v2/history/car/{VIN}?api_key={API_KEY}"
auction_url = f"https://api.marketcheck.com/v2/search/car/auction/active?api_key={API_KEY}&vin={VIN}"
market_url = f"https://api.marketcheck.com/v2/search/car/active?api_key={API_KEY}&vin={VIN}"

decode = pedir(decode_url)
history = pedir(history_url)
auction = pedir(auction_url)
market = pedir(market_url)

print("\n========== REPORTE DEL VEHÍCULO ==========\n")

print("VIN:", VIN)
print("AÑO:", decode.get("year", "N/A"))
print("MARCA:", decode.get("make", "N/A"))
print("MODELO:", decode.get("model", "N/A"))
print("TRIM:", decode.get("trim", "N/A"))
print("MOTOR:", decode.get("engine", "N/A"))
print("TRANSMISIÓN:", decode.get("transmission", "N/A"))
print("DRIVETRAIN:", decode.get("drivetrain", "N/A"))

print("\n========== HISTORIAL ==========\n")

print("Registros encontrados:", len(history) if isinstance(history, list) else 0)

if isinstance(history, list) and len(history) > 0:
    ultimo = history[0]
    print("Últimas millas:", ultimo.get("miles", "N/A"))
    print("Última fuente:", ultimo.get("source", "N/A"))
    print("Última fecha:", ultimo.get("last_seen_at_date", "N/A"))
    print("Link historial:", ultimo.get("vdp_url", "N/A"))

print("\n========== SUBASTA ACTIVA ==========\n")

fotos = []

if auction.get("num_found", 0) > 0:
    carro = auction["listings"][0]

    print("Título:", carro.get("heading", "N/A"))
    print("Millas:", carro.get("miles", "N/A"))
    print("Subasta:", carro.get("source", "N/A"))
    print("Vendedor:", carro.get("dealer", {}).get("name", "N/A"))
    print("Ciudad:", carro.get("dealer", {}).get("city", "N/A"))
    print("Estado:", carro.get("dealer", {}).get("state", "N/A"))
    print("Teléfono:", carro.get("dealer", {}).get("phone", "N/A"))
    print("Link:", carro.get("vdp_url", "N/A"))

    fotos = carro.get("media", {}).get("photo_links", [])

    print("\n========== FOTOS COPART ==========\n")

    if fotos:
        for i, foto in enumerate(fotos, start=1):
            print(foto)

            try:
                nombre = f"foto_{VIN}_{i}.jpg"
                urllib.request.urlretrieve(foto, nombre)
                print("Foto descargada:", nombre)
            except Exception as e:
                print("No se pudo descargar foto:", e)
    else:
        print("No hay fotos disponibles")

else:
    print("No hay subasta activa encontrada")

print("\n========== VALOR MERCADO ==========\n")

precios = []

if market.get("num_found", 0) > 0:
    for item in market.get("listings", []):
        precio = item.get("price")
        if precio:
            precios.append(precio)

if precios:
    promedio = sum(precios) / len(precios)
    print("Precios encontrados:", precios)
    print("Valor mercado promedio: $", round(promedio, 2))
else:
    promedio = 0
    print("No se encontró valor de mercado activo")

print("\n========== SALVAGE CHECK ==========\n")

salvage_detectado = False

if isinstance(history, list):
    for item in history:
        texto = str(item).lower()
        if "salvage" in texto or "auction" in texto or "copart" in texto:
            salvage_detectado = True

if salvage_detectado:
    print("⚠️ Posible SALVAGE / SUBASTA detectado")
else:
    print("✅ No se detectó salvage en los datos disponibles")

print("\n========== CALCULADORA DE GANANCIA ==========\n")

try:
    reparacion = float(input("REPARACIÓN ESTIMADA: $"))
    fees = float(input("FEES SUBASTA: $"))
    transporte = float(input("TRANSPORTE: $"))
    oferta = float(input("TU OFERTA / COMPRA: $"))

    ganancia = promedio - reparacion - fees - transporte - oferta

    print("\nGANANCIA ESTIMADA: $", round(ganancia, 2))

    if ganancia > 2000:
        print("🔥 Buen negocio")
    elif ganancia > 0:
        print("⚠️ Ganancia baja")
    else:
        print("❌ No conviene")

except:
    print("Calculadora omitida")

print("\n========== FIN DEL REPORTE ==========")