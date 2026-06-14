# BNBU Calendar Database — Relational Schema

**Database:** `bnbu_calendar_db` &nbsp;|&nbsp; **Engine:** MariaDB / MySQL &nbsp;|&nbsp; **Tables:** 17

> Convention: `<u>field</u>→Table` = Foreign Key &nbsp;|&nbsp; **field** = Primary Key &nbsp;|&nbsp; `*` = Unique constraint

---

## 1. User
**User** (**id**, username, password, email, first_name, last_name, role, avatar_url, email_notifications, dark_mode, auto_sync, is_active, is_staff, is_superuser, last_login, date_joined)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| username | VARCHAR(150) | Unique |
| password | VARCHAR(128) | Hashed |
| email | VARCHAR(254) | |
| first_name | VARCHAR(150) | |
| last_name | VARCHAR(150) | |
| role | VARCHAR(10) | `student` / `teacher` / `admin` |
| avatar_url | VARCHAR(200) | Nullable |
| email_notifications | TINYINT(1) | Default 1 |
| dark_mode | TINYINT(1) | Default 0 |
| auto_sync | TINYINT(1) | Default 1 |
| is_active | TINYINT(1) | Default 1 |
| is_staff | TINYINT(1) | Default 0 |
| is_superuser | TINYINT(1) | Default 0 |
| last_login | DATETIME(6) | Nullable |
| date_joined | DATETIME(6) | |

- **PK:** id
- **Unique:** username

---

## 2. Student
**Student** (**id**, <u>user_id</u>→User, student_id, name, major_code, major_name, faculty, grade, total_credit)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| user_id | BIGINT | FK → User(id), Unique |
| student_id | VARCHAR(20) | Unique |
| name | VARCHAR(100) | |
| major_code | VARCHAR(10) | |
| major_name | VARCHAR(100) | |
| faculty | VARCHAR(10) | Faculty code |
| grade | INT | Year of study |
| total_credit | INT | Default 0 |

- **PK:** id
- **FK:** user_id → User(id) ON DELETE CASCADE
- **Unique:** user_id, student_id

---

## 3. Teacher
**Teacher** (**id**, <u>user_id</u>→User, teacher_id, name, faculty, title)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| user_id | BIGINT | FK → User(id), Unique |
| teacher_id | VARCHAR(20) | Unique |
| name | VARCHAR(100) | |
| faculty | VARCHAR(10) | Faculty code |
| title | VARCHAR(50) | e.g. Professor, Associate Professor |

- **PK:** id
- **FK:** user_id → User(id) ON DELETE CASCADE
- **Unique:** user_id, teacher_id

---

## 4. Semester
**Semester** (**id**, name, start_date, end_date, is_current)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| name | VARCHAR(50) | e.g. "2024-2025-1" |
| start_date | DATE | |
| end_date | DATE | |
| is_current | TINYINT(1) | Default 0 |

- **PK:** id

---

## 5. Venue
**Venue** (**id**, name, building, capacity, type)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| name | VARCHAR(50) | |
| building | VARCHAR(20) | |
| capacity | INT | Default 50 |
| type | VARCHAR(20) | `classroom` / `lab` / `auditorium` / `gym` / `library` / `meeting` / `online` |

- **PK:** id

---

## 6. Category
**Category** (**id**, name, name_cn, color, icon)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| name | VARCHAR(50) | English name |
| name_cn | VARCHAR(50) | Chinese name, optional |
| color | VARCHAR(10) | Hex color code, Default `#5B8DEF` |
| icon | VARCHAR(30) | Icon identifier, optional |

- **PK:** id

---

## 7. Course
**Course** (**id**, code, name, description, <u>teacher_id</u>→Teacher, <u>semester_id</u>→Semester, credit, schedule, <u>venue_id</u>→Venue, faculty, max_students)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| code | VARCHAR(20) | Unique |
| name | VARCHAR(200) | |
| description | LONGTEXT | Optional |
| teacher_id | BIGINT | FK → Teacher(id), Nullable |
| semester_id | BIGINT | FK → Semester(id) |
| credit | INT | Default 3 |
| schedule | VARCHAR(100) | Text description of class times |
| venue_id | BIGINT | FK → Venue(id), Nullable |
| faculty | VARCHAR(10) | Faculty code of the offering department |
| max_students | INT | Default 120 |

