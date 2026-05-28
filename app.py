import os
from flask import Flask, render_template, request, redirect, jsonify
from dotenv import load_dotenv
from services.carfax_vercel import extraer_carfax_vercel
from services.marketcheck import buscar_marketcheck
from services.nhtsa import decode_vin
from services.financial import calcular_financiero
from services.utils import money_to_number
load_dotenv()
app=Flask(__name__)

def build_vehicle(vin):
    carfax=extraer_carfax_vercel(vin)
    market=buscar_marketcheck(vin)
    nhtsa=decode_vin(vin)
    # Fill missing market fields from NHTSA
    for k in ['engine','drivetrain','transmission','body']:
        if market.get(k) in [None,'','No encontrado']:
            mapn={'drivetrain':'drivetrain','transmission':'transmission','engine':'engine','body':'body'}
            market[k]=nhtsa.get(mapn[k],'No encontrado')
    carfax_value=money_to_number(carfax.get('carfax_value'))
    carfax['carfax_value']=carfax_value
    carfax['retail_value']=carfax_value
    carfax['wholesale_value']=int(carfax_value*0.82) if carfax_value else 0
    if carfax.get('body') in [None,'','No encontrado']:
        carfax['body']=nhtsa.get('body','No encontrado')
    if carfax.get('engine') in [None,'','No encontrado']:
        carfax['engine']=nhtsa.get('engine','No encontrado')
    if carfax.get('drive_type') in [None,'','No encontrado']:
        carfax['drive_type']=nhtsa.get('drivetrain','No encontrado')
    if not market.get('market_value'):
        market['market_value']=carfax_value
    if not market.get('colorado_average'):
        market['colorado_average']=market.get('market_value',0)
    financial=calcular_financiero(carfax, market)
    return {'vin': vin, 'carfax': carfax, 'marketcheck': market, 'financial': financial, 'debug': {'market_error': market.get('error',''), 'nhtsa': nhtsa}}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    q=request.form.get('q','').strip().upper()
    if not q: return redirect('/')
    return redirect(f'/lot/{q}')

@app.route('/lot/<vin>')
def lot(vin):
    vehicle=build_vehicle(vin.upper().strip())
    return render_template('lot.html', vehicle=vehicle)

@app.route('/debug-carfax/<vin>')
def debug_carfax(vin): return jsonify(extraer_carfax_vercel(vin.upper().strip()))

@app.route('/api/lot/<vin>')
def api_lot(vin): return jsonify(build_vehicle(vin.upper().strip()))

@app.route('/health')
def health(): return jsonify({'status':'ok'})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT',5000)), debug=True)
