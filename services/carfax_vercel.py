import os
import re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

URL = "https://carfax-app.vercel.app/pro"


def money_to_number(value):
    try:
        return int(float(str(value).replace('$', '').replace(',', '').strip()))
    except Exception:
        return 0


def buscar(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "No encontrado"


def detectar_accidentes(text):
    t = (text or "").lower()
    if "no accidents" in t or "no accident" in t:
        return "0"
    if "total loss vehicle" in t:
        return "Sí - Total Loss"
    if "accident reported" in t or "damage reported" in t:
        return "Sí"
    match = re.search(r"(\d+)\s+accidents?\s+reported", text or "", re.IGNORECASE)
    if match:
        return match.group(1)
    return "No encontrado"


def extraer_texto_frames(page):
    texto = ""
    try:
        texto += page.locator("body").inner_text(timeout=3000) + "\n"
    except Exception:
        pass
    for frame in page.frames:
        try:
            texto += frame.locator("body").inner_text(timeout=3000) + "\n"
        except Exception:
            pass
    return texto


def extraer_carfax_vercel(vin):
    email = os.getenv("VERCEL_EMAIL")
    password = os.getenv("VERCEL_PASSWORD")

    if not email or not password:
        return {
            "vin": vin,
            "error": "Faltan credenciales",
            "detalle": "Agrega VERCEL_EMAIL y VERCEL_PASSWORD en .env",
            "miles": "No encontrado",
            "carfax_value": 0,
            "pdf_url": "No encontrado",
        }

    request_id = None
    texto_reporte = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context()
        page = context.new_page()

        def capturar_response(response):
            nonlocal request_id
            if "/api/pro/requests" in response.url:
                try:
                    data = response.json()
                    request_id = data.get("request", {}).get("id")
                    print("REQUEST ID:", request_id)
                except Exception as e:
                    print("ERROR REQUEST ID:", e)

        page.on("response", capturar_response)

        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.fill('input[type="email"]', email, timeout=30000)
        page.fill('input[type="password"]', password, timeout=30000)
        page.click('button[type="submit"]', timeout=30000)
        page.wait_for_timeout(4000)

        page.locator("#vin").fill(vin, timeout=30000)
        try:
            page.select_option("select", "CO", timeout=5000)
        except Exception:
            pass

        page.get_by_role("button", name="Run Report").click(timeout=30000)
        print("CLICK RUN REPORT HECHO")

        for _ in range(20):
            if request_id:
                break
            page.wait_for_timeout(1000)

        try:
            page.wait_for_selector("text=Open PDF", timeout=15000)
        except Exception:
            pass

        for p2 in context.pages:
            try:
                texto_reporte += extraer_texto_frames(p2)
            except Exception:
                pass

        try:
            with open("debug_frames_text.txt", "w", encoding="utf-8") as f:
                f.write(texto_reporte)
        except Exception:
            pass

        browser.close()

    pdf_url = "No encontrado"
    if request_id:
        pdf_url = f"https://carfax-app.vercel.app/api/requests/{request_id}/pdf"

    text = texto_reporte or ""
    carfax_value_raw = buscar([
        r"CARFAX VALUE\s*\$([\d,]+)",
        r"CARFAX Value\s*\$([\d,]+)",
        r"\$([\d,]+)"
    ], text)

    return {
        "vin": vin,
        "miles": buscar([
            r"(\d{1,3},\d{3})\s*mi\s*\|\s*VIN",
            r"(\d{1,3},\d{3})\s*mi",
            r"Odometer\s*([\d,]+)",
        ], text),
        "carfax_value": money_to_number(carfax_value_raw),
        "title": buscar([
            r"(Total Loss Vehicle)",
            r"(Salvage Title)",
            r"(Rebuilt Title)",
            r"(Clean Title)",
            r"(Flood Title)",
            r"(Total Loss)",
            r"(Salvage)",
            r"(Rebuilt)",
        ], text),
        "branded_title": buscar([
            r"(Total Loss Vehicle)",
            r"(Salvage Title)",
            r"(Rebuilt Title)",
            r"(Flood Title)",
            r"(No Branded Title)",
        ], text),
        "owners": buscar([
            r"(\d+)\s+Owner",
            r"Owner\(s\)\s*(\d+)",
        ], text),
        "accidents": detectar_accidentes(text),
        "service_records": buscar([
            r"(\d+)\s+Service Records?",
            r"(\d+)\s+Service",
        ], text),
        "engine": buscar([
            r"Engine:\s*([^\n]+)",
            r"Engine\s*\n([^\n]+)",
            r"([0-9]\.[0-9]L\s+[A-Za-z0-9\s\-]+)",
        ], text),
        "drive_type": buscar([
            r"Drivetrain:\s*([^\n]+)",
            r"Drive Type:\s*([^\n]+)",
            r"(4WD\/4-Wheel Drive\/4x4)",
            r"(All-Wheel Drive)",
            r"(AWD)",
            r"(FWD)",
            r"(RWD)",
            r"(4WD)",
        ], text),
        "body": buscar([
            r"Body Style:\s*([^\n]+)",
            r"(Sport Utility Vehicle \(SUV\))",
            r"(SUV)",
            r"(Sedan)",
            r"(Coupe)",
            r"(Pickup)",
            r"(Hatchback)",
        ], text),
        "pdf_url": pdf_url,
        "raw_text": text[:12000],
    }
