-- Removes the fake students added by seed.sql and the grades added by the load test user.
-- Change 'loadtest' below if you used a different load test username.

DELETE g FROM grades AS g
JOIN users AS u ON u.id = g.user_id
WHERE u.username LIKE 'seeduser%' OR u.username = 'loadtest';

DELETE FROM users WHERE username LIKE 'seeduser%';

SELECT (SELECT COUNT(*) FROM users) AS total_users, (SELECT COUNT(*) FROM grades) AS total_grades;
