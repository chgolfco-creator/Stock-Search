const express = require('express');
const fetch = require('node-fetch');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Serve the frontend
app.use(express.static(path.join(__dirname, 'public')));

// Proxy route — all Yahoo Finance calls go through here
app.get('/api/yf', async (req, res) => {
  const url = req.query.url;
  if (!url || !url.startsWith('https://query1.finance.yahoo.com')) {
    return res.status(400).json({ error: 'Invalid URL' });
  }
  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
      }
    });
    const data = await response.json();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));