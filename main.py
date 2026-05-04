from flask import Flask, jsonify, send_file, request
import yfinance as yf
from datetime import datetime, timedelta
import traceback
import os

app = Flask(__name__)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/quote')
def quote():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        info = t.info
        return jsonify({
            'name': info.get('longName') or info.get('shortName',''),
            'exchange': info.get('exchange',''),
            'price': info.get('currentPrice') or info.get('regularMarketPrice',0),
            'open': info.get('open') or info.get('regularMarketOpen',0),
            'high': info.get('dayHigh') or info.get('regularMarketDayHigh',0),
            'low': info.get('dayLow') or info.get('regularMarketDayLow',0),
            'prevClose': info.get('previousClose') or info.get('regularMarketPreviousClose',0),
            'volume': info.get('volume') or info.get('regularMarketVolume',0),
            'avgVolume': info.get('averageVolume',0),
            'mktCap': info.get('marketCap',0),
            'pe': info.get('trailingPE',0),
            'fwdPE': info.get('forwardPE',0),
            'eps': info.get('trailingEps',0),
            'ps': info.get('priceToSalesTrailing12Months',0),
            'pb': info.get('priceToBook',0),
            'beta': info.get('beta',0),
            'divYield': info.get('dividendYield',0),
            'sharesOut': info.get('sharesOutstanding',0),
            'week52High': info.get('fiftyTwoWeekHigh',0),
            'week52Low': info.get('fiftyTwoWeekLow',0),
            'revenue': info.get('totalRevenue',0),
            'grossMargin': info.get('grossMargins',0),
            'sector': info.get('sector',''),
            'industry': info.get('industry',''),
            'employees': info.get('fullTimeEmployees',0),
            'website': info.get('website',''),
            'description': info.get('longBusinessSummary',''),
            'targetPrice': info.get('targetMeanPrice',0),
            'recommendation': info.get('recommendationKey',''),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart')
def chart():
    sym = request.args.get('symbol','').upper()
    days = int(request.args.get('days', 365))
    try:
        period_map = {
            30: ('3mo','1d'),
            90: ('6mo','1d'),
            180: ('6mo','1d'),
            365: ('1y','1d'),
            365*3: ('5y','1wk'),
            365*5: ('10y','1wk'),
        }
        # find closest period
        closest = min(period_map.keys(), key=lambda k: abs(k-days))
        period, interval = period_map[closest]
        t = yf.Ticker(sym)
        hist = t.history(period=period, interval=interval)
        dates = [str(d.date()) for d in hist.index]
        closes = [round(float(c), 2) for c in hist['Close']]
        return jsonify({'dates': dates, 'closes': closes})
    except Exception as e:
        return jsonify({'error': str(e), 'dates': [], 'closes': []}), 500

@app.route('/api/earnings')
def earnings():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        # Quarterly earnings
        eq = t.quarterly_earnings
        result = []
        if eq is not None and not eq.empty:
            for idx, row in eq.iterrows():
                result.append({
                    'period': str(idx),
                    'actual': round(float(row['Actual']),2) if 'Actual' in row else None,
                    'estimate': round(float(row['Estimate']),2) if 'Estimate' in row else None,
                })
        return jsonify(result)
    except Exception as e:
        return jsonify([])

@app.route('/api/revenue')
def revenue():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        fin = t.quarterly_financials
        result = []
        if fin is not None and not fin.empty:
            rev_row = None
            for label in ['Total Revenue','Revenue']:
                if label in fin.index:
                    rev_row = fin.loc[label]
                    break
            ni_row = None
            for label in ['Net Income','Net Income Common Stockholders']:
                if label in fin.index:
                    ni_row = fin.loc[label]
                    break
            cols = list(fin.columns[:8])
            cols.reverse()
            for col in cols:
                rev = float(rev_row[col]) if rev_row is not None and col in rev_row.index else 0
                ni  = float(ni_row[col])  if ni_row  is not None and col in ni_row.index  else 0
                result.append({
                    'date': str(col.date()) if hasattr(col,'date') else str(col)[:10],
                    'revenue': rev,
                    'netIncome': ni
                })
        return jsonify(result)
    except Exception as e:
        return jsonify([])

@app.route('/api/recommendations')
def recommendations():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        rec = t.recommendations
        if rec is None or rec.empty:
            return jsonify({})
        # get most recent period
        latest = rec.iloc[-1] if len(rec) else None
        if latest is None:
            return jsonify({})
        return jsonify({
            'strongBuy': int(latest.get('strongBuy',0)),
            'buy': int(latest.get('buy',0)),
            'hold': int(latest.get('hold',0)),
            'sell': int(latest.get('sell',0)),
            'strongSell': int(latest.get('strongSell',0)),
        })
    except Exception as e:
        return jsonify({})

@app.route('/api/news')
def news():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        raw = t.news or []
        result = []
        for n in raw[:20]:
            result.append({
                'title': n.get('title',''),
                'url': n.get('link',''),
                'source': n.get('publisher',''),
                'time': n.get('providerPublishTime',0),
            })
        return jsonify(result)
    except Exception as e:
        return jsonify([])

@app.route('/api/market')
def market():
    syms = request.args.get('symbols','SPY,QQQ,BTC-USD').split(',')
    result = {}
    for sym in syms:
        try:
            t = yf.Ticker(sym)
            info = t.info
            price = info.get('currentPrice') or info.get('regularMarketPrice',0)
            prev  = info.get('previousClose') or info.get('regularMarketPreviousClose',0)
            chg   = round((price-prev)/prev*100,2) if prev else 0
            result[sym] = {'price': price, 'change': chg}
        except:
            result[sym] = {'price':0,'change':0}
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
