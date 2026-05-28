import os, requests
from .utils import money_to_number

def buscar_marketcheck(vin):
    api_key = os.getenv('MARKETCHECK_API_KEY')
    if not api_key:
        return {
            'market_value': 0, 'colorado_average': 0, 'miles': 'No encontrado',
            'accidents': 'No encontrado', 'transmission': 'No encontrado',
            'drivetrain': 'No encontrado', 'engine': 'No encontrado', 'body': 'No encontrado',
            'error': 'MARKETCHECK_API_KEY no configurada'
        }
    try:
        specs_url = f"https://api.marketcheck.com/v2/decode/car/{vin}/specs?api_key={api_key}"
        specs = requests.get(specs_url, timeout=20).json()
        engine = specs.get('engine') or specs.get('engine_description') or 'No encontrado'
        drivetrain = specs.get('drivetrain') or 'No encontrado'
        transmission = specs.get('transmission') or 'No encontrado'
        body = specs.get('body_type') or specs.get('body') or 'No encontrado'
        year = specs.get('year')
        make = specs.get('make')
        model = specs.get('model')

        market_value = 0
        colorado_average = 0
        if year and make and model:
            search_url = 'https://api.marketcheck.com/v2/search/car/active'
            params = {'api_key': api_key, 'year': year, 'make': make, 'model': model, 'state': 'CO', 'rows': 50}
            data = requests.get(search_url, params=params, timeout=20).json()
            prices = [money_to_number(x.get('price')) for x in data.get('listings', []) if money_to_number(x.get('price')) > 0]
            if prices:
                colorado_average = int(sum(prices)/len(prices))
                market_value = colorado_average
        return {
            'market_value': market_value,
            'colorado_average': colorado_average,
            'miles': 'No encontrado',
            'accidents': 'No encontrado',
            'transmission': transmission,
            'drivetrain': drivetrain,
            'engine': engine,
            'body': body,
            'error': ''
        }
    except Exception as e:
        return {
            'market_value': 0, 'colorado_average': 0, 'miles': 'No encontrado',
            'accidents': 'No encontrado', 'transmission': 'No encontrado',
            'drivetrain': 'No encontrado', 'engine': 'No encontrado', 'body': 'No encontrado',
            'error': str(e)
        }