- **PK:** id
- **FK:** teacher_id → Teacher(id) ON DELETE SET NULL
- **FK:** semester_id → Semester(id) ON DELETE CASCADE
- **FK:** venue_id → Venue(id) ON DELETE SET NULL
- **Unique:** code

---

## 8. Assignment
**Assignment** (**id**, <u>course_id</u>→Course, title, description, deadline, priority, created_at, is_completed)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| course_id | BIGINT | FK → Course(id) |
| title | VARCHAR(200) | |
| description | LONGTEXT | Optional |
| deadline | DATETIME(6) | Indexed |
| priority | VARCHAR(10) | `high` / `medium` / `low`, Default `medium` |
| created_at | DATETIME(6) | Default NOW() |
| is_completed | TINYINT(1) | Default 0 |

- **PK:** id
- **FK:** course_id → Course(id) ON DELETE CASCADE
- **Index:** (course_id, deadline), (deadline)

---

## 9. Enrollment
**Enrollment** (**id**, <u>student_id</u>→Student, <u>course_id</u>→Course, enrolled_at, status)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| student_id | BIGINT | FK → Student(id) |
| course_id | BIGINT | FK → Course(id) |
| enrolled_at | DATETIME(6) | |
| status | VARCHAR(10) | `active` / `dropped`, Default `active` |

- **PK:** id
- **FK:** student_id → Student(id) ON DELETE CASCADE
- **FK:** course_id → Course(id) ON DELETE CASCADE
- **Unique:** (student_id, course_id)
- **Index:** (student_id, status), (course_id)

---

## 10. Event
**Event** (**id**, title, description, start_time, end_time, <u>venue_id</u>→Venue, <u>category_id</u>→Category, organizer, is_public, image, <u>created_by_id</u>→User)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| title | VARCHAR(200) | |
| description | LONGTEXT | Optional |
| start_time | DATETIME(6) | Indexed |
| end_time | DATETIME(6) | Indexed |
| venue_id | BIGINT | FK → Venue(id), Nullable |
| category_id | BIGINT | FK → Category(id), Nullable |
| organizer | VARCHAR(100) | Organizer name, optional |
| is_public | TINYINT(1) | Default 1 |
| image | VARCHAR(100) | Event image path, Nullable |
| created_by_id | BIGINT | FK → User(id), Nullable |

- **PK:** id
- **FK:** venue_id → Venue(id) ON DELETE SET NULL
- **FK:** category_id → Category(id) ON DELETE SET NULL
- **FK:** created_by_id → User(id) ON DELETE SET NULL
- **Index:** (start_time, end_time), (category_id)

---

## 11. Notification
**Notification** (**id**, <u>user_id</u>→User, title, content, type, related_id, is_read, created_at)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| user_id | BIGINT | FK → User(id) |
| title | VARCHAR(200) | |
| content | LONGTEXT | Optional |
| type | VARCHAR(20) | `ddl_reminder` / `announcement` / `system`, Default `system` |
| related_id | INT | ID of the related object, Nullable |
| is_read | TINYINT(1) | Default 0, Indexed |
| created_at | DATETIME(6) | Default NOW(), Indexed |

- **PK:** id
- **FK:** user_id → User(id) ON DELETE CASCADE
- **Index:** (user_id, is_read), (user_id, created_at)

---

## 12. CustomTag
**CustomTag** (**id**, <u>user_id</u>→User, name, color)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| user_id | BIGINT | FK → User(id) |
| name | VARCHAR(50) | |
| color | VARCHAR(10) | Hex color code, Default `#5B8DEF` |

- **PK:** id
- **FK:** user_id → User(id) ON DELETE CASCADE

---

## 13. Feedback
**Feedback** (**id**, <u>user_id</u>→User, title, content, status, created_at)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| user_id | BIGINT | FK → User(id) |
| title | VARCHAR(200) | |
| content | LONGTEXT | |
| status | VARCHAR(10) | `pending` / `resolved` / `rejected`, Default `pending` |
| created_at | DATETIME(6) | Default NOW() |

- **PK:** id
- **FK:** user_id → User(id) ON DELETE CASCADE

---

