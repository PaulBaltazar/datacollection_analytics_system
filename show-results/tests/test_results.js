const {
  test,
  before,
  after,
  beforeEach,
  afterEach,
  mock
} = require('node:test');

const assert = require('node:assert/strict');
const http = require('node:http');

// Dummy configuration: tests do not connect to these services.
process.env.MONGO_URI = 'mongodb://localhost:27017';
process.env.MONGO_DB = 'test_student_analytics';
process.env.AUTH_URL = 'http://auth-service:5000';
process.env.ANALYTICS_URL = 'http://analytics-service:5002';

const { app, mongo } = require('../server');

let server;
let port;
let fetchMock;
let findOneMock;

// Send a real HTTP request to the Express app.
// Use http rather than fetch because fetch is mocked for upstream services.
function post(path, body, token) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify(body || {});

    const headers = {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload)
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const request = http.request({
      hostname: '127.0.0.1',
      port,
      path,
      method: 'POST',
      headers
    }, response => {
      let text = '';

      response.setEncoding('utf8');
      response.on('data', chunk => {
        text += chunk;
      });
      response.on('end', () => {
        try {
          resolve({
            status: response.statusCode,
            body: JSON.parse(text)
          });
        } catch (error) {
          reject(error);
        }
      });
    });

    request.on('error', reject);
    request.end(payload);
  });
}

function reply(status, data) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => data,
    text: async () => JSON.stringify(data)
  };
}

before(async () => {
  await new Promise(resolve => {
    server = app.listen(0, '127.0.0.1', resolve);
  });

  port = server.address().port;
});

after(async () => {
  await new Promise((resolve, reject) => {
    server.close(error => error ? reject(error) : resolve());
  });
});

beforeEach(() => {
  // Default: token belongs to user 1 and refresh succeeds.
  fetchMock = mock.method(globalThis, 'fetch', async url => {
    if (url.endsWith('/auth/verify')) {
      return reply(200, { user_id: 1 });
    }

    if (url.endsWith('/refresh')) {
      return reply(200, { message: 'Analytics refreshed' });
    }

    throw new Error(`Unexpected upstream request: ${url}`);
  });

  findOneMock = mock.fn(async () => ({
    user_id: 1,
    username: 'student1',
    grades: [
      { grade_id: 1, course_name: 'Math', grade: 80 }
    ],
    summary: {
      count: 1,
      minimum: 80,
      maximum: 80,
      average: 80
    }
  }));

  mock.method(mongo, 'db', () => ({
    collection: () => ({
      findOne: findOneMock
    })
  }));
});

afterEach(() => {
  mock.restoreAll();
});

test('successful login returns a token', async () => {
  fetchMock.mock.mockImplementation(async () =>
    reply(200, {
      access_token: 'test-token',
      token_type: 'Bearer',
      expires_in: 900
    })
  );

  const response = await post('/api/login', {
    username: 'student1',
    password: 'test-password'
  });

  assert.equal(response.status, 200);
  assert.equal(response.body.access_token, 'test-token');

  const [url, options] = fetchMock.mock.calls[0].arguments;
  assert.equal(url, 'http://auth-service:5000/auth/login');
  assert.deepEqual(JSON.parse(options.body), {
    username: 'student1',
    password: 'test-password'
  });
});

test('incorrect login is rejected', async () => {
  fetchMock.mock.mockImplementation(async () =>
    reply(401, { error: 'Invalid username or password' })
  );

  const response = await post('/api/login', {
    username: 'student1',
    password: 'wrong-password'
  });

  assert.equal(response.status, 401);
  assert.equal(response.body.access_token, undefined);
});

test('missing token prevents access', async () => {
  const response = await post('/api/results/refresh');

  assert.equal(response.status, 401);
  assert.equal(fetchMock.mock.callCount(), 0);
  assert.equal(findOneMock.mock.callCount(), 0);
});

