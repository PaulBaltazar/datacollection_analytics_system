# Load test and performance improvements

Three runs of the same test, then compare:

| Run | What's different | Why |
| --- | --- | --- |
| A. Baseline | Original system | Starting point |
| B. + more workers | auth-service and enter-data run 4 Gunicorn workers instead of 1 | Every request is checked by auth-service; with 1 worker, requests queue up behind each other |
| C. + per-user refresh | Reload results recalculates only the logged-in user, not every user | The original refresh reads every user's grades and rewrites every user's results on each reload |

All commands are PowerShell, run from the repo folder, with the system running (`docker compose ps` all healthy).

## One-time setup

1. Create the load test account (pick any password with 8+ characters and remember it):
   ```
   docker compose exec auth-service flask --app app create-user loadtest
   ```
2. Add realistic data: 200 extra students with 100 grades each.
   ```
   Get-Content loadtest\seed.sql | docker compose exec -T mysql sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'
   ```
   It prints `total_users` and `total_grades` at the end (about 201+ and 20,000+).
3. Find the Compose network name (the one ending in `_backend`):
   ```
   docker network ls
   ```
   Below it's assumed to be `datacollection_analytics_system_backend`. Change it if yours is different.

## Running one test

Replace `YOUR_PASSWORD` with the loadtest account's password and `RUN` with `A`, `B` or `C`:

```
docker run --rm --network datacollection_analytics_system_backend -v "${PWD}/loadtest:/mnt/locust" -e LOAD_USER=loadtest -e LOAD_PASSWORD=YOUR_PASSWORD locustio/locust -f /mnt/locust/locustfile.py --headless -u 30 -r 5 -t 2m --csv /mnt/locust/RUN
```

That's 30 simulated students, added 5 per second, for 2 minutes. Use exactly the same command for every run.

**While it runs**, in a second PowerShell window, run this 2-3 times about 30 seconds apart and screenshot it:
```
docker stats --no-stream
```

**Results** are in `loadtest\RUN_stats.csv`. Open it in Excel. For each run, record from these rows:
- `Aggregated` row: **Requests/s**, **Failure Count**, **Average Response Time**, **95%**
- `reload results` row: **Average Response Time** and **95%** (this is where improvement C shows)
- From `docker stats`: CPU % and memory for auth-service, enter-data, analytics-service and mysql

Also screenshot the summary table Locust prints at the end of each run.

## The three runs

**Run A - baseline.** Make sure `.env` has `GUNICORN_WORKERS=1` (or no such line). Run the test with `RUN` = `A`.

**Run B - more workers.** In `.env` set `GUNICORN_WORKERS=4`, then:
```
docker compose up -d
```
Wait until healthy, then run the test with `RUN` = `B`.

**Run C - per-user refresh.** Apply the code change (`02-per-user-refresh.patch`, see the kit instructions), rebuild, and run the test with `RUN` = `C`:
```
docker compose up -d --build
```

Note: each run adds more grades for the `loadtest` user, so later runs work with slightly more data. That makes the improvements look slightly smaller than they really are, not bigger.

## Clean up afterwards

Removes the 200 fake students and the load test grades (your real accounts and grades stay):
```
Get-Content loadtest\cleanup.sql | docker compose exec -T mysql sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'
```
Keep `GUNICORN_WORKERS=4` and the per-user refresh change - they're real improvements.

## What to write in the report

- **Method:** Locust, 30 users, ramp 5/s, 2 minutes, run inside the Compose network, against a database of 200 students and 20,000 grades. Each user saves grades (75%) and reloads results (25%).
- **Results table:** runs A, B, C with requests/s, failures, average and 95th percentile response time, and CPU/memory.
- **Improvement 1 (workers):** Gunicorn's default is 1 synchronous worker, which handles one request at a time. Every save and every reload also calls auth-service to verify the token, so auth-service was a queue. 4 workers let requests be handled in parallel.
- **Improvement 2 (per-user refresh):** before, every reload recalculated and rewrote results for all ~200 users, so the cost grew with the size of the class. Now it only reads the logged-in user's grades (using the existing `idx_grades_user_course` index) and writes one document.
- Only write numbers you actually measured. If an improvement made little difference, say so and explain why - that's still a valid finding.
