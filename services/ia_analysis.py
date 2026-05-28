import os
import json
from openai import OpenAI


def fallback_analysis(carfax, market, nhtsa):
    title = str(carfax.get('title') or carfax.get('title_type') or '').lower()
    miles = str(carfax.get('miles') or '').replace(',', '')
    accidents = str(carfax.get('accidents') or '').lower()

    risk = 'Medio'
    title_discount = 0.75

    if 'total loss' in title or 'salvage' in title:
        risk = 'Alto'
        title_discount = 0.45
    elif 'rebuilt' in title:
        risk = 'Medio-Alto'
        title_discount = 0.65
    elif 'clean' in title:
        risk = 'Bajo-Medio'
        title_discount = 0.9

    try:
        m = int(miles)
        if m > 160000:
            risk = 'Alto'
        elif m > 120000 and risk == 'Bajo-Medio':
            risk = 'Medio'
    except Exception:
        pass

    market_value = market.get('colorado_average') or market.get('market_value') or carfax.get('carfax_value') or 0
    try:
        mv = float(str(market_value).replace('$', '').replace(',', ''))
    except Exception:
        mv = 0

    title_value = round(mv * title_discount) if mv else 0
    estimated_repair = 3500 if risk == 'Alto' else 2200
    max_bid = max(round(title_value - estimated_repair - 1700 - 2000), 0) if title_value else 0

    return {
        'title_value': f'${title_value:,}' if title_value else 'No calculado',
        'max_bid': f'${max_bid:,}' if max_bid else 'No calculado',
        'estimated_repair': f'${estimated_repair:,}',
        'risk': risk,
        'advice': 'Comprar solo barato' if risk in ['Alto', 'Medio-Alto'] else 'Comprar si los números dan',
        'reason': 'Estimación automática basada en título, millas, accidentes y valor de mercado. Verifica daños, airbags, motor y transmisión antes de ofertar.'
    }


def analizar_finanzas_ia(vin, carfax, market, nhtsa):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key.startswith('TU_'):
        return fallback_analysis(carfax, market, nhtsa)

    try:
        client = OpenAI(api_key=api_key)
        prompt = f'''
Eres experto en subastas de carros para reventa en Colorado.
Analiza este VIN y responde SOLO JSON válido.

VIN: {vin}
CARFAX/VERCEL: {carfax}
MARKETCHECK: {market}
NHTSA: {nhtsa}

Campos JSON:
{{
  "title_value": "$0",
  "max_bid": "$0",
  "estimated_repair": "$0",
  "risk": "Bajo/Medio/Alto",
  "advice": "Comprar/Comprar solo barato/No comprar",
  "reason": "motivo corto en español"
}}

Reglas:
- Calcula valor por título según clean, rebuilt, salvage, total loss o branded.
- Ajusta por millas, accidentes, branded title, CARFAX value, MarketCheck Colorado y demanda local.
- Sé conservador.
- Incluye oferta máxima para subasta pensando en ganancia.
'''
        res = client.chat.completions.create(
            model='gpt-4.1-mini',
            messages=[
                {'role': 'system', 'content': 'Eres analista automotriz experto en CARFAX, MarketCheck, títulos salvage/rebuilt y subastas en Colorado.'},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.2,
        )
        text = res.choices[0].message.content.strip()
        return json.loads(text)
    except Exception as e:
        out = fallback_analysis(carfax, market, nhtsa)
        out['ai_error'] = str(e)
        return out
