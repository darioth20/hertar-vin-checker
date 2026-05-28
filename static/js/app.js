function n(id){
    const el = document.getElementById(id);
    if(!el) return 0;
    return parseFloat(el.value || '0') || 0;
}
function money(v){
    const sign = v < 0 ? '-' : '';
    return sign + '$' + Math.abs(Math.round(v)).toLocaleString();
}
function calcularGanancia(){
    const market = n('marketValue');
    const pay = n('payPrice');
    const fees = n('fees');
    const repairs = n('repairs');
    const transport = n('transport');
    const profit = market - pay - fees - repairs - transport;
    const profitEl = document.getElementById('profit');
    const profitTop = document.getElementById('profitTop');
    if(profitEl) profitEl.innerText = money(profit);
    if(profitTop) profitTop.innerText = money(profit);
}
document.querySelectorAll('input').forEach(input => input.addEventListener('input', calcularGanancia));
calcularGanancia();
