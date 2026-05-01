const express = require('express');
const fetch = require('node-fetch');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const FINNHUB_KEY = process.env.FINNHUB_KEY || 'd7q60npr01qosaaqosfgd7q60npr01qosaaqosg0';
const AV_KEY = process.env.AV_KEY || 'XKDZ6IIGKBZXECYM';

app.use((req, res, next) => { res.set('Cache-Control','no-store'); next(); });

app.get('/', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));

app.get('/api/fh', async (req, res) => {
  const endpoint = req.query.endpoint;
  if (!endpoint) return res.status(400).json({ error: 'No endpoint' });
  const sep = endpoint.includes('?') ? '&' : '?';
  const url = `https://finnhub.io/api/v1${endpoint}${sep}token=${FINNHUB_KEY}`;
  try {
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
    res.json(await r.json());
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/chart', async (req, res) => {
  const sym = (req.query.symbol || '').toUpperCase();
  const days = parseInt(req.query.days) || 365;
  if (!sym) return res.status(400).json({ error: 'No symbol' });
  const outputSize = days <= 100 ? 'compact' : 'full';
  const url = `https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=${sym}&outputsize=${outputSize}&apikey=${AV_KEY}`;
  try {
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
    const data = await r.json();
    const series = data['Time Series (Daily)'];
    if (!series) return res.json({ dates: [], closes: [] });
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const dates = [], closes = [];
    const entries = Object.entries(series).sort((a,b) => a[0].localeCompare(b[0]));
    for (const [date, values] of entries) {
      if (new Date(date) >= cutoff) {
        dates.push(date);
        closes.push(parseFloat(values['4. close']));
      }
    }
    res.json({ dates, closes });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/revenue', async (req, res) => {
  const sym = req.query.symbol;
  if (!sym) return res.status(400).json({ error: 'No symbol' });
  try {
    const url = `https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol=${sym}&apikey=${AV_KEY}`;
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
    const data = await r.json();
    const reports = (data.quarterlyReports || data.annualReports || []).slice(0, 8).reverse();
    res.json(reports.map(q => ({
      date: q.fiscalDateEnding,
      revenue: parseInt(q.totalRevenue) || 0,
      netIncome: parseInt(q.netIncome) || 0
    })));
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/revenue-debug', async (req, res) => {
  const sym = req.query.symbol || 'AAPL';
  const url = `https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol=${sym}&apikey=${AV_KEY}`;
  try {
    const r = await fetch(url);
    res.send('<pre>'+(await r.text()).slice(0,3000)+'</pre>');
  } catch(e) { res.send('Error: '+e.message); }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
