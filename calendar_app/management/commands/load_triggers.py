"""
管理命令：load_triggers
将 calendar_app/sql/triggers.sql 中定义的触发器装载进数据库。
自动检测后端（mysql / sqlite），使用对应的 SQL 语法。
用法：python manage.py load_triggers
"""
from django.core.management.base import BaseCommand
from django.db import connection

# ──────────────────────────────────────────────
# MySQL trigger bodies（无 DELIMITER，cursor 直接执行）
# ──────────────────────────────────────────────
_MYSQL = [
    {
        'name': 'after_enrollment_insert',
        'sql': """
CREATE TRIGGER after_enrollment_insert
AFTER INSERT ON enrollments
FOR EACH ROW
BEGIN
    DECLARE v_user_id BIGINT;
    SELECT user_id INTO v_user_id
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
               SELECT 1 FROM notifications n
               WHERE  n.user_id    = v_user_id
                 AND  n.related_id = a.id
                 AND  n.type       = 'ddl_reminder'
           );
END
""",
    },
    {
        'name': 'after_assignment_insert',
        'sql': """
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
               SELECT 1 FROM notifications n
               WHERE  n.user_id    = s.user_id
                 AND  n.related_id = NEW.id
                 AND  n.type       = 'ddl_reminder'
           );
END
""",
    },
    {
        'name': 'after_assignment_complete',
        'sql': """
CREATE TRIGGER after_assignment_complete
AFTER UPDATE ON assignments
FOR EACH ROW
BEGIN
    DECLARE v_credit INT;
    IF OLD.is_completed = FALSE AND NEW.is_completed = TRUE THEN
        SELECT credit INTO v_credit
        FROM   courses
        WHERE  id = NEW.course_id;

        UPDATE students s
        INNER JOIN enrollments e ON e.student_id = s.id
        SET    s.total_credit = s.total_credit + v_credit
        WHERE  e.course_id = NEW.course_id
          AND  e.status    = 'active';
    END IF;
END
""",
    },
]

# ──────────────────────────────────────────────
# SQLite trigger bodies
# 差异：|| 代替 CONCAT，datetime() 代替 NOW()，
#        0/1 代替 FALSE/TRUE，子查询代替 DECLARE
# ──────────────────────────────────────────────
_SQLITE = [
    {
        'name': 'after_enrollment_insert',
        'sql': """
CREATE TRIGGER after_enrollment_insert
AFTER INSERT ON enrollments
FOR EACH ROW
BEGIN
    INSERT INTO notifications
           (user_id, title, content, type, related_id, is_read, created_at)
    SELECT  (SELECT user_id FROM students WHERE id = NEW.student_id),
            'DDL Reminder: ' || a.title,
            'Deadline: ' || datetime(a.deadline),
            'ddl_reminder',
            a.id,
            0,
            datetime('now')
    FROM   assignments a
    WHERE  a.course_id = NEW.course_id
      AND  NOT EXISTS (
               SELECT 1 FROM notifications n
               WHERE  n.user_id    = (SELECT user_id FROM students WHERE id = NEW.student_id)
                 AND  n.related_id = a.id
                 AND  n.type       = 'ddl_reminder'
           );
END
""",
    },
    {
        'name': 'after_assignment_insert',
        'sql': """
CREATE TRIGGER after_assignment_insert
AFTER INSERT ON assignments
FOR EACH ROW
BEGIN
    INSERT INTO notifications
           (user_id, title, content, type, related_id, is_read, created_at)
    SELECT  s.user_id,
            'DDL Reminder: ' || NEW.title,
            'Deadline: ' || datetime(NEW.deadline),
            'ddl_reminder',
            NEW.id,
            0,
            datetime('now')
    FROM   enrollments e
    JOIN   students    s ON s.id = e.student_id
    WHERE  e.course_id = NEW.course_id
      AND  e.status    = 'active'
      AND  NOT EXISTS (
               SELECT 1 FROM notifications n
               WHERE  n.user_id    = s.user_id
                 AND  n.related_id = NEW.id
                 AND  n.type       = 'ddl_reminder'
           );
END
""",
    },
    {
        'name': 'after_assignment_complete',
        # SQLite: AFTER UPDATE OF col 仅在该列被显式 UPDATE 时触发；
        # WHEN 子句过滤 0→1 的跳变；子查询替代 DECLARE。
        'sql': """
CREATE TRIGGER after_assignment_complete
AFTER UPDATE OF is_completed ON assignments
FOR EACH ROW
WHEN OLD.is_completed = 0 AND NEW.is_completed = 1
BEGIN
    UPDATE students
    SET    total_credit = total_credit + (
               SELECT credit FROM courses WHERE id = NEW.course_id
           )
    WHERE  id IN (
               SELECT student_id
               FROM   enrollments
               WHERE  course_id = NEW.course_id
                 AND  status    = 'active'
           );
END
""",
    },
]


class Command(BaseCommand):
    help = 'Load SQL triggers (auto-detects MySQL/SQLite backend)'

    def handle(self, *args, **options):
        vendor = connection.vendor
        self.stdout.write(f'Backend: {vendor}')

        defs = _MYSQL if vendor == 'mysql' else _SQLITE

        with connection.cursor() as cursor:
            for tdef in defs:
                name = tdef['name']
                cursor.execute(f'DROP TRIGGER IF EXISTS {name}')
                self.stdout.write(f'  dropped (if existed): {name}')
                cursor.execute(tdef['sql'])
                self.stdout.write(self.style.SUCCESS(f'  created: {name}'))

        self.stdout.write(self.style.SUCCESS('\nAll triggers loaded.'))
