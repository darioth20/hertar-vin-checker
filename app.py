
from flask import Flask, render_template, request
import os, re, statistics, requests
from openai import OpenAI

try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None

app = Flask(__name__)

MARKETCHECK_API_KEY = os.getenv("MARKETCHECK_API_KEY", "2TCIi74NzmAfNDwdccW9Hy2ihmgFxooa")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def api_get(url):
    try:
        r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        try:
            return r.json()
        except Exception:
            return {"error": "Respuesta no JSON", "status_code": r.status_code, "text": r.text[:1200], "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}

def first(*values, default="No encontrado"):
    for value in values:
        if value not in [None, "", [], {}, "N/A", "Unknown"]:
            return value
    return default

def num(value, default=0):
    try:
        if value in [None, "", "N/A", "Unknown", "No encontrado"]:
            return default
        return float(str(value).replace("$", "").replace(",", ""))
    except Exception:
        return default

def is_vin(text):
    return bool(re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", str(text).strip().upper()))

def extract_lot(text):
    text = str(text).strip()
    m = re.search(r"copart\.com/lot/(\d+)", text, re.I)
    if m:
        return m.group(1)
    nums = re.findall(r"\d+", text)
    return nums[0] if nums else text

def extract_vin(text):
    m = re.search(r"\b[A-HJ-NPR-Z0-9]{17}\b", str(text).upper())
    return m.group(0) if m else ""

# ========================= MARKETCHECK =========================

def consultar_marketcheck(vin):
    decode = api_get(f"https://api.marketcheck.com/v2/decode/car/{vin}/specs?api_key={MARKETCHECK_API_KEY}")
    year, make, model = decode.get("year", ""), decode.get("make", ""), decode.get("model", "")
    prices, comps, market = [], [], {}
    if year and make and model:
        market = api_get(
            "https://api.marketcheck.com/v2/search/car/active"
            f"?api_key={MARKETCHECK_API_KEY}&year={year}&make={make}&model={model}"
            "&car_type=used&state=CO&rows=50"
        )
        for item in market.get("listings", []):
            p = item.get("price")
            if p:
                try:
                    prices.append(float(p))
                    comps.append({
                        "year": item.get("year",""), "make": item.get("make",""),
                        "model": item.get("model",""), "trim": item.get("trim",""),
                        "price": item.get("price",0), "miles": item.get("miles",0),
                        "city": item.get("city",""), "state": item.get("state","")
                    })
                except Exception:
                    pass
    return {
        "year": decode.get("year", "No encontrado"),
        "make": decode.get("make", "No encontrado"),
        "model": decode.get("model", "No encontrado"),
        "trim": decode.get("trim", ""),
        "engine": decode.get("engine", "No encontrado"),
        "transmission": decode.get("transmission", "No encontrado"),
        "drive": decode.get("drivetrain", "No encontrado"),
        "body": decode.get("body_type", "No encontrado"),
        "market_value": round(statistics.median(prices), 2) if prices else 0,
        "average_market": round(statistics.mean(prices), 2) if prices else 0,
        "comparables": comps,
        "raw_decode": decode,
        "raw_market": market
    }

# ========================= AUCTION =========================

def normalizar_subasta(listing=None, raw=None):
    listing = listing or {}
    media = listing.get("media", {})
    photos = media.get("photo_links", []) if isinstance(media, dict) else []
    source = first(listing.get("source"), listing.get("auction_source"))
    run_drive = first(
        listing.get("run_and_drive"), listing.get("run_drive"), listing.get("run_condition"),
        listing.get("drive_status"), listing.get("vehicle_runs"), listing.get("starts"),
        listing.get("engine_starts"), listing.get("operational_status")
    )
    if run_drive == "No encontrado" and "copart" in str(source).lower():
        run_drive = "Run & Drive"
    return {
        "raw": raw or {},
        "vin": first(listing.get("vin"), default=""),
        "lot": first(listing.get("lot_id"), listing.get("stock_no"), listing.get("id")),
        "source": source,
        "title": first(listing.get("title_type"), listing.get("title"), listing.get("title_status")),
        "damage": first(listing.get("primary_damage"), listing.get("damage"), listing.get("condition")),
        "secondary_damage": first(listing.get("secondary_damage"), listing.get("secondary_damage_description")),
        "seller": first(listing.get("seller_name"), listing.get("seller")),
        "price": first(listing.get("price"), listing.get("current_bid"), listing.get("sale_price"), default=0),
        "miles": first(listing.get("miles"), listing.get("odometer")),
        "location": first(listing.get("city"), listing.get("location")),
        "state": first(listing.get("state")),
        "auction_link": first(listing.get("vdp_url"), listing.get("listing_url"), default="#"),
        "image": photos[0] if photos else "https://via.placeholder.com/900x600?text=Sin+foto",
        "photos": photos,
        "run_drive": run_drive,
        "airbags": first(listing.get("airbags"), listing.get("air_bags"), listing.get("airbag_status")),
        "transmission_status": first(listing.get("transmission_status"), listing.get("transmission_condition")),
    }

def consultar_subasta_por_vin(vin):
    data = api_get(f"https://api.marketcheck.com/v2/search/car/auction/active?api_key={MARKETCHECK_API_KEY}&vin={vin}&rows=10")
    listing = data.get("listings", [{}])[0] if data.get("num_found",0) > 0 and data.get("listings") else {}
    return normalizar_subasta(listing, data)

def consultar_lote_exacto_marketcheck(lot):
    lot = str(lot).strip()
    urls = [
        f"https://api.marketcheck.com/v2/search/car/auction/active?api_key={MARKETCHECK_API_KEY}&lot_id={lot}&rows=50",
        f"https://api.marketcheck.com/v2/search/car/auction/active?api_key={MARKETCHECK_API_KEY}&stock_no={lot}&rows=50",
        f"https://api.marketcheck.com/v2/search/car/auction/active?api_key={MARKETCHECK_API_KEY}&keyword={lot}&rows=50",
        f"https://api.marketcheck.com/v2/search/car/auction/active?api_key={MARKETCHECK_API_KEY}&lot={lot}&rows=50",
    ]
    last = {}
    for url in urls:
        data = api_get(url); last = data
        for listing in data.get("listings", []):
            lot_values = [str(listing.get(k,"")).strip() for k in ["lot_id", "stock_no", "id"]]
            if lot in lot_values:
                return normalizar_subasta(listing, data)
    return normalizar_subasta({}, last)

def copart_requests(lot):
    url = f"https://www.copart.com/lot/{lot}"
    try:
        r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        text = r.text
        vin = extract_vin(text)
        return {"found": bool(vin), "vin": vin, "lot": lot, "copart_url": url, "method": "requests", "status_code": r.status_code}
    except Exception as e:
        return {"found": False, "vin": "", "lot": lot, "copart_url": url, "method": "requests", "error": str(e)}

def copart_playwright(lot):
    url = f"https://www.copart.com/lot/{lot}"
    if sync_playwright is None:
        return {"found": False, "vin": "", "lot": lot, "copart_url": url, "method": "playwright", "error": "Playwright no está instalado."}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36")
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)
            text = page.inner_text("body")
            html = page.content()
            vin = extract_vin(text) or extract_vin(html)
            run_drive = "Run & Drive" if ("run and drive" in text.lower() or "run & drive" in text.lower()) else "No encontrado"
            browser.close()
            return {"found": bool(vin), "vin": vin, "lot": lot, "copart_url": url, "method": "playwright", "run_drive": run_drive}
    except Exception as e:
        return {"found": False, "vin": "", "lot": lot, "copart_url": url, "method": "playwright", "error": str(e)}

def consultar_copart_directo_por_lote(lot):
    req = copart_requests(lot)
    if req.get("vin"):
        return req
    pw = copart_playwright(lot)
    if pw.get("vin"):
        return pw
    return {"found": False, "vin": "", "lot": lot, "copart_url": f"https://www.copart.com/lot/{lot}", "requests": req, "playwright": pw, "error": "No se pudo extraer VIN desde Copart."}

# ========================= CALCULOS =========================

def calcular_fee_subasta(precio):
    precio = num(precio)
    if precio <= 0: return 0
    if precio <= 1000: return round(precio * 0.55, 2)
    if precio <= 3000: return round(precio * 0.445, 2)
    if precio <= 5000: return round(precio * 0.35, 2)
    if precio <= 10000: return round(precio * 0.25, 2)
    return round(precio * 0.18, 2)

def valor_por_titulo(market_value, title):
    mv, title = num(market_value), str(title).lower()
    if mv <= 0: return 0
    if "clean" in title: return mv
    if "rebuilt" in title: return round(mv * 0.75, 2)
    if "salvage" in title or "total loss" in title: return round(mv * 0.50, 2)
    return round(mv * 0.65, 2)

def estimar_reparacion(vehicle):
    text = f"{vehicle.get('damage','')} {vehicle.get('secondary_damage','')}".lower()
    airbags, run_drive, trans = str(vehicle.get("airbags","")).lower(), str(vehicle.get("run_drive","")).lower(), str(vehicle.get("transmission_status","")).lower()
    repair = 1500
    if "rear" in text: repair = 3500
    elif "side" in text: repair = 4500
    elif "front" in text: repair = 6500
    elif "mechanical" in text: repair = 5500
    elif "water" in text or "flood" in text: repair = 8500
    elif "burn" in text or "fire" in text: repair = 9000
    elif "hail" in text: repair = 3000
    if "deployed" in airbags or "yes" in airbags or "blown" in airbags: repair += 3000
    if not ("run and drive" in run_drive or "run & drive" in run_drive or "yes" in run_drive): repair += 1000
    if "bad" in trans or "unknown" in trans: repair += 1000
    return round(repair, 2)

def calcular_negocio(vehicle):
    sale_price = num(vehicle.get("price"))
    title_value = valor_por_titulo(vehicle.get("market_value"), vehicle.get("title"))
    fees = calcular_fee_subasta(sale_price)
    repair = estimar_reparacion(vehicle)
    transport, misc = 800, 1000
    desired_profit = round(title_value * 0.20, 2)
    max_bid = max(0, title_value - fees - repair - transport - misc - desired_profit)
    total_cost = sale_price + fees + repair + transport + misc
    return {
        "sale_price": sale_price, "title_value": title_value, "fees": fees, "repair": repair,
        "transport": transport, "misc": misc, "desired_profit": desired_profit,
        "max_bid": round(max_bid, 2), "total_cost": round(total_cost, 2),
        "potential_profit": round(title_value - total_cost, 2)
    }

def evaluar_riesgo(vehicle, calculos):
    reasons, risk = [], []
    title, damage, secondary = str(vehicle.get("title","")).lower(), str(vehicle.get("damage","")).lower(), str(vehicle.get("secondary_damage","")).lower()
    airbags, run_drive, trans = str(vehicle.get("airbags","")).lower(), str(vehicle.get("run_drive","")).lower(), str(vehicle.get("transmission_status","")).lower()
    if "run and drive" in run_drive or "run & drive" in run_drive or "yes" in run_drive: reasons.append("El vehículo aparece como Run & Drive.")
    else: risk.append(3); reasons.append("No está confirmado como Run & Drive.")
    if "salvage" in title or "total loss" in title: risk.append(3); reasons.append("Título salvage o total loss.")
    elif "rebuilt" in title: risk.append(2); reasons.append("Título rebuilt.")
    if "front" in damage or "front" in secondary: risk.append(3); reasons.append("Daño frontal.")
    if "mechanical" in damage or "mechanical" in secondary: risk.append(4); reasons.append("Daño mecánico.")
    if "structural" in damage or "structural" in secondary: risk.append(5); reasons.append("Posible daño estructural.")
    if "water" in damage or "flood" in damage: risk.append(5); reasons.append("Daño de agua/flood.")
    if "deployed" in airbags or "yes" in airbags or "blown" in airbags: risk.append(4); reasons.append("Airbags explotados.")
    if "bad" in trans: risk.append(4); reasons.append("Transmisión reportada con problema.")
    if calculos.get("potential_profit", 0) < 0: risk.append(3); reasons.append("La ganancia sale negativa con el precio actual.")
    total = sum(risk)
    level = "ALTO" if total >= 9 else "MEDIO" if total >= 5 else "BAJO"
    return {"score": total, "level": level, "reasons": reasons}

# ========================= IA =========================

def pedir_consejo_ia(vehicle, calculos, riesgo):
    prompt = f"""
Eres un dealer profesional experto comprando carros en Copart e IAA para reventa en Colorado.
Analiza este carro como si fueras a comprarlo con tu propio dinero. Da una opinión profunda, honesta y práctica.

DATOS DEL VEHÍCULO:
{vehicle}

CÁLCULOS:
{calculos}

RIESGO:
{riesgo}

Responde exactamente:
OPINIÓN IA COMO COMPRADOR:
VALOR REAL DE MERCADO EN COLORADO:
VALOR AJUSTADO POR TÍTULO:
OFERTA MÁXIMA QUE YO HARÍA:
COSTOS QUE MÁS ME PREOCUPAN:
RIESGO:
GANANCIA POTENCIAL:
¿LO COMPRARÍA?:
¿PARA REVENTA, SUBASTA O YONKE?:
QUÉ REVISARÍA ANTES DE PAGAR:
CONCLUSIÓN FINAL:
"""
    try:
        return client.responses.create(model="gpt-4.1-mini", input=prompt).output_text
    except Exception as e:
        return f"No se pudo consultar OpenAI. Error: {e}"

# ========================= FLUJO =========================

def unir_datos(vin, auction):
    market = consultar_marketcheck(vin)
    vehicle = {
        "vin": vin,
        "year": market.get("year"), "make": market.get("make"), "model": market.get("model"),
        "trim": market.get("trim"), "engine": market.get("engine"), "transmission": market.get("transmission"),
        "drive": market.get("drive"), "body": market.get("body"), "market_value": market.get("market_value"),
        "average_market": market.get("average_market"), "comparables": market.get("comparables", []),
        "lot": auction.get("lot"), "source": auction.get("source"), "title": auction.get("title"),
        "damage": auction.get("damage"), "secondary_damage": auction.get("secondary_damage"),
        "seller": auction.get("seller"), "price": auction.get("price"), "miles": auction.get("miles"),
        "location": auction.get("location"), "state": auction.get("state"), "auction_link": auction.get("auction_link"),
        "image": auction.get("image"), "photos": auction.get("photos", []), "run_drive": auction.get("run_drive"),
        "airbags": auction.get("airbags"), "transmission_status": auction.get("transmission_status"),
    }
    calculos = calcular_negocio(vehicle)
    riesgo = evaluar_riesgo(vehicle, calculos)
    consejo_ia = pedir_consejo_ia(vehicle, calculos, riesgo)
    return {"vehicle": vehicle, "calculos": calculos, "riesgo": riesgo, "consejo_ia": consejo_ia, "debug": {"market": market, "auction": auction}}

def analizar_por_vin(vin):
    return unir_datos(vin, consultar_subasta_por_vin(vin))

def analizar_por_lote(query):
    lot = extract_lot(query)
    auction = consultar_lote_exacto_marketcheck(lot)
    if auction.get("vin"):
        return unir_datos(auction["vin"], auction)
    copart = consultar_copart_directo_por_lote(lot)
    if copart.get("vin"):
        auction = consultar_subasta_por_vin(copart["vin"])
        auction["lot"], auction["source"], auction["auction_link"] = lot, "Copart", copart.get("copart_url")
        if auction.get("run_drive") == "No encontrado":
            auction["run_drive"] = copart.get("run_drive", "Run & Drive")
        return unir_datos(copart["vin"], auction)
    return {"error": True, "lot": lot, "copart_url": copart.get("copart_url", f"https://www.copart.com/lot/{lot}"), "copart_error": copart.get("error"), "copart": copart}

# ========================= ROUTES =========================

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/search")
def search():
    query = request.args.get("query", "").strip()
    if not query:
        return render_template("home.html")
    if is_vin(query):
        return calculator(query.upper())
    return lot_search(query)

@app.route("/calculator/<vin>")
def calculator(vin):
    data = analizar_por_vin(vin)
    return render_template("calculator.html", vehicle=data["vehicle"], calculos=data["calculos"], riesgo=data["riesgo"], consejo_ia=data["consejo_ia"])

@app.route("/lot-search/<path:lot>")
def lot_search(lot):
    data = analizar_por_lote(lot)
    if data.get("error"):
        return render_template("not_found.html", lot=data.get("lot"), copart_url=data.get("copart_url"), copart_error=data.get("copart_error"), copart=data.get("copart"))
    return render_template("calculator.html", vehicle=data["vehicle"], calculos=data["calculos"], riesgo=data["riesgo"], consejo_ia=data["consejo_ia"])

@app.route("/debug-auction/<path:query>")
def debug_auction(query):
    if is_vin(query):
        return consultar_subasta_por_vin(query.upper())
    lot = extract_lot(query)
    return {"lot": lot, "marketcheck": consultar_lote_exacto_marketcheck(lot), "copart_direct": consultar_copart_directo_por_lote(lot)}

if __name__ == "__main__":
    app.run(debug=True)
