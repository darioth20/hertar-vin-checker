from .utils import money_to_number

def calcular_financiero(carfax, marketcheck, auction=None):
    carfax_value = money_to_number(carfax.get('carfax_value'))
    market_value = money_to_number(marketcheck.get('market_value')) or carfax_value
    miles = money_to_number(carfax.get('miles'))
    title = str(carfax.get('title',''))
    accidents = str(carfax.get('accidents',''))
    discount = 0
    risk_points = 0
    reasons=[]
    if any(x.lower() in title.lower() for x in ['total loss','salvage','rebuilt','flood']):
        discount += 3500; risk_points += 3; reasons.append('título con marca o pérdida total')
    if accidents not in ['0','No encontrado','','None']:
        discount += 1500; risk_points += 2; reasons.append('historial de accidente/daño')
    if miles > 120000:
        discount += 1200; risk_points += 1; reasons.append('millas altas')
    estimated_repair = 2500
    title_value = max(market_value - discount, 0)
    max_bid = max(title_value - estimated_repair - 1200 - 500, 0)
    if risk_points >= 5:
        decision='DO NOT BUY'; risk='ALTO'
    elif risk_points >= 3:
        decision='BUY ONLY CHEAP'; risk='MEDIO'
    else:
        decision='BUY'; risk='BAJO'
    ai_reason = ('Vehículo analizado con CARFAX/Vercel, MarketCheck/NHTSA, millas, título y accidentes. ' +
                 ('Riesgos detectados: '+', '.join(reasons)+'. ' if reasons else 'No hay riesgos graves detectados. ') +
                 f'Valor ajustado por título: ${title_value:,}. Oferta máxima recomendada: ${max_bid:,}.')
    return {'title_value': title_value, 'max_bid': max_bid, 'estimated_repair': estimated_repair, 'risk': risk, 'ai_decision': decision, 'ai_reason': ai_reason}
