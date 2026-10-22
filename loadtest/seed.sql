-- Adds 200 fake students with 100 grades each (20,000 grades) so the database
-- looks like a real class list instead of an almost empty test system.
-- The fake accounts can't log in (their password hash is not a real hash).
-- Remove them afterwards with cleanup.sql.

SET SESSION cte_max_recursion_depth = 1000;

INSERT INTO users (username, password_hash)
WITH RECURSIVE seq(n) AS (
  SELECT 1 UNION ALL SELECT n + 1 FROM seq WHERE n < 200
)
SELECT CONCAT('seeduser', n), 'seed-account-cannot-log-in' FROM seq;

INSERT INTO grades (user_id, course_name, grade)
WITH RECURSIVE seq(n) AS (
  SELECT 1 UNION ALL SELECT n + 1 FROM seq WHERE n < 100
)
SELECT u.id,
       ELT(1 + (s.n % 5), 'Math', 'Science', 'English', 'History', 'Art'),
       ROUND(50 + RAND() * 50, 2)
FROM users AS u
CROSS JOIN seq AS s
WHERE u.username LIKE 'seeduser%';

SELECT (SELECT COUNT(*) FROM users) AS total_users, (SELECT COUNT(*) FROM grades) AS total_grades;
