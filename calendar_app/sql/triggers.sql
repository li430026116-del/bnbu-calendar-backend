-- ================================================================
-- BNBU Calendar — Database Triggers
-- Target  : MySQL 8.0+
-- Tables  : enrollments, assignments, students, notifications
-- Execute : mysql -u root -p bnbu_calendar_db < triggers.sql
-- Python  : python manage.py load_triggers
-- ================================================================

DELIMITER //

-- ----------------------------------------------------------------
-- Trigger 1: after_enrollment_insert
--
-- Fires : AFTER INSERT ON enrollments
-- Effect: For the newly enrolled student, insert one DDL-reminder
--         notification for every assignment that already exists in
--         the course.  Skips if a matching notification exists
--         (idempotent guard).
-- ----------------------------------------------------------------

DROP TRIGGER IF EXISTS after_enrollment_insert //

CREATE TRIGGER after_enrollment_insert
AFTER INSERT ON enrollments
FOR EACH ROW
BEGIN
    DECLARE v_user_id BIGINT;

    -- Resolve the Django User PK from the Student record
    SELECT user_id
    INTO   v_user_id
    FROM   students
    WHERE  id = NEW.student_id;

    INSERT INTO notifications
           (user_id, title, content, type, related_id, is_read, created_at)
    SELECT  v_user_id,
            CONCAT('DDL Reminder: ', a.title),
            CONCAT('Deadline: ', DATE_FORMAT(a.deadline, '%Y-%m-%d %H:%i')),
            'ddl_reminder',
            a.id,
            FALSE,
            NOW()
    FROM   assignments a
    WHERE  a.course_id = NEW.course_id
      AND  NOT EXISTS (
               SELECT 1
               FROM   notifications n
               WHERE  n.user_id    = v_user_id
                 AND  n.related_id = a.id
                 AND  n.type       = 'ddl_reminder'
           );
END //

-- ----------------------------------------------------------------
-- Trigger 2: after_assignment_insert
--
-- Fires : AFTER INSERT ON assignments
-- Effect: For every active student enrolled in the course, insert
--         one DDL-reminder notification for the new assignment.
--         Skips duplicate notifications.
-- ----------------------------------------------------------------

DROP TRIGGER IF EXISTS after_assignment_insert //

CREATE TRIGGER after_assignment_insert
AFTER INSERT ON assignments
FOR EACH ROW
BEGIN
    INSERT INTO notifications
           (user_id, title, content, type, related_id, is_read, created_at)
    SELECT  s.user_id,
            CONCAT('DDL Reminder: ', NEW.title),
            CONCAT('Deadline: ', DATE_FORMAT(NEW.deadline, '%Y-%m-%d %H:%i')),
            'ddl_reminder',
            NEW.id,
            FALSE,
            NOW()
    FROM   enrollments e
    JOIN   students    s ON s.id = e.student_id
    WHERE  e.course_id = NEW.course_id
      AND  e.status    = 'active'
      AND  NOT EXISTS (
               SELECT 1
               FROM   notifications n
               WHERE  n.user_id    = s.user_id
                 AND  n.related_id = NEW.id
                 AND  n.type       = 'ddl_reminder'
           );
END //

-- ----------------------------------------------------------------
-- Trigger 3: after_assignment_complete
--
-- Fires : AFTER UPDATE ON assignments
-- When  : is_completed changes FALSE → TRUE
-- Effect: Add the course's credit to total_credit for every
--         active student enrolled in that course.
--
-- Join chain:
--   assignments.course_id → courses.credit
--   enrollments (course_id, student_id, status='active') → students.total_credit
-- ----------------------------------------------------------------

DROP TRIGGER IF EXISTS after_assignment_complete //

CREATE TRIGGER after_assignment_complete
AFTER UPDATE ON assignments
FOR EACH ROW
BEGIN
    DECLARE v_credit INT;

    IF OLD.is_completed = FALSE AND NEW.is_completed = TRUE THEN
        SELECT credit
        INTO   v_credit
        FROM   courses
        WHERE  id = NEW.course_id;

        UPDATE students s
        INNER JOIN enrollments e ON e.student_id = s.id
        SET    s.total_credit = s.total_credit + v_credit
        WHERE  e.course_id = NEW.course_id
          AND  e.status    = 'active';
    END IF;
END //

DELIMITER ;
