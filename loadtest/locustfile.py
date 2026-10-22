"""Load test for the Data Collection and Analytics System.

Each simulated student logs in once, then repeatedly:
  - saves a grade through Enter Data        (weight 3)
  - reloads their results in Show Results   (weight 1)

It runs inside the Compose network, so it talks to the services by name.
See loadtest/README.md for the exact commands.
"""
import os
import random

from locust import HttpUser, between, task
from locust.exception import StopUser

ENTER_DATA = os.environ.get("ENTER_DATA_URL", "http://enter-data:5000")
SHOW_RESULTS = os.environ.get("SHOW_RESULTS_URL", "http://show-results:3000")
USERNAME = os.environ["LOAD_USER"]
PASSWORD = os.environ["LOAD_PASSWORD"]
COURSES = ["Math", "Science", "English", "History", "Art"]


class Student(HttpUser):
    host = ENTER_DATA
    wait_time = between(0.5, 1.5)

    def on_start(self):
        with self.client.post(
            f"{ENTER_DATA}/login",
            json={"username": USERNAME, "password": PASSWORD},
            name="login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"login failed ({response.status_code}) - check LOAD_USER / LOAD_PASSWORD")
                raise StopUser()
            self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    @task(3)
    def save_grade(self):
        self.client.post(
            f"{ENTER_DATA}/api/grades",
            json={"course_name": random.choice(COURSES), "grade": round(random.uniform(50, 100), 2)},
            headers=self.headers,
            name="save grade",
        )

    @task(1)
    def reload_results(self):
        self.client.post(
            f"{SHOW_RESULTS}/api/results/refresh",
            headers=self.headers,
            name="reload results",
        )
