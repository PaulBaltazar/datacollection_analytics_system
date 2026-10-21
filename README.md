# Student Grades Analytics — starter (demo only)

This is a development starter for the analytics/results half of the project. It does NOT yet connect to the partner's MySQL or JWT authentication. Do not deploy publicly in demo mode.

## Quick start (PowerShell)
1. Copy `.env.example` to `.env`, and replace the password with a long random password containing letters and digits.
2. `docker compose up --build -d`
3. `docker compose ps` (wait until all containers are healthy)
4. `docker compose exec analytics-service python -c "import urllib.request; print(urllib.request.urlopen(urllib.request.Request('http://localhost:5002/refresh', method='POST')).read().decode())"`
5. Open `http://localhost:3000`
6. `docker compose logs --tail=50 analytics-service show-results`
7. `docker compose down` (preserves MongoDB data; avoid `down -v` unless intentionally resetting).

## Integration checklist
- Replace DEMO_GRADES in analytics-service/app.py with a read-only MySQL query grouped by user_id/course_name.
- Set DEMO_MODE=false; remove demo-only endpoint access; use a protected internal job or authenticated refresh endpoint.
- Integrate auth-service JWT verification in show-results/server.js, identify user from verified token, filter MongoDB by that ID. Never trust user_id supplied by the browser.
- Configure credentials with Docker secrets or environment injection; don't commit .env.
- Add a least-privileged MongoDB application account (starter uses root for simplicity only).
- Implement resource limits, performance tests, security scans, and CI/CD before submission.
