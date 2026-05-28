import os, re, time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
load_dotenv()
URL = 'https://carfax-app.vercel.app/pro'

def buscar(patterns, text):
    for pattern in patterns:
        m = re.search(pattern, text or '', re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return 'No encontrado'

def detectar_accidentes(text):
    t=(text or '').lower()
    if 'no accidents' in t or 'no accident' in t: return '0'
    if 'total loss vehicle' in t: return 'Sí - Total Loss'
    m=re.search(r'(\d+)\s+accidents?\s+reported', text or '', re.I)
    if m: return m.group(1)
    if 'accident reported' in t or 'damage reported' in t or 'accident' in t: return 'Sí'
    return 'No encontrado'

def extraer_texto_frames(page):
    texto=''
    try: texto += page.locator('body').inner_text() + '\n'
    except Exception: pass
    for frame in page.frames:
        try: texto += frame.locator('body').inner_text() + '\n'
        except Exception: pass
    return texto

def extraer_carfax_vercel(vin):
    email=os.getenv('VERCEL_EMAIL')
    password=os.getenv('VERCEL_PASSWORD')
    if not email or not password:
        return {'vin': vin, 'error':'Faltan credenciales','detalle':'Agrega VERCEL_EMAIL y VERCEL_PASSWORD en .env'}
    request_id=None; texto_reporte=''
    with sync_playwright() as p:
        browser = p.chromium.launch(
    channel="chromium",
    headless=True,
    args=[
        "--no-sandbox",
        "--disable-dev-shm-usage"
    ]
)
        context=browser.new_context()
        page=context.new_page()
        def cap(response):
            nonlocal request_id
            if '/api/pro/requests' in response.url:
                try: request_id=response.json().get('request',{}).get('id'); print('REQUEST ID:', request_id)
                except Exception as e: print('ERROR REQUEST ID:', e)
        page.on('response', cap)
        page.goto(URL, wait_until='networkidle')
        page.fill('input[type="email"]', email)
        page.fill('input[type="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_timeout(6000)
        page.locator('#vin').fill(vin)
        try: page.select_option('select','CO')
        except Exception: pass
        page.screenshot(path='before_run_report.png', full_page=True)
        page.get_by_role('button', name='Run Report').click()
        for _ in range(30):
            if request_id: break
            page.wait_for_timeout(1000)
        try:
            page.wait_for_selector("text=Open PDF", timeout=60000)
        except:
            pass
        for p2 in context.pages:
            try:
                print('PAGE:', p2.url)
                texto_reporte += extraer_texto_frames(p2)
            except Exception: pass
        try:
            with open('debug_frames_text.txt','w',encoding='utf-8') as f: f.write(texto_reporte)
        except Exception: pass
        browser.close()
    pdf_url = f'https://carfax-app.vercel.app/api/requests/{request_id}/pdf' if request_id else 'No encontrado'
    text=texto_reporte
    value=buscar([r'CARFAX VALUE\s*\$([\d,]+)', r'CARFAX Value\s*\$([\d,]+)'], text)
    title=buscar([r'(Total Loss Vehicle)', r'(Salvage Title)', r'(Rebuilt Title)', r'(Clean Title)', r'(Flood Title)', r'(Total Loss)', r'(Salvage)', r'(Rebuilt)'], text)
    miles=buscar([r'(\d{1,3},\d{3})\s*mi\s*\|\s*VIN', r'(\d{1,3},\d{3})\s*mi'], text)
    return {
        'vin': vin, 'miles': miles, 'carfax_value': value, 'retail_value': value,
        'wholesale_value': 'No encontrado', 'title': title, 'branded_title': title,
        'owners': buscar([r'(\d+)\s+Owner', r'Owner\(s\)\s*(\d+)'], text),
        'accidents': detectar_accidentes(text),
        'service_records': buscar([r'(\d+)\s+Service Records?', r'Service Records?\s*[:\-]?\s*(\d+)'], text),
        'engine': buscar([r'Engine:\s*([^\n]+)', r'([0-9]\.[0-9]L\s+[A-Za-z0-9\s\-]+)'], text),
        'drive_type': buscar([r'(4WD\/4-Wheel Drive\/4x4)', r'(All-Wheel Drive)', r'(AWD)', r'(FWD)', r'(RWD)', r'(4WD)'], text),
        'body': buscar([r'Body Style:\s*([^\n]+)', r'(Sport Utility Vehicle \(SUV\))', r'(SUV)', r'(Sedan)', r'(Coupe)', r'(Pickup)', r'(Hatchback)'], text),
        'pdf_url': pdf_url, 'raw_text': text[:12000]
    }
