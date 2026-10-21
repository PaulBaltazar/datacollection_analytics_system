const express = require('express');
const { MongoClient } = require('mongodb');
const app = express();
const mongo = new MongoClient(process.env.MONGO_URI);
const dbName = process.env.MONGO_DB || 'student_analytics';
app.use(express.static('public'));
app.get('/health', async (_req, res) => {
  try { await mongo.db('admin').command({ ping: 1 }); res.json({ status: 'ok' }); }
  catch { res.status(503).json({ status: 'unhealthy' }); }
});
app.get('/api/results', async (_req, res) => {
  if (process.env.DEMO_MODE !== 'true') return res.status(503).json({ error: 'Authentication not configured' });
  try {
    const results = await mongo.db(dbName).collection('results')
      .find({ user_id: 1 }, { projection: { _id: 0 } }).sort({ course_name: 1 }).toArray();
    res.json(results);
  } catch { res.status(503).json({ error: 'Database unavailable' }); }
});
(async () => {
  await mongo.connect();
  app.listen(3000, '0.0.0.0', () => console.log('Show Results listening on port 3000'));
})().catch(err => { console.error('Startup failed:', err.message); process.exit(1); });
