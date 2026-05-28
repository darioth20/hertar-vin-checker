import requests

def decode_vin(vin):
    try:
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
        data = requests.get(url, timeout=15).json()
        results = {r.get('Variable'): r.get('Value') for r in data.get('Results', []) if r.get('Value')}
        return {
            'year': results.get('Model Year', 'No encontrado'),
            'make': results.get('Make', 'No encontrado'),
            'model': results.get('Model', 'No encontrado'),
            'trim': results.get('Trim', ''),
            'engine': results.get('Displacement (L)', '') + 'L ' + (results.get('Engine Configuration') or results.get('Engine Number of Cylinders','')),
            'body': results.get('Body Class', 'No encontrado'),
            'drivetrain': results.get('Drive Type', 'No encontrado'),
            'transmission': results.get('Transmission Style', 'No encontrado'),
        }
    except Exception as e:
        return {'error': str(e)}
