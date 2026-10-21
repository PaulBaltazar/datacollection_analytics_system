
async function load() {
  const target = document.getElementById('results');
  const controller = new AbortController();

  // Stop waiting after 10 seconds
  const timeout = setTimeout(() => controller.abort(), 10000);

  target.textContent = 'Loading...';

  try {
    const response = await fetch('/api/results', {
      signal: controller.signal
    });

    if (!response.ok) {
      throw new Error('Results unavailable');
    }

    const data = await response.json();

    if (!data.length) {
      target.textContent = 'No results yet. Run the analytics refresh command.';
      return;
    }

    target.replaceChildren();

    for (const row of data) {
      const card = document.createElement('section');
      card.className = 'card';

      const heading = document.createElement('h2');
      heading.textContent = row.course_name;

      const info = document.createElement('p');
      info.textContent =
        `Count: ${row.count} | Min: ${row.minimum}% | Max: ${row.maximum}% | Average: ${row.average}%`;

      card.append(heading, info);
      target.append(card);
    }

  } catch (err) {
    target.textContent =
      'Results temporarily unavailable. Please try again.';

  } finally {
    clearTimeout(timeout);
  }
}

document.getElementById('reload').addEventListener('click', load);

load();
