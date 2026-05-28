def money_to_number(value):
    try:
        return int(float(str(value).replace('$','').replace(',','').strip()))
    except Exception:
        return 0


def build_financial(vin, carfax, market):
    carfax_value = money_to_number(carfax.get('carfax_value'))
    market_value = money_to_number(market.get('market_value') or carfax_value)
    if not market_value:
        market_value = carfax_value

    miles = money_to_number(carfax.get('miles') or market.get('miles'))
    title = str(carfax.get('title','')).lower()
    accidents = str(carfax.get('accidents','')).lower()

    discount = 0
    risk_points = 0
    reasons = []

    if any(x in title for x in ['total loss','salvage','rebuilt','flood']):
        discount += 3500
        risk_points += 3
        reasons.append('Título con riesgo/branded title.')

    if accidents not in ['', '0', 'no encontrado', 'none']:
        discount += 1500
        risk_points += 2
        reasons.append('Historial de accidente o daño reportado.')

    if miles > 120000:
        discount += 1200
        risk_points += 1
        reasons.append('Millaje alto para reventa.')

    estimated_repair = 2500 + (1500 if risk_points >= 3 else 0)
    title_value = max(market_value - discount, 0)
    max_bid = max(title_value - estimated_repair - 1200 - 500 - 1800, 0)

    risk = 'Bajo'
    if risk_points >= 4:
        risk = 'Alto'
    elif risk_points >= 2:
        risk = 'Medio'

    decision = 'BUY' if max_bid > 0 and risk != 'Alto' else 'DO NOT BUY'
    if risk == 'Alto' and max_bid > 0:
        decision = 'BUY ONLY CHEAP'

    ai_reason = (
        f"Valor base analizado: ${market_value:,}. Descuento por riesgo: ${discount:,}. "
        f"Valor ajustado por título: ${title_value:,}. Oferta máxima sugerida: ${max_bid:,}. "
        + (' '.join(reasons) if reasons else 'Sin alertas fuertes detectadas.')
    )

    return {
        'title_value': title_value,
        'max_bid': max_bid,
        'estimated_repair': estimated_repair,
        'risk': risk,
        'ai_decision': decision,
        'ai_reason': ai_reason,
    }
