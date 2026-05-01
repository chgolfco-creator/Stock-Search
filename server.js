const express = require('express');
const fetch = require('node-fetch');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// TEST ROUTE - visit /test in your browser to see raw Yahoo response
app.get('/test', async (req, res) => {
  const url = 'https://query1.finance.yahoo.com/v8/finance/chart/NVDA?interval=1d&range=5d';
  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.5',
      }
    });
    const text = await response.text();
    res.send(`STATUS: ${response.status}<br><br><pre>${text.slice(0, 2000)}</pre>`);
  } catch (err) {
    res.send('ERROR: ' + err.message);
  }
});

app.get('/api/yf', async (req, res) => {
  const url = req.query.url;
  if (!url || !url.startsWith('https://query1.finance.yahoo.com')) {
    return res.status(400).json({ error: 'Invalid URL' });
  }
  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.5',
      }
    });
    const data = await response.json();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
