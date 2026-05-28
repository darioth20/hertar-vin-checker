def money_to_number(value):
    if isinstance(value, (int, float)):
        return float(value)
    if not value:
        return 0
    try:
        return float(str(value).replace('$', '').replace(',', '').strip())
    except Exception:
        return 0


def calcular_finanzas_base(carfax, market, ia):
    market_value = money_to_number(market.get('colorado_average') or market.get('market_value'))
    if not market_value:
        market_value = money_to_number(carfax.get('retail_value') or carfax.get('carfax_value'))

    max_bid = money_to_number(ia.get('max_bid')) if isinstance(ia, dict) else 0
    repair = money_to_number(ia.get('estimated_repair')) if isinstance(ia, dict) else 0

    if not max_bid:
        max_bid = max(market_value * 0.45, 0) if market_value else 0
    if not repair:
        repair = 2500

    fees = 1200
    transport = 500
    profit = market_value - max_bid - fees - repair - transport

    return {
        'market_value_number': round(market_value),
        'max_bid_number': round(max_bid),
        'estimated_repair_number': round(repair),
        'default_fees': fees,
        'default_transport': transport,
        'profit_number': round(profit),
    }