test('invalid token prevents refresh and database access', async () => {
  fetchMock.mock.mockImplementation(async () =>
    reply(422, { error: 'Invalid token' })
  );

  const response = await post(
    '/api/results/refresh', {}, 'bad-token'
  );

  assert.equal(response.status, 401);
  assert.equal(fetchMock.mock.callCount(), 1);
  assert.equal(findOneMock.mock.callCount(), 0);
});

test('results use verified user ID, ignoring browser user_id', async () => {
  const response = await post(
    '/api/results/refresh',
    { user_id: 999 },
    'test-token'
  );

  assert.equal(response.status, 200);
  assert.equal(response.body.username, 'student1');

  const [filter, options] = findOneMock.mock.calls[0].arguments;
  assert.deepEqual(filter, { user_id: 1 });
  assert.deepEqual(options, { projection: { _id: 0 } });

  const [, verificationOptions] =
    fetchMock.mock.calls[0].arguments;

  assert.equal(
    verificationOptions.headers.Authorization,
    'Bearer test-token'
  );
});

test('a second user receives a query for their own ID', async () => {
  fetchMock.mock.mockImplementation(async url =>
    url.endsWith('/auth/verify')
      ? reply(200, { user_id: 2 })
      : reply(200, { message: 'Refreshed' })
  );

  findOneMock.mock.mockImplementation(async () => ({
    user_id: 2,
    username: 'student2',
    grades: [],
    summary: {
      count: 0, minimum: null, maximum: null, average: null
    }
  }));

  const response = await post(
    '/api/results/refresh', {}, 'user-two-token'
  );

  assert.equal(response.status, 200);
  assert.equal(response.body.user_id, 2);
  assert.deepEqual(
    findOneMock.mock.calls[0].arguments[0],
    { user_id: 2 }
  );
});

test('authentication outage returns 503 without reading data', async () => {
  fetchMock.mock.mockImplementation(async () => {
    throw new Error('Connection failed');
  });

  const response = await post(
    '/api/results/refresh', {}, 'test-token'
  );

  assert.equal(response.status, 503);
  assert.equal(fetchMock.mock.callCount(), 1);
  assert.equal(findOneMock.mock.callCount(), 0);
});

test('analytics failure prevents reading stale results', async () => {
  fetchMock.mock.mockImplementation(async url =>
    url.endsWith('/auth/verify')
      ? reply(200, { user_id: 1 })
      : reply(503, { error: 'Database unavailable' })
  );

  const response = await post(
    '/api/results/refresh', {}, 'test-token'
  );

  assert.equal(response.status, 503);
  assert.equal(findOneMock.mock.callCount(), 0);
});

test('refresh finishes before results are queried', async () => {
  const events = [];

  fetchMock.mock.mockImplementation(async url => {
    if (url.endsWith('/auth/verify')) {
      return reply(200, { user_id: 1 });
    }

    return {
      ok: true,
      status: 200,
      text: async () => {
        await new Promise(resolve => setImmediate(resolve));
        events.push('refresh finished');
        return '{}';
      }
    };
  });

  findOneMock.mock.mockImplementation(async () => {
    events.push('database queried');
    return null;
  });

  const response = await post(
    '/api/results/refresh', {}, 'test-token'
  );

  assert.equal(response.status, 200);
  assert.deepEqual(events, [
    'refresh finished',
    'database queried'
  ]);
});

test('MongoDB failure returns 503', async () => {
  findOneMock.mock.mockImplementation(async () => {
    throw new Error('Database unavailable');
  });

  const response = await post(
    '/api/results/refresh', {}, 'test-token'
  );

  assert.equal(response.status, 503);
  assert.equal(response.body.error, 'Database unavailable');
});

test('missing dashboard returns an empty result', async () => {
  findOneMock.mock.mockImplementation(async () => null);

  const response = await post(
    '/api/results/refresh', {}, 'test-token'
  );

  assert.equal(response.status, 200);
  assert.deepEqual(response.body.grades, []);
  assert.equal(response.body.summary.count, 0);
  assert.equal(response.body.summary.average, null);
});