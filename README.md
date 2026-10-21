# Data Collection and Analytics System

## Project Overview

This project is for **ACIT 3495 – Advanced IT Infrastructure at BCIT**.

Our project is a student grades system that uses Docker containers to collect, calculate, store, and display student grades.

The system uses Python, JavaScript, MySQL, and MongoDB.

**Current progress:** The Analytics Service, MongoDB, and Show Results web app are working with sample data. MySQL and authentication will be added soon.

## Technologies Used

- **Docker and Docker Compose** – Run and manage containers.
- **Python and Flask** – Calculate student grade statistics.
- **MongoDB** – Store calculated results.
- **Node.js and Express** – Retrieve results for the dashboard.
- **HTML, CSS, JavaScript** – Display results on a web page.
- **Pytest** – Test Python calculations.
- **MySQL** – Store student grades.
- **JWT** – User authentication.

## How the System Works

The completed project will have four main services:

1. **Authentication Service** – Handles user login.
2. **Enter Data Service** – Allows users to enter grades into MySQL.
3. **Analytics Service** – Calculates the average, minimum, maximum, and number of grades.
4. **Show Results Service** – Displays the calculated statistics on a web dashboard.

Currently, the Analytics Service uses sample grades instead of MySQL.

## How to Run the Project

**1. Set up environment variables**

Copy `.env.example` to `.env` and enter your own MongoDB username and password.

```powershell
Copy-Item .env.example .env
```

Do not upload your `.env` file to GitHub.

**2. Start the Docker containers**

```powershell
docker compose up --build -d
```

**3. Check the containers**

```powershell
docker compose ps
```

Wait until all three containers are healthy.

**4. Generate sample statistics**

```powershell
docker compose exec analytics-service python -c "import urllib.request; print(urllib.request.urlopen(urllib.request.Request('http://localhost:5002/refresh', method='POST')).read().decode())"
```

**5. Open the dashboard**

Open http://localhost:3000 in your browser.

**6. Stop the containers**

```powershell
docker compose down
```

This keeps the MongoDB data saved in its Docker volume.

## Testing Completed

We tested the following:

- **Python unit test:** Passed. Verified grade calculations.
- **MongoDB persistence:** Passed. Data remained after restarting containers.
- **MongoDB failure test:** Passed. The dashboard displayed an error when MongoDB was unavailable.
- **MongoDB recovery:** Passed. The dashboard displayed results again after MongoDB restarted.

## Remaining Tasks

- Connect the Analytics Service to MySQL.
- Integrate the Enter Data and Authentication services.
- Add JWT authentication to the dashboard.
- Improve database security.
- Add resource limits and more tests.
- Set up a CI/CD pipeline.
- Test the complete system.

## Notes

The current project is still under development and only used for local testing only. Authentication and additional security features must still be completed.