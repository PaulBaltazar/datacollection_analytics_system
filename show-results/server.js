const express = require('express');
const { MongoClient } = require('mongodb');

const app = express();

const mongo = new MongoClient(process.env.MONGO_URI, {
  serverSelectionTimeoutMS: 4000,
  connectTimeoutMS: 4000,
  socketTimeoutMS: 4000
});

const dbName = process.env.MONGO_DB || 'student_analytics';
const authUrl = process.env.AUTH_URL;
const analyticsUrl = process.env.ANALYTICS_URL;

if (!authUrl || !analyticsUrl) {
  throw new Error('AUTH_URL and ANALYTICS_URL are required');
}

app.use(express.json({ limit: '16kb' }));
app.use('/api', (_req, res, next) => {
  res.set('Cache-Control', 'no-store');
  next();
});
app.use(express.static('public'));

// Forward login to Authentication.
app.post('/api/login', async (req, res) => {
  try {
    const response = await fetch(`${authUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: req.body?.username,
        password: req.body?.password
      }),
      signal: AbortSignal.timeout(5000)
    });

    if (![200, 400, 401].includes(response.status)) {
      return res.status(503).json({
        error: 'Authentication service unavailable'
      });
    }

    const data = await response.json();
    res.status(response.status).json(data);
  } catch {
    res.status(503).json({
      error: 'Authentication service unavailable'
    });
  }
});

// Validate the token before accessing results.
async function requireLogin(req, res, next) {
  const authorization = req.get('Authorization') || '';

  if (!authorization.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Login required' });
  }

  try {
    const response = await fetch(`${authUrl}/auth/verify`, {
      method: 'POST',
      headers: { Authorization: authorization },
      signal: AbortSignal.timeout(5000)
    });

    if ([401, 422].includes(response.status)) {
      return res.status(401).json({
        error: 'Invalid or expired token. Log in again.'
      });
    }

    if (!response.ok) {
      return res.status(503).json({
        error: 'Authentication service unavailable'
      });
    }

    const data = await response.json();

    if (!Number.isSafeInteger(data.user_id) || data.user_id <= 0) {
      return res.status(503).json({
        error: 'Invalid authentication response'
      });
    }

    req.userId = data.user_id;
    next();
  } catch {
    res.status(503).json({
      error: 'Authentication service unavailable'
    });
  }
}

// Refresh analytics, then return the authenticated user's results.
app.post('/api/results/refresh', requireLogin, async (req, res) => {
  try {
    const response = await fetch(`${analyticsUrl}/refresh`, {
      method: 'POST',
      signal: AbortSignal.timeout(30000)
    });

    if (!response.ok) {
      return res.status(503).json({
        error: 'Analytics refresh failed'
      });
    }

    // Wait until the response body has been received.
    await response.text();
  } catch {
    return res.status(503).json({
      error: 'Analytics service unavailable'
    });
  }

  try {
    const dashboard = await mongo.db(dbName)
      .collection('dashboards')
      .findOne(
        { user_id: req.userId },
        { projection: { _id: 0 } }
      );

    res.json(dashboard || {
      grades: [],
      summary: {
        count: 0,
        minimum: null,
        maximum: null,
        average: null
      }
    });
  } catch {
    res.status(503).json({ error: 'Database unavailable' });
  }
});

app.get('/health', async (_req, res) => {
  try {
    await mongo.db('admin').command({ ping: 1 });
    res.json({ status: 'ok' });
  } catch {
    res.status(503).json({ status: 'unhealthy' });
  }
});

// Start only when run directly: node server.js
if (require.main === module) {
  (async () => {
    await mongo.connect();

    app.listen(3000, '0.0.0.0', () => {
      console.log('Show Results listening on port 3000');
    });
  })().catch(err => {
    console.error('Startup failed:', err.name);
    process.exit(1);
  });
}

// Allow tests to import the app and replace database calls.
module.exports = { app, mongo };