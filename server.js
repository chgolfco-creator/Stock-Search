const express = require('express');
const fetch = require('node-fetch');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const FINNHUB_KEY = process.env.FINNHUB_KEY || 'd7q60npr01qosaaqosfgd7q60npr01qosaaqosg0';

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

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

// Dedicated revenue endpoint using Alpha Vantage (free, no IP blocking)
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
      netIncome: parseInt(q.netIncome) || 0,
      grossProfit: parseInt(q.grossProfit) || 0
    }));
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