## 14. EventSubscription
**EventSubscription** (**id**, <u>user_id</u>→User, <u>event_id</u>→Event, subscribed_at)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| user_id | BIGINT | FK → User(id) |
| event_id | BIGINT | FK → Event(id) |
| subscribed_at | DATETIME(6) | Default NOW() |

- **PK:** id
- **FK:** user_id → User(id) ON DELETE CASCADE
- **FK:** event_id → Event(id) ON DELETE CASCADE
- **Unique:** (user_id, event_id)

---

## 15. AssignmentSubmission
**AssignmentSubmission** (**id**, <u>assignment_id</u>→Assignment, <u>student_id</u>→Student, file, submitted_at)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| assignment_id | BIGINT | FK → Assignment(id) |
| student_id | BIGINT | FK → Student(id) |
| file | VARCHAR(100) | Uploaded submission file path |
| submitted_at | DATETIME(6) | Default NOW() |

- **PK:** id
- **FK:** assignment_id → Assignment(id) ON DELETE CASCADE
- **FK:** student_id → Student(id) ON DELETE CASCADE
- **Unique:** (assignment_id, student_id)
- **Index:** (assignment_id, student_id)

---

## 16. PersonalTask
**PersonalTask** (**id**, <u>owner_id</u>→User, title, description, due_at, priority, is_completed, share_token, <u>source_task_id</u>→PersonalTask, created_at, updated_at)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| owner_id | BIGINT | FK → User(id) |
| title | VARCHAR(200) | |
| description | LONGTEXT | Optional |
| due_at | DATETIME(6) | Indexed |
| priority | VARCHAR(10) | `high` / `medium` / `low`, Default `medium` |
| is_completed | TINYINT(1) | Default 0 |
| share_token | VARCHAR(32) | Nullable, Unique, Indexed |
| source_task_id | BIGINT | Self FK → PersonalTask(id), Nullable |
| created_at | DATETIME(6) | Default NOW() |
| updated_at | DATETIME(6) | Auto-updated on save |

- **PK:** id
- **FK:** owner_id → User(id) ON DELETE CASCADE
- **FK:** source_task_id → PersonalTask(id) ON DELETE SET NULL
- **Unique:** share_token
- **Index:** (owner_id, due_at), (due_at)

---

## 17. ShareLink
**ShareLink** (**id**, <u>user_id</u>→User, token, created_at)

| Field | Type | Notes |
|-------|------|-------|
| **id** | BIGINT | PK, AUTO_INCREMENT |
| user_id | BIGINT | FK → User(id) |
| token | VARCHAR(8) | Unique, Indexed |
| created_at | DATETIME(6) | Default NOW() |

- **PK:** id
- **FK:** user_id → User(id) ON DELETE CASCADE
- **Unique:** token
- **Index:** token

---

## FK Relationship Summary

| # | Child Table | FK Field | Parent Table | On Delete |
|---|-------------|----------|--------------|-----------|
| 1 | Student | user_id | User(id) | CASCADE |
| 2 | Teacher | user_id | User(id) | CASCADE |
| 3 | Course | teacher_id | Teacher(id) | SET NULL |
| 4 | Course | semester_id | Semester(id) | CASCADE |
| 5 | Course | venue_id | Venue(id) | SET NULL |
| 6 | Assignment | course_id | Course(id) | CASCADE |
| 7 | Enrollment | student_id | Student(id) | CASCADE |
| 8 | Enrollment | course_id | Course(id) | CASCADE |
| 9 | Event | venue_id | Venue(id) | SET NULL |
| 10 | Event | category_id | Category(id) | SET NULL |
| 11 | Event | created_by_id | User(id) | SET NULL |
| 12 | Notification | user_id | User(id) | CASCADE |
| 13 | CustomTag | user_id | User(id) | CASCADE |
| 14 | Feedback | user_id | User(id) | CASCADE |
| 15 | EventSubscription | user_id | User(id) | CASCADE |
| 16 | EventSubscription | event_id | Event(id) | CASCADE |
| 17 | AssignmentSubmission | assignment_id | Assignment(id) | CASCADE |
| 18 | AssignmentSubmission | student_id | Student(id) | CASCADE |
| 19 | PersonalTask | owner_id | User(id) | CASCADE |
| 20 | PersonalTask | source_task_id | PersonalTask(id) | SET NULL |
| 21 | ShareLink | user_id | User(id) | CASCADE |
