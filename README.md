# BNBU Calendar — Campus Schedule Management Platform (Backend)

> 北师港浸大数据库系统课程结课项目 · 后端独立开发

A full-featured RESTful backend for a campus-wide calendar and schedule management platform, supporting **student, teacher, and administrator** portals. Built with Django 5.2 + Django REST Framework + MySQL.

## ✨ Highlights

- **17 database tables** with full relational design (ER modeling, normalization to 3NF/BCNF)
- **45 REST API endpoints** across 10 functional modules
- **3 MySQL triggers** for automated business logic (auto-notification on enrollment, auto-credit on assignment completion)
- **13 composite/single-column indexes** optimizing high-frequency query paths
- **RFC 5545 iCal export** — one-click sync to Google Calendar / Apple Calendar
- **Token-based calendar & task sharing** with public access (no login required)
- **4-tier RBAC permission system** (Student / Teacher / Admin / EduAdmin)
- Unified API response format with global exception handling

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | Django 5.2 + Django REST Framework |
| Database | MySQL 8.0 (with SQLite fallback for dev/testing) |
| Authentication | Bearer Token (custom) + DRF Token + Session |
| File Handling | Pillow (image processing), multipart upload |
| Calendar | icalendar (RFC 5545 .ics generation) |
| Data Generation | Faker (test data seeding) |
| Cross-Origin | django-cors-headers |
| Filtering | django-filter |

## 📋 Functional Modules

| Module | Description |
|--------|-------------|
| **Authentication** | Register/login/logout with auto-profile creation; Bearer Token auth |
| **Course Management** | Browse courses, one-click enrollment, view course details & assignments |
| **Assignment / DDL Tracking** | View all assignment deadlines across enrolled courses, mark completion, priority sorting |
| **File Submission** | Upload assignment attachments with re-submit and withdraw support |
| **Campus Events** | Browse school-wide events with category/date filtering, subscribe to events |
| **Personal Tasks** | Create private to-do items with priority and due dates |
| **Aggregated Calendar** | Unified calendar view combining DDLs + events + personal tasks |
| **Calendar Export** | Export .ics file containing all schedule items |
| **Calendar & Task Sharing** | Generate shareable links for calendar (7-day view) and individual tasks |
| **Smart Notifications** | Auto-push DDL reminders on enrollment/assignment creation, batch mark-as-read |
| **User Preferences** | Dark mode, email notifications, data sync settings |
| **Teacher Portal** | Create/manage courses & assignments, view enrolled students, dashboard stats |
| **Admin Portal** | Publish campus events, data dashboard, activity logs |

## 🗄 Database Design

17 custom tables (plus Django built-in auth tables):

```
User (AbstractUser) ──1:1── Student (student_id, major, credits)
                    ──1:1── Teacher (teacher_id, title)

Semester ──1:N── Course ──N:1── Teacher
                        ──N:1── Venue
                        ──M:N── Student (via Enrollment)
                        ──1:N── Assignment ──1:N── AssignmentSubmission

Event ──1:N── EventSubscription ──N:1── User
      ──N:1── Category

User ──1:N── PersonalTask
     ──1:N── Notification
     ──1:N── CustomTag
     ──1:N── Feedback
     ──1:N── ShareLink
```

### Triggers (MySQL)

| Trigger | Event | Logic |
|---------|-------|-------|
| `after_enrollment_insert` | Student enrolls in course | Auto-generate DDL notifications for all existing assignments |
| `after_assignment_insert` | Teacher creates assignment | Auto-push notification to all enrolled students |
| `after_assignment_complete` | Student completes assignment | Auto-accumulate course credits to student's total |

All trigger logic has a Python-layer fallback for SQLite compatibility.

### Indexes

13 composite and single-column indexes covering high-frequency query paths, including:
- `(owner_id, due_at)` on personal tasks
- `(course_id, deadline)` on assignments
- `(user_id, is_read)` on notifications

## 🔌 API Overview

**Authentication**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register (returns Token) |
| POST | `/api/auth/login/` | Login (returns Token) |
| POST | `/api/auth/logout/` | Logout (delete Token) |
| GET | `/api/auth/me/` | Current user info |

**Courses & Enrollment**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/courses/` | List courses (filter by semester/faculty) |
| POST | `/api/enrollments/` | Enroll in course (student only) |
| GET | `/api/enrollments/my/` | My enrollments |
| GET | `/api/courses/{id}/students/` | Student roster |

**Assignments**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/assignments/my/` | My assignments (filtered by enrollment) |
| POST | `/api/assignments/{id}/complete/` | Mark complete |
| POST | `/api/assignments/{id}/submission/` | Submit file |

**Calendar & Export**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/calendar/events/` | Aggregated calendar (DDLs + events + tasks) |
| GET | `/api/calendar/export/ical/` | Export .ics file |
| POST | `/api/calendar/share/` | Generate share link |
| GET | `/api/shared/{token}/` | View shared calendar (no auth) |

**Personal Tasks**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/personal-tasks/` | List / create tasks |
| POST | `/api/personal-tasks/{id}/share/` | Generate share link |
| GET | `/api/personal-tasks/shared/{token}/ical/` | Download task as .ics |

> Full API: 45 endpoint actions across 20+ URL patterns. See source code for complete routing.

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- MySQL 8.0+ (or use SQLite for quick testing)

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/bnbu-calendar-backend.git
cd bnbu-calendar-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure database (create .env file)
echo "MYSQL_DATABASE=bnbu_calendar" > .env
echo "MYSQL_USER=root" >> .env
echo "MYSQL_PASSWORD=your_password" >> .env

# Run migrations
python manage.py migrate

# (Optional) Load triggers and indexes for MySQL
mysql -u root -p bnbu_calendar < calendar_app/sql/triggers.sql
mysql -u root -p bnbu_calendar < calendar_app/sql/indexes.sql

# Start server
python manage.py runserver
```

## 📁 Project Structure

```
bnbu-calendar-backend/
├── calendar_app/
│   ├── models/          # 17 Django models
│   ├── views/           # ViewSets & API views
│   ├── serializers/     # DRF serializers
│   ├── permissions.py   # 4-tier RBAC (IsStudent/IsTeacher/IsAdmin/IsEduAdmin)
│   ├── urls.py          # URL routing
│   ├── api_response.py  # Unified response wrapper
│   └── sql/
│       ├── triggers.sql # 3 MySQL triggers
│       └── indexes.sql  # 13 indexes
├── manage.py
├── requirements.txt
└── README.md
```

## 👤 Author

**Sophie Li** — Data Science, BNBU (Beijing Normal University - Hong Kong Baptist University United International College)

Backend independently designed and implemented as a course final project for Database Systems.
