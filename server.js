const http = require('http');
const path = require('path');
const fs = require('fs');
const { createClient } = require('@supabase/supabase-js');

const PORT = process.env.PORT || 3003;
const SUPABASE_URL = process.env.SUPABASE_URL || 'https://ansiaiuaygcfztabtknl.supabase.co';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFuc2lhaXVheWdjZnp0YWJ0a25sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMwNjg2NjksImV4cCI6MjA3ODY0NDY2OX0.-a4CakCH4DhHGOG1vMo9nVdtW0ux252QqXRi-7CA_gA';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const MIME_TYPES = {
  '.html': 'text/html',
  '.css':  'text/css',
  '.js':   'application/javascript',
  '.json': 'application/json',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
  '.woff': 'font/woff',
  '.woff2':'font/woff2',
  '.ttf':  'font/ttf',
};

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk.toString(); });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch {
        resolve({});
      }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const pathname = url.pathname;

  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // --- Health check ---
  if (req.method === 'GET' && pathname === '/api/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', site: 'rhythmclaw', supabase: true, timestamp: new Date().toISOString() }));
    return;
  }

  // --- GET /api/tracks ---
  if (req.method === 'GET' && pathname === '/api/tracks') {
    const { data, error } = await supabase
      .from('tracks')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(100);
    res.writeHead(error ? 500 : 200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(error ? { error: error.message } : data));
    return;
  }

  // --- POST /api/mix-session ---
  if (req.method === 'POST' && pathname === '/api/mix-session') {
    const body = await parseBody(req);
    const { error } = await supabase.from('mix_sessions').insert({
      ...body,
      started_at: new Date().toISOString()
    });
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: !error, error: error ? error.message : null }));
    return;
  }

  // --- POST /api/contact ---
  if (req.method === 'POST' && pathname === '/api/contact') {
    const body = await parseBody(req);
    const { name, email, message } = body;
    if (!email || !message) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Email and message are required' }));
      return;
    }
    const { error } = await supabase.from('contacts').insert({
      site_name: 'rhythmclaw',
      name: name || '',
      email,
      message,
      created_at: new Date().toISOString()
    });
    if (error) console.error('[rhythmclaw] contact error:', error.message);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: !error, message: error ? error.message : 'Message received successfully' }));
    return;
  }

  // --- POST /api/newsletter ---
  if (req.method === 'POST' && pathname === '/api/newsletter') {
    const body = await parseBody(req);
    const { email } = body;
    if (!email) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Email is required' }));
      return;
    }
    const { error } = await supabase.from('newsletter_subscribers').insert({
      site_name: 'rhythmclaw',
      email,
      subscribed_at: new Date().toISOString(),
      is_active: true
    });
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, message: 'Successfully subscribed' }));
    return;
  }

  // --- POST /api/page-view ---
  if (req.method === 'POST' && (pathname === '/api/page-view' || pathname === '/api/analytics')) {
    const body = await parseBody(req);
    await supabase.from('page_views').insert({
      site_name: 'rhythmclaw',
      page_path: body.page || body.page_path || '/',
      referrer: body.referrer || '',
      user_agent: body.userAgent || req.headers['user-agent'] || '',
      session_id: body.session_id || '',
      created_at: new Date().toISOString()
    });
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  // --- Static file serving ---
  let filePath = pathname === '/' ? '/index.html' : pathname;
  filePath = path.join(__dirname, filePath);

  // Security: prevent path traversal
  if (!filePath.startsWith(__dirname)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  const ext = path.extname(filePath);
  const mimeType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, data) => {
    if (err) {
      // SPA fallback: serve index.html for unknown paths
      fs.readFile(path.join(__dirname, 'index.html'), (err2, indexData) => {
        if (err2) {
          res.writeHead(404);
          res.end('Not found');
        } else {
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(indexData);
        }
      });
    } else {
      res.writeHead(200, { 'Content-Type': mimeType });
      res.end(data);
    }
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[rhythmclaw] Server running on http://localhost:${PORT}`);
  console.log(`[rhythmclaw] Supabase: ${SUPABASE_URL}`);
});
