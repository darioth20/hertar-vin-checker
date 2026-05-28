import os
import re
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
URL = 'https://carfax-app.vercel.app/pro'


def money_to_number(value):
    try:
        return int(float(str(value).replace('$','').replace(',','').strip()))
    except Exception:
        return 0


def buscar(patterns, text):
    for pattern in patterns:
        m = re.search(pattern, text or '', re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return 'No encontrado'


def detectar_accidentes(text):
    t = (text or '').lower()
    if 'no accidents' in t or 'no accident' in t:
        return '0'
    if 'total loss vehicle' in t:
        return 'Sí - Total Loss'
    if 'accident reported' in t or 'damage reported' in t:
        return 'Sí'
    m = re.search(r'(\d+)\s+accidents?\s+reported', text or '', re.IGNORECASE)
    if m:
        return m.group(1)
    return 'No encontrado'


def extraer_texto_frames(page):
    texto = ''
    try:
        texto += page.locator('body').inner_text(timeout=5000) + '\n'
    except Exception:
        pass
    for frame in page.frames:
        try:
            texto += frame.locator('body').inner_text(timeout=3000) + '\n'
        except Exception:
            pass
    return texto


def normalizar(texto, vin, request_id=None):
    value = money_to_number(buscar([
        r'CARFAX VALUE\s*\$([\d,]+)',
        r'CARFAX Value\s*\$([\d,]+)',
        r'Retail\s+Value\s*\$([\d,]+)'
    ], texto))
    if not value:
        value = 0
    return {
        'vin': vin,
        'miles': buscar([r'(\d{1,3},\d{3})\s*mi\s*\|\s*VIN', r'(\d{1,3},\d{3})\s*mi'], texto),
        'carfax_value': value,
        'retail_value': value,
        'wholesale_value': int(value * 0.82) if value else 0,
        'title': buscar([r'(Total Loss Vehicle)', r'(Salvage Title)', r'(Rebuilt Title)', r'(Clean Title)', r'(Flood Title)', r'(Total Loss)', r'(Salvage)', r'(Rebuilt)'], texto),
        'branded_title': buscar([r'(Total Loss Vehicle)', r'(Salvage Title)', r'(Rebuilt Title)', r'(Flood Title)', r'(Branded Title)'], texto),
        'owners': buscar([r'(\d+)\s+Owner', r'Owner\(s\)\s*(\d+)'], texto),
        'accidents': detectar_accidentes(texto),
        'service_records': buscar([r'(\d+)\s+Service Records?', r'Service Records?\s*[:\-]?\s*(\d+)'], texto),
        'engine': buscar([r'Engine:\s*([^\n]+)', r'Engine\s*\n([^\n]+)', r'([0-9]\.[0-9]L\s+[A-Za-z0-9\s\-]+)'], texto),
        'drive_type': buscar([r'Drivetrain:\s*([^\n]+)', r'Drive Type:\s*([^\n]+)', r'(4WD\/4-Wheel Drive\/4x4)', r'(All-Wheel Drive)', r'(AWD)', r'(FWD)', r'(RWD)', r'(4WD)'], texto),
        'body': buscar([r'Body Style:\s*([^\n]+)', r'(Sport Utility Vehicle \(SUV\))', r'(SUV)', r'(Sedan)', r'(Coupe)', r'(Pickup)', r'(Hatchback)'], texto),
        'pdf_url': f'https://carfax-app.vercel.app/api/requests/{request_id}/pdf' if request_id else 'No encontrado',
        'raw_text': (texto or '')[:12000],
    }


def extraer_carfax_vercel(vin):
    email = os.getenv('VERCEL_EMAIL')
    password = os.getenv('VERCEL_PASSWORD')
    if not email or not password:
        return {'vin': vin, 'error': 'Faltan credenciales', 'miles':'No encontrado','carfax_value':0,'retail_value':0,'wholesale_value':0,'title':'No encontrado','branded_title':'No encontrado','owners':'No encontrado','accidents':'No encontrado','service_records':'No encontrado','engine':'No encontrado','drive_type':'No encontrado','body':'No encontrado','pdf_url':'No encontrado'}

    request_id = None
    texto = ''
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
        context = browser.new_context()
        page = context.new_page()

        def on_response(response):
            nonlocal request_id
            if '/api/pro/requests' in response.url:
                try:
                    data = response.json()
                    request_id = data.get('request', {}).get('id') or request_id
                    print('REQUEST ID:', request_id)
                except Exception as e:
                    print('REQUEST CAPTURE ERROR:', e)

        page.on('response', on_response)
        page.goto(URL, wait_until='networkidle', timeout=45000)
        page.fill('input[type="email"]', email)
        page.fill('input[type="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_timeout(5000)
        page.locator('#vin').fill(vin)
        try:
            page.select_option('select', 'CO')
        except Exception:
            pass
        page.get_by_role('button', name='Run Report').click()

        # esperar request id primero
        for _ in range(20):
            if request_id:
                break
            page.wait_for_timeout(1000)

        # esperar pantalla de reporte/PDF pero sin exceder Gunicorn
        try:
            page.wait_for_selector('text=Open PDF', timeout=45000)
        except Exception:
            pass

        for p2 in context.pages:
            try:
                texto += extraer_texto_frames(p2)
            except Exception:
                pass
        browser.close()

    # fallback si no extrajo texto visual suficiente
    if not texto.strip():
        texto = ''
    carfax = normalizar(texto, vin, request_id)
    return carfax
