# Data Collection and Analytics System

## Project Overview

This project is for **ACIT 3495 – Advanced IT Infrastructure at BCIT**.

Our project is a student grades system that uses Docker containers to collect, calculate, store, and display student grades.

## Technologies Used

- **Docker and Docker Compose** – Run and manage containers.
- **Python and Flask** – Manage student grade collection and statistics.
- **MongoDB** – Store calculated results.
- **Node.js and Express** – Retrieve results for the dashboard.
- **HTML, CSS, JavaScript** – For the web pages.
- **Pytest** – Test Python calculations.
- **MySQL** – Store student grades.
- **JWT** – User authentication.

## How the System Works

The project has four main services:

1. **Authentication Service** – Handles user login.
2. **Enter Data Service** – Allows users to enter grades into MySQL.
3. **Analytics Service** – Calculates the average, minimum, maximum, and number of grades.
4. **Show Results Service** – Displays the calculated statistics on a web dashboard.

## How to Run the Project

**1. Set up environment variables**

Copy `.env.example` to a `.env` file and enter your own usernames and passwords:

```powershell
Copy-Item .env.example .env
```

Then, generate a JWT secret with Python and put it in the same `.env` file:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**2. Start the Docker containers**

```bash
docker compose up --build -d
```

**3. Check the containers**

```bash
docker compose ps
```

Wait until all containers are healthy.

**4. Create users**

Accounts are created through an administrator CLI command. Public registration is outside this implementation's scope.

```bash
docker compose exec auth-service flask --app app create-user choose_the_usernames
```

Enter and confirm a password of at least eight characters. The command stores a salted password hash in MySQL. Repeat with another username to create additional accounts.

**5. Enter some grades**

Open http://localhost:8080.

1. Log in using a created account.
2. Enter a course name.
3. Enter a grade between 0 and 100, with at most two decimal places.
4. Click **Save grade** and check the confirmation message.
5. Click **Log out** when finished.

Each submission creates a new grade row; it does not replace a previous grade for that course.

The browser keeps the access token in JavaScript memory. Refreshing the page clears it. Tokens expire after 15 minutes. 
Logout clears the browser's copy but does not revoke a token already issued.

**6. View the grades**

Open http://localhost:3000 in your browser.

1. Log in using a created account.
2. Click **Reload results** to see the latest grades.
3. Click **Log out** when finished.

The logged in user can only see their own grades. That is intended behavior for now. 

**7. Remove the containers**

```bash
docker compose down
```

This retains the database volumes. 
**Do not add `-v` unless you intend to delete the stored users and grades.**

## Running tests and healthchecks

Make sure all the containers are running first:

```bash
docker compose up --build -d
```

**Authentication service tests**

```bash
docker compose run --rm --no-deps -v "./auth-service/tests:/app/tests:ro" auth-service python -m pytest tests -v -p no:cacheprovider
```

**Authentication service healthcheck**

```bash
docker compose exec auth-service python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:5000/health').read().decode())"
```

**Enter data web app tests**

```bash
docker compose run --rm --no-deps -v "./enter-data/tests:/app/tests:ro" enter-data python -m pytest tests -v -p no:cacheprovider
```

**Enter data web app healthcheck**

```powershell
curl.exe -i http://localhost:8080/health
```

**Analytics service tests**

```bash
docker compose run --rm --no-deps -v "./analytics-service/tests:/app/tests:ro" analytics-service python -m pytest tests -v -p no:cacheprovider
```

**Analytics service healthcheck**

```bash
docker compose exec analytics-service python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5002/health', timeout=3).read().decode())"
```

**Show results web app tests**

```bash
docker compose run --rm --no-deps -v "./show-results/tests:/app/tests:ro" show-results node --test tests/test_results.js
```

**Show results web app healthcheck**

```powershell
curl.exe -i http://localhost:3000/health
```

## CI/CD pipeline

GitHub Actions automatically runs the pipeline when changes are pushed to **main**.

The pipeline:

1. Builds the four application images and runs their unit tests. (The database images are pulled from the Docker Hub)
2. Scans the images using Trivy, failing on fixable HIGH or CRITICAL vulnerabilities.
3. After all checks pass on main, builds and publishes AMD64 and ARM64 images to GitHub Container Registry (GHCR), tagged with latest and the commit SHA.

Scan reports are available under the run’s **Artifacts**, and published images appear under **Packages**.
