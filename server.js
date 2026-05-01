const express = require('express');
const fetch = require('node-fetch');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const FINNHUB_KEY = process.env.FINNHUB_KEY || 'd7q60npr01qosaaqosfgd7q60npr01qosaaqosg0';

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// Generic Finnhub proxy
app.get('/api/fh', async (req, res) => {
  const endpoint = req.query.endpoint;
  if (!endpoint) return res.status(400).json({ error: 'No endpoint' });
  const sep = endpoint.includes('?') ? '&' : '?';
  const url = `https://finnhub.io/api/v1${endpoint}${sep}token=${FINNHUB_KEY}`;
  try {
    const r = await fetch(url, {
      headers: { 'Accept': 'application/json' }
    });
    const data = await r.json();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
