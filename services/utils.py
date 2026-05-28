def money_to_number(value):
    try:
        return int(float(str(value).replace('$','').replace(',','').strip()))
    except Exception:
        return 0

def fmt_money(value):
    n = money_to_number(value)
    return f"${n:,}" if n else "$0"
