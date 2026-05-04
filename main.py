\from flask import Flask, jsonify, send_file, request
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
            'revenueGrowth': info.get('revenueGrowth',None),
            'earningsGrowth': info.get('earningsGrowth',None),
            'epsForward': info.get('forwardEps',None),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart')
def chart():
    sym = request.args.get('symbol','').upper()
    days = int(request.args.get('days', 365))
    try:
        period_map = {
            30:    ('3mo',  '1d'),
            90:    ('6mo',  '1d'),
            180:   ('6mo',  '1d'),
            365:   ('1y',   '1d'),
            365*3: ('5y',   '1wk'),
            365*5: ('10y',  '1wk'),
        }
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
        result = []

        # Try earnings_history first (newer yfinance)
        try:
            eh = t.get_earnings_history()
            if eh is not None and not eh.empty:
                for _, row in eh.iterrows():
                    period = str(row.get('period','') or row.get('quarter',''))
                    actual = row.get('epsActual') or row.get('Actual')
                    estimate = row.get('epsEstimate') or row.get('Estimate')
                    result.append({
                        'period': period,
                        'actual': round(float(actual),2) if actual is not None else None,
                        'estimate': round(float(estimate),2) if estimate is not None else None,
                    })
        except:
            pass

        # Fallback: quarterly_earnings
        if not result:
            try:
                eq = t.quarterly_earnings
                if eq is not None and not eq.empty:
                    for idx, row in eq.iterrows():
                        actual = row.get('Actual') or row.get('epsActual')
                        estimate = row.get('Estimate') or row.get('epsEstimate')
                        result.append({
                            'period': str(idx),
                            'actual': round(float(actual),2) if actual is not None else None,
                            'estimate': round(float(estimate),2) if estimate is not None else None,
                        })
            except:
                pass

        # Fallback: earnings_dates
        if not result:
            try:
                ed = t.earnings_dates
                if ed is not None and not ed.empty:
                    ed = ed.dropna(subset=['EPS Estimate','Reported EPS'])
                    for idx, row in ed.iterrows():
                        result.append({
                            'period': str(idx.date()),
                            'actual': round(float(row['Reported EPS']),2),
                            'estimate': round(float(row['EPS Estimate']),2),
                        })
                    result = list(reversed(result))
            except:
                pass

        return jsonify(result)
    except Exception as e:
        print('Earnings error:', traceback.format_exc())
        return jsonify([])

@app.route('/api/revenue')
def revenue():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        result = []

        # Try quarterly_financials
        try:
            fin = t.quarterly_financials
            if fin is not None and not fin.empty:
                rev_row = None
                for label in ['Total Revenue','Revenue','TotalRevenue']:
                    if label in fin.index:
                        rev_row = fin.loc[label]
                        break
                ni_row = None
                for label in ['Net Income','NetIncome','Net Income Common Stockholders']:
                    if label in fin.index:
                        ni_row = fin.loc[label]
                        break
                cols = list(fin.columns[:8])
                cols.reverse()
                for col in cols:
                    rev = float(rev_row[col]) if rev_row is not None and col in rev_row.index and rev_row[col] == rev_row[col] else 0
                    ni  = float(ni_row[col])  if ni_row  is not None and col in ni_row.index  and ni_row[col]  == ni_row[col]  else 0
                    result.append({
                        'date': str(col.date()) if hasattr(col,'date') else str(col)[:10],
                        'revenue': rev,
                        'netIncome': ni
                    })
        except Exception as e:
            print('quarterly_financials error:', e)

        # Fallback: income_stmt
        if not result:
            try:
                fin = t.quarterly_income_stmt
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
                        rev = float(rev_row[col]) if rev_row is not None and col in rev_row.index and rev_row[col]==rev_row[col] else 0
                        ni  = float(ni_row[col])  if ni_row  is not None and col in ni_row.index  and ni_row[col]==ni_row[col]  else 0
                        result.append({
                            'date': str(col.date()) if hasattr(col,'date') else str(col)[:10],
                            'revenue': rev,
                            'netIncome': ni
                        })
            except Exception as e:
                print('income_stmt error:', e)

        return jsonify(result)
    except Exception as e:
        print('Revenue error:', traceback.format_exc())
        return jsonify([])

@app.route('/api/analysts')
def analysts():
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        result = []

        # Analyst price targets
        try:
            upgrades = t.upgrades_downgrades
            if upgrades is not None and not upgrades.empty:
                recent = upgrades.head(20).reset_index()
                for _, row in recent.iterrows():
                    result.append({
                        'firm': str(row.get('Firm','')),
                        'action': str(row.get('Action','')),
                        'toGrade': str(row.get('ToGrade','')),
                        'fromGrade': str(row.get('FromGrade','')),
                        'date': str(row.get('GradeDate','')[:10]) if row.get('GradeDate') else '',
                    })
        except Exception as e:
            print('upgrades error:', e)

        # Analyst price targets table
        targets = []
        try:
            at = t.analyst_price_targets
            if at is not None:
                targets = {
                    'low': at.get('low'),
                    'high': at.get('high'),
                    'mean': at.get('mean'),
                    'median': at.get('median'),
                    'current': at.get('current'),
                }
        except Exception as e:
            print('analyst_price_targets error:', e)

        return jsonify({'upgrades': result, 'targets': targets})
    except Exception as e:
        return jsonify({'upgrades': [], 'targets': {}})
    sym = request.args.get('symbol','').upper()
    try:
        t = yf.Ticker(sym)
        rec = t.recommendations
        if rec is None or rec.empty:
            return jsonify({})
        latest = rec.iloc[-1]
        return jsonify({
            'strongBuy':  int(latest.get('strongBuy',0)),
            'buy':        int(latest.get('buy',0)),
            'hold':       int(latest.get('hold',0)),
            'sell':       int(latest.get('sell',0)),
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
            ct = n.get('content',{})
            result.append({
                'title':  ct.get('title','') or n.get('title',''),
                'url':    (ct.get('canonicalUrl',{}) or {}).get('url','') or n.get('link',''),
                'source': (ct.get('provider',{}) or {}).get('displayName','') or n.get('publisher',''),
                'time':   ct.get('pubDate','') or n.get('providerPublishTime',0),
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

# Debug endpoint
@app.route('/api/debug')
def debug():
    sym = request.args.get('symbol','AAPL').upper()
    try:
        t = yf.Ticker(sym)
        fin = t.quarterly_financials
        inc = t.quarterly_income_stmt
        ed  = t.earnings_dates
        return jsonify({
            'fin_index': list(fin.index) if fin is not None and not fin.empty else [],
            'inc_index': list(inc.index) if inc is not None and not inc.empty else [],
            'ed_cols':   list(ed.columns) if ed is not None and not ed.empty else [],
            'ed_rows':   ed.shape[0] if ed is not None else 0,
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
