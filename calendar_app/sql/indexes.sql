-- ================================================================
-- BNBU Calendar — Database Indexes
-- Target  : MySQL/MariaDB 8.0+
-- Execute : mysql -u root -p bnbu_calendar_db < indexes.sql
-- ================================================================

-- ----------------------------------------------------------------
-- Current index status (verified 2026-04-28):
-- ALL indexes below are already created by Django migrations.
-- This file serves as the authoritative record and can be used
-- to recreate indexes on a fresh database.
-- ----------------------------------------------------------------

-- enrollments: (student_id, status) composite index
CREATE INDEX IF NOT EXISTS enrollments_student_929bef_idx
    ON enrollments (student_id, status);

-- enrollments: (course_id) index
CREATE INDEX IF NOT EXISTS enrollments_course__711f04_idx
    ON enrollments (course_id);

-- notifications: (user_id, is_read) composite index
CREATE INDEX IF NOT EXISTS notificatio_user_id_a4dd5c_idx
    ON notifications (user_id, is_read);

-- notifications: (user_id, created_at) composite index
CREATE INDEX IF NOT EXISTS notificatio_user_id_7336fd_idx
    ON notifications (user_id, created_at);

-- assignments: (course_id, deadline) composite index
CREATE INDEX IF NOT EXISTS assignments_course__2a7178_idx
    ON assignments (course_id, deadline);

-- assignments: (deadline) single-column index
CREATE INDEX IF NOT EXISTS assignments_deadlin_9c956b_idx
    ON assignments (deadline);

-- assignment_submissions: (assignment_id, student_id) composite index
CREATE INDEX IF NOT EXISTS assignment__assignm_c9693f_idx
    ON assignment_submissions (assignment_id, student_id);

-- events: (start_time, end_time) composite index
CREATE INDEX IF NOT EXISTS events_start_t_9c99d7_idx
    ON events (start_time, end_time);

-- events: (category_id) index
CREATE INDEX IF NOT EXISTS events_categor_fd16be_idx
    ON events (category_id);

-- personal_tasks: (owner_id, due_at) composite index
CREATE INDEX IF NOT EXISTS personal_ta_owner_i_19b6f2_idx
    ON personal_tasks (owner_id, due_at);

-- personal_tasks: (due_at) single-column index
CREATE INDEX IF NOT EXISTS personal_ta_due_at_ecb28a_idx
    ON personal_tasks (due_at);

-- courses: (semester_id) index — auto-created by Django FK
CREATE INDEX IF NOT EXISTS courses_semester_id_b0a820a8_fk_semesters_id
    ON courses (semester_id);

-- courses: (teacher_id) index — auto-created by Django FK
CREATE INDEX IF NOT EXISTS courses_teacher_id_79a070ce_fk_teachers_id
    ON courses (teacher_id);
