const express = require('express');
const fetch = require('node-fetch');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const FINNHUB_KEY = process.env.FINNHUB_KEY || 'd7q60npr01qosaaqosfgd7q60npr01qosaaqosg0';

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// Finnhub proxy (quote, profile, metrics, recommendations, earnings, news)
app.get('/api/fh', async (req, res) => {
  const endpoint = req.query.endpoint;
  if (!endpoint) return res.status(400).json({ error: 'No endpoint' });
  const sep = endpoint.includes('?') ? '&' : '?';
  const url = `https://finnhub.io/api/v1${endpoint}${sep}token=${FINNHUB_KEY}`;
  try {
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
    const data = await r.json();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Price chart via stooq (free, no key, no IP blocking)
app.get('/api/chart', async (req, res) => {
  const sym = (req.query.symbol || '').toUpperCase();
  const days = parseInt(req.query.days) || 365;
  if (!sym) return res.status(400).json({ error: 'No symbol' });

  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - days);
  const fmt = d => d.toISOString().split('T')[0].replace(/-/g,'');

  // stooq returns CSV: Date,Open,High,Low,Close,Volume
  const url = `https://stooq.com/q/d/l/?s=${sym.toLowerCase()}.us&d1=${fmt(from)}&d2=${fmt(to)}&i=d`;
  try {
    const r = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0' }
    });
    const text = await r.text();
    const lines = text.trim().split('\n');
    if (lines.length < 2) return res.json({ dates: [], closes: [] });

    const dates = [], closes = [];
    for (let i = 1; i < lines.length; i++) {
      const parts = lines[i].split(',');
      if (parts.length < 5) continue;
      dates.push(parts[0]);
      closes.push(parseFloat(parts[4]));
    }
    res.json({ dates, closes });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Revenue via Alpha Vantage
app.get('/api/revenue', async (req, res) => {
  const sym = req.query.symbol;
  if (!sym) return res.status(400).json({ error: 'No symbol' });
  try {
    const url = `https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol=${sym}&apikey=demo`;
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
    const data = await r.json();
    const reports = (data.quarterlyReports || []).slice(0, 8).reverse();
    const result = reports.map(q => ({
      date: q.fiscalDateEnding,
      revenue: parseInt(q.totalRevenue) || 0,
      netIncome: parseInt(q.netIncome) || 0
    }));
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
