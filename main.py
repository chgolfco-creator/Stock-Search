from flask import Flask, jsonify, send_file, request
import yfinance as yf
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
        i = t.info
        return jsonify({
            'name': i.get('longName') or i.get('shortName',''),
            'exchange': i.get('exchange',''),
            'price': i.get('currentPrice') or i.get('regularMarketPrice',0),
            'open': i.get('open',0), 'high': i.get('dayHigh',0), 'low': i.get('dayLow',0),
            'prevClose': i.get('previousClose',0),
            'mktCap': i.get('marketCap',0), 'pe': i.get('trailingPE',0),
            'ps': i.get('priceToSalesTrailing12Months',0), 'eps': i.get('trailingEps',0),
            'revenue': i.get('totalRevenue',0), 'revenueGrowth': i.get('revenueGrowth'),
            'earningsGrowth': i.get('earningsGrowth'), 'beta': i.get('beta',0),
            'week52High': i.get('fiftyTwoWeekHigh',0), 'week52Low': i.get('fiftyTwoWeekLow',0),
            'targetPrice': i.get('targetMeanPrice',0), 'sector': i.get('sector',''),
            'industry': i.get('industry',''), 'employees': i.get('fullTimeEmployees',0),
            'website': i.get('website',''), 'description': i.get('longBusinessSummary',''),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart')
def chart():
    sym = request.args.get('symbol','').upper()
    days = int(request.args.get('days', 365))
    try:
        period_map = {30:('3mo','1d'),90:('6mo','1d'),180:('6mo','1d'),365:('1y','1d'),365*3:('5y','1wk'),365*5:('10y','1wk')}
        closest = min(period_map.keys(), key=lambda k: abs(k-days))
        period, interval = period_map[closest]
        hist = yf.Ticker(sym).history(period=period, interval=interval)
        return jsonify({'dates':[str(d.date()) for d in hist.index],'closes':[round(float(c),2) for c in hist['Close']]})
    except Exception as e:
        return jsonify({'error':str(e),'dates':[],'closes':[]}), 500

@app.route('/api/earnings')
def earnings():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        result = []
        try:
            ed = t.earnings_dates
            if ed is not None and not ed.empty:
                ed = ed.dropna(subset=['EPS Estimate','Reported EPS'])
                for idx, row in ed.iterrows():
                    result.append({'period':str(idx.date()),'actual':round(float(row['Reported EPS']),2),'estimate':round(float(row['EPS Estimate']),2)})
                result = list(reversed(result))
        except: pass
        if not result:
            try:
                eq = t.quarterly_earnings
                if eq is not None and not eq.empty:
                    for idx, row in eq.iterrows():
                        result.append({'period':str(idx),'actual':round(float(row['Actual']),2) if 'Actual' in row else None,'estimate':round(float(row['Estimate']),2) if 'Estimate' in row else None})
            except: pass
        return jsonify(result)
    except Exception as e:
        return jsonify([])

@app.route('/api/revenue')
def revenue():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        result = []
        for attr in ['quarterly_income_stmt','quarterly_financials']:
            try:
                fin = getattr(t, attr)
                if fin is None or fin.empty: continue
                rev_row = next((fin.loc[l] for l in ['Total Revenue','Revenue'] if l in fin.index), None)
                ni_row  = next((fin.loc[l] for l in ['Net Income','Net Income Common Stockholders'] if l in fin.index), None)
                cols = list(reversed(list(fin.columns[:8])))
                for col in cols:
                    result.append({
                        'date': str(col.date()) if hasattr(col,'date') else str(col)[:10],
                        'revenue': float(rev_row[col]) if rev_row is not None and col in rev_row.index and rev_row[col]==rev_row[col] else 0,
                        'netIncome': float(ni_row[col]) if ni_row is not None and col in ni_row.index and ni_row[col]==ni_row[col] else 0,
                    })
                if result: break
            except: continue
        return jsonify(result)
    except Exception as e:
        return jsonify([])

@app.route('/api/recommendations')
def recommendations():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        rec = t.recommendations
        if rec is None or rec.empty: return jsonify({})
        latest = rec.iloc[-1]
        return jsonify({'strongBuy':int(latest.get('strongBuy',0)),'buy':int(latest.get('buy',0)),'hold':int(latest.get('hold',0)),'sell':int(latest.get('sell',0)),'strongSell':int(latest.get('strongSell',0))})
    except:
        return jsonify({})

@app.route('/api/analysts')
def analysts():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        upgrades = []
        try:
            ud = t.upgrades_downgrades
            if ud is not None and not ud.empty:
                for _, row in ud.head(25).reset_index().iterrows():
                    upgrades.append({'firm':str(row.get('Firm','')),'action':str(row.get('Action','')),'toGrade':str(row.get('ToGrade','')),'fromGrade':str(row.get('FromGrade','')),'date':str(row.get('GradeDate',''))[:10]})
        except: pass
        targets = {}
        try:
            at = t.analyst_price_targets
            if at: targets = {'low':at.get('low'),'high':at.get('high'),'mean':at.get('mean'),'median':at.get('median'),'current':at.get('current')}
        except: pass
        return jsonify({'upgrades':upgrades,'targets':targets})
    except Exception as e:
        return jsonify({'upgrades':[],'targets':{}})

@app.route('/api/news')
def news():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        result = []
        for n in (t.news or [])[:20]:
            ct = n.get('content',{}) or {}
            result.append({'title':ct.get('title','') or n.get('title',''),'url':(ct.get('canonicalUrl',{}) or {}).get('url','') or n.get('link',''),'source':(ct.get('provider',{}) or {}).get('displayName','') or n.get('publisher',''),'time':ct.get('pubDate','') or n.get('providerPublishTime',0)})
        return jsonify(result)
    except:
        return jsonify([])

@app.route('/api/market')
def market():
    result = {}
    for sym in request.args.get('symbols','SPY,QQQ,BTC-USD').split(','):
        try:
            i = yf.Ticker(sym).info
            price = i.get('currentPrice') or i.get('regularMarketPrice',0)
            prev  = i.get('previousClose') or i.get('regularMarketPreviousClose',0)
            result[sym] = {'price':price,'change':round((price-prev)/prev*100,2) if prev else 0}
        except:
            result[sym] = {'price':0,'change':0}
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',3000)))
