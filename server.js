const express = require('express');
const path = require('path');
const cors = require('cors');

const PORT = process.env.PORT || 3003;
const app = express();

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// --- API Routes ---

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', site: 'rhythmclaw', timestamp: new Date().toISOString() });
});

app.post('/api/contact', (req, res) => {
  const { name, email, message } = req.body;
  if (!email || !message) return res.status(400).json({ error: 'Email and message required' });
  console.log(`[Contact] ${email}: ${message}`);
  res.json({ success: true, message: 'Message received' });
});

app.post('/api/newsletter', (req, res) => {
  const { email } = req.body;
  if (!email) return res.status(400).json({ error: 'Email required' });
  console.log(`[Newsletter] ${email}`);
  res.json({ success: true, message: 'Subscribed' });
});

app.post('/api/analytics', (req, res) => {
  res.json({ success: true });
});

// --- Static files ---
app.use(express.static(__dirname));
app.get('/{*splat}', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));

app.listen(PORT, '0.0.0.0', () => {
  console.log(`RhythmClaw server on http://localhost:${PORT}`);
});
