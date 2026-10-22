let token = null;

const loginSection = document.getElementById('loginSection');
const dashboard = document.getElementById('dashboard');
const message = document.getElementById('message');
const results = document.getElementById('results');
const reloadButton = document.getElementById('reload');

function logout() {
  token = null;
  loginSection.hidden = false;
  dashboard.hidden = true;
  results.replaceChildren();
}

function displayResults(data) {
  results.replaceChildren();

  if (data.grades.length === 0) {
    results.textContent = 'No grades found for your account.';
    return;
  }

  const formatGrade = value => Number(value).toFixed(2);

  const table = document.createElement('table');
  const head = document.createElement('thead');
  const headerRow = document.createElement('tr');

  for (const title of ['Username', 'Course', 'Grade']) {
    const th = document.createElement('th');
    th.textContent = title;
    headerRow.appendChild(th);
  }

  head.appendChild(headerRow);
  table.appendChild(head);

  const body = document.createElement('tbody');

  for (const grade of data.grades) {
    const row = document.createElement('tr');

    for (const value of [
      data.username,
      grade.course_name,
      formatGrade(grade.grade)
    ]) {
      const td = document.createElement('td');
      td.textContent = value;
      row.appendChild(td);
    }

    body.appendChild(row);
  }

  table.appendChild(body);
  results.appendChild(table);

  const summary = document.createElement('section');
  summary.className = 'card';

  const heading = document.createElement('h2');
  heading.textContent = 'Overall grade summary';
  summary.appendChild(heading);

  const explanation = document.createElement('p');
  explanation.textContent =
    `Across your ${data.summary.count} submitted grades in all courses.`;
  summary.appendChild(explanation);

  for (const [label, value] of [
    ['Minimum', data.summary.minimum],
    ['Maximum', data.summary.maximum],
    ['Average', data.summary.average]
  ]) {
    const line = document.createElement('p');
    line.textContent = `${label}: ${formatGrade(value)}`;
    summary.appendChild(line);
  }
  results.appendChild(summary);
}

async function reloadResults() {
  reloadButton.disabled = true;
  message.textContent = 'Refreshing analytics...';

  try {
    const response = await fetch('/api/results/refresh', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    });

    const data = await response.json();

    if (response.status === 401) {
      logout();
    }

    if (!response.ok) {
      message.textContent = data.error || 'Unable to load results';
      return;
    }

    displayResults(data);
    message.textContent = 'Results updated from your saved grades.';
  } catch {
    message.textContent = 'Unable to connect. Please try again.';
  } finally {
    reloadButton.disabled = false;
  }
}

document.getElementById('loginForm').addEventListener(
  'submit', async event => {
    event.preventDefault();
    message.textContent = '';

    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: document.getElementById('username').value,
          password: document.getElementById('password').value
        })
      });

      const data = await response.json();

      if (!response.ok) {
        message.textContent = data.error || 'Login failed';
        return;
      }

      token = data.access_token;
      document.getElementById('loginForm').reset();
      loginSection.hidden = true;
      dashboard.hidden = false;

      await reloadResults();
    } catch {
      message.textContent = 'Unable to connect. Please try again.';
    }
  }
);

reloadButton.addEventListener('click', reloadResults);

document.getElementById('logout').addEventListener('click', () => {
  logout();
  message.textContent = 'Logged out';
});