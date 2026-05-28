import os
import requests


def num(v):
    try:
        return int(float(str(v).replace('$','').replace(',','').strip()))
    except Exception:
        return 0


def buscar_marketcheck(vin, carfax=None):
    api_key = os.getenv('MARKETCHECK_API_KEY')
    carfax = carfax or {}
    fallback_value = num(carfax.get('carfax_value'))
    fallback_miles = carfax.get('miles', 'No encontrado')

    base = {
        'market_value': fallback_value,
        'colorado_average': fallback_value,
        'transmission': 'No encontrado',
        'drivetrain': carfax.get('drive_type', 'No encontrado'),
        'engine': carfax.get('engine', 'No encontrado'),
        'miles': fallback_miles,
        'accidents': carfax.get('accidents', 'No encontrado'),
        'error': ''
    }

    if not api_key:
        base['error'] = 'MARKETCHECK_API_KEY no configurado; usando CARFAX fallback.'
        return base

    try:
        url = f'https://api.marketcheck.com/v2/decode/car/{vin}/specs'
        r = requests.get(url, params={'api_key': api_key}, timeout=12)
        if r.status_code != 200:
            base['error'] = f'MarketCheck status {r.status_code}; usando fallback.'
            return base
        data = r.json()
        build = data.get('build', data)
        base['transmission'] = build.get('transmission') or build.get('transmission_type') or base['transmission']
        base['drivetrain'] = build.get('drivetrain') or base['drivetrain']
        engine = build.get('engine') or build.get('engine_size') or base['engine']
        base['engine'] = str(engine)
        return base
    except Exception as e:
        base['error'] = str(e)
        return base
