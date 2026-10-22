import os

os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")

from app import calculate_results


def test_statistics():
    result = calculate_results([
        {
            "user_id": 1,
            "username": "student1",
            "grade_id": 1,
            "course_name": "Math",
            "grade": 60,
        },
        {
            "user_id": 1,
            "username": "student1",
            "grade_id": 2,
            "course_name": "Math",
            "grade": 80,
        },
    ])[0]

    assert result["user_id"] == 1
    assert result["username"] == "student1"
    assert len(result["grades"]) == 2

    assert result["summary"] == {
        "count": 2,
        "minimum": 60,
        "maximum": 80,
        "average": 70,
    }


def test_summary_includes_all_courses():
    result = calculate_results([
        {
            "user_id": 1,
            "username": "student1",
            "grade_id": 1,
            "course_name": "Math",
            "grade": 60,
        },
        {
            "user_id": 1,
            "username": "student1",
            "grade_id": 2,
            "course_name": "Science",
            "grade": 90,
        },
    ])[0]

    assert result["summary"]["count"] == 2
    assert result["summary"]["average"] == 75
    assert {row["course_name"] for row in result["grades"]} == {
        "Math",
        "Science",
    }


def test_users_have_separate_results():
    results = calculate_results([
        {
            "user_id": 1,
            "username": "student1",
            "grade_id": 1,
            "course_name": "Math",
            "grade": 60,
        },
        {
            "user_id": 2,
            "username": "student2",
            "grade_id": 2,
            "course_name": "Math",
            "grade": 90,
        },
    ])

    by_user = {result["user_id"]: result for result in results}

    assert len(by_user) == 2
    assert by_user[1]["summary"]["average"] == 60
    assert by_user[2]["summary"]["average"] == 90
    assert by_user[1]["grades"][0]["grade_id"] == 1
    assert by_user[2]["grades"][0]["grade_id"] == 2


def test_user_without_grades():
    result = calculate_results([
        {
            "user_id": 1,
            "username": "student1",
            "grade_id": None,
            "course_name": None,
            "grade": None,
        },
    ])[0]

    assert result["grades"] == []
    assert result["summary"] == {
        "count": 0,
        "minimum": None,
        "maximum": None,
        "average": None,
    }


def test_empty_input():
    assert calculate_results([]) == []


def test_average_uses_individual_grades():
    result = calculate_results([
        {
            "user_id": 1,
            "username": "student1",
            "grade_id": 1,
            "course_name": "Math",
            "grade": 60,
        },
        {
            "user_id": 1,
            "username": "student1",
            "grade_id": 2,
            "course_name": "Math",
            "grade": 80,
        },
        {
            "user_id": 1,
            "username": "student1",
            "grade_id": 3,
            "course_name": "Science",
            "grade": 100,
        },
    ])[0]

    # (60 + 80 + 100) / 3 = 80.
    # Averaging the two course averages would incorrectly give 85.
    assert result["summary"]["average"] == 80