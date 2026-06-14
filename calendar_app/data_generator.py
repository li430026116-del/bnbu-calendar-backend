# -*- coding: utf-8 -*-
"""
BNBU 校园日程管理系统 - 数据生成脚本 (完整补全版)
"""

import os
import csv
import random
from datetime import datetime, timedelta, time, date
from faker import Faker
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.hashers import make_password
from calendar_app.models import (
    User, Student, Teacher, Course, Semester, Venue, Category,
    Enrollment, Assignment, Event, Notification, CustomTag, Feedback
)

fake = Faker('zh_CN')
random.seed(42)
Faker.seed(42)

# ============================================================
# 配置与元数据
# ============================================================
BATCH_SIZE = 2000
EMAIL_DOMAIN = "mail.bnbu.edu.cn"

# 目标数量（调整这里即可控制规模）
N_STUDENTS    = 5000   # → 5000 students, 5000 user accounts
N_TEACHERS    = 50     # → 50 teachers
N_ASSIGN_PER_COURSE = 20   # assignments per course  (~6000 total with 301 courses)
N_ENROLL_PER_STUDENT = 10  # enrollments per student → 5000×10 = 50 000
N_EVENTS      = 50001
N_NOTIF_EXTRA = 50001   # manual notifications (beyond trigger-generated ones)
N_FEEDBACK    = 5000

EVENT_TITLES = [
    'Academic Writing Workshop',
    'Database Systems Review Session',
    'Campus Career Talk',
    'AI Innovation Seminar',
    'Student Club Meeting',
    'Final Exam Briefing',
    'Library Study Session',
    'Business Case Competition',
    'Programming Lab Practice',
    'Graduation Project Meeting',
    'Python Lab Practice',
    'Research Methodology Seminar',
    'Group Presentation Session',
    'Campus Volunteer Briefing',
    'International Student Orientation',
]

EVENT_DESCRIPTIONS = [
    'This event is arranged to help students review key course content and prepare for upcoming academic tasks.',
    'Students are encouraged to attend on time and bring the required learning materials.',
    'This session focuses on academic development, teamwork, and practical learning experience.',
    'The activity provides useful information for study planning and campus participation.',
    'Please check the course portal regularly for updates related to this event.',
]

NOTIFICATION_TITLES = [
    'Assignment deadline reminder',
    'New course announcement',
    'Campus event update',
    'System maintenance notice',
    'Course schedule updated',
    'Exam arrangement released',
    'New feedback received',
    'Library notice',
    'Class reminder',
    'Student activity update',
]

NOTIFICATION_CONTENTS = [
    'Please check the latest update in your student portal.',
    'A new academic notice has been released for your attention.',
    'Please review your course schedule and prepare accordingly.',
    'This is a reminder about an upcoming deadline or campus activity.',
    'Further details are available in the dashboard and related course page.',
]

ASSIGNMENT_TITLES = [
    'Weekly Practice Assignment',
    'Course Reading Report',
    'Lab Exercise Submission',
    'Group Project Milestone',
    'Final Review Task',
]

ASSIGNMENT_DESCRIPTIONS = [
    'Please complete the required task and submit it before the deadline.',
    'This assignment helps students review important course concepts.',
    'Students should follow the instructions in the course portal.',
    'Please prepare your work carefully and upload the final version on time.',
]

FEEDBACK_TITLES = [
    'Course feedback submitted',
    'Learning support request',
    'Teaching quality feedback',
    'Campus service suggestion',
    'Student portal feedback',
]

FEEDBACK_CONTENTS = [
    'The student submitted feedback about course learning experience.',
    'This feedback records a suggestion for improving academic support.',
    'The message has been received and will be reviewed by the relevant team.',
    'Please follow up with the student if additional details are required.',
]


def template_text(pool, index):
    return pool[index % len(pool)]


def event_times_for_index(base_date, index):
    hour_slots = [8, 9, 10, 11, 14, 15, 16, 18, 19, 20]
    day_offset = index % 365
    hour = hour_slots[index % len(hour_slots)]
    start_time = base_date + timedelta(days=day_offset)
    start_time = start_time.replace(hour=hour, minute=0, second=0, microsecond=0)
    return start_time, start_time + timedelta(hours=1)

FACULTIES = {
    'FBM': {'name_cn': '工商管理学院', 'majors': {'ACCT': 'Accounting', 'FIN': 'Finance', 'CST': 'Computer Science'}},
    'FST': {'name_cn': '理工科技学院', 'majors': {'AI': 'Artificial Intelligence', 'DS': 'Data Science', 'CST': 'Computer Science'}},
}

SEMESTERS_DATA = [
    {'name': '2024-2025 春季学期', 'start': date(2025, 2, 10), 'end': date(2025, 5, 20), 'is_current': False},
    {'name': '2025-2026 春季学期', 'start': date(2026, 2, 24), 'end': date(2026, 5, 29), 'is_current': True},
]

CATEGORIES_DATA = [
    {'name': 'Academic', 'name_cn': '学术活动', 'color': '#5B8DEF'},
    {'name': 'Sports', 'name_cn': '体育活动', 'color': '#7ED321'},
    {'name': 'Course', 'name_cn': '课程相关', 'color': '#4A90E2'},
]

# ============================================================
# 数据生成逻辑
# ============================================================

def save_to_database():
    """核心持久化函数，严格按依赖顺序写入"""

    print("Starting database population...")

    # Pre-hash password once to avoid re-hashing N_STUDENTS times
    pwd_hash = make_password('password123')

    with transaction.atomic():
        # 1. Semester
        print("[1/12] Saving Semesters...")
        Semester.objects.bulk_create(
            [Semester(name=s['name'], start_date=s['start'], end_date=s['end'],
                      is_current=s['is_current']) for s in SEMESTERS_DATA]
        )
        all_semesters = list(Semester.objects.all())

        # 2. Category
        print("[2/12] Saving Categories...")
        Category.objects.bulk_create(
            [Category(name=c['name'], name_cn=c['name_cn'], color=c['color'])
             for c in CATEGORIES_DATA]
        )
        all_categories = list(Category.objects.all())

        # 3. Venue
        print("[3/12] Saving Venues...")
        venue_objs = []
        buildings = ['T1', 'T2', 'T3', 'T7', 'A1', 'A2']
        for i in range(1, 61):
            venue_objs.append(Venue(
                name=f"{random.choice(buildings)}-{100+i}",
                building=random.choice(buildings),
                capacity=random.choice([30, 50, 80, 120, 200]),
                type=random.choice(['classroom', 'lab', 'auditorium'])
            ))
        Venue.objects.bulk_create(venue_objs)
        all_venues = list(Venue.objects.all())

        # 4. Users (bulk, single password hash)
        print(f"[4/12] Saving Users ({N_TEACHERS} teachers + {N_STUDENTS} students)...")
        user_objs = []
        for i in range(N_TEACHERS):
            user_objs.append(User(
                username=f"t{1000+i}", email=f"t{1000+i}@{EMAIL_DOMAIN}",
                role='teacher', password=pwd_hash
            ))
        for i in range(N_STUDENTS):
            user_objs.append(User(
                username=f"s{2024000+i}", email=f"s{2024000+i}@{EMAIL_DOMAIN}",
                role='student', password=pwd_hash
            ))
        User.objects.bulk_create(user_objs, batch_size=BATCH_SIZE)
        all_users       = list(User.objects.exclude(is_superuser=True))
        teacher_users   = [u for u in all_users if u.role == 'teacher']
        student_users   = [u for u in all_users if u.role == 'student']

        # 5. Teacher / Student profiles
        print("[5/12] Saving Profiles...")
        faculties = list(FACULTIES.keys())
        titles    = ['Lecturer', 'Assistant Professor', 'Associate Professor', 'Professor']
        Teacher.objects.bulk_create(
            [Teacher(user=u, teacher_id=u.username, name=fake.name(),
                     faculty=random.choice(faculties), title=random.choice(titles))
             for u in teacher_users],
            batch_size=BATCH_SIZE
        )
        all_teachers = list(Teacher.objects.all())

        major_pairs = [
            (fcode, mcode, mname)
            for fcode, fdata in FACULTIES.items()
            for mcode, mname in fdata['majors'].items()
        ]
        Student.objects.bulk_create(
            [Student(
                user=u, student_id=u.username, name=fake.name(),
                major_code=(mp := random.choice(major_pairs))[1],
                major_name=mp[2], faculty=mp[0],
                grade=random.choice([2022, 2023, 2024, 2025]),
                total_credit=0,
             ) for u in student_users],
            batch_size=BATCH_SIZE
        )
        all_students = list(Student.objects.all())

        # 6. Courses (from CSV, or fallback)
        print("[6/12] Saving Courses...")
        csv_path = os.path.join(os.path.dirname(__file__), 'courses_real.csv')
        course_objs = []
        schedules = [
            'Mon/Wed 08:00-09:50', 'Tue/Thu 10:00-11:50',
            'Mon/Wed 14:00-15:50', 'Fri 08:00-11:50',
        ]
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    course_objs.append(Course(
                        code=row['code'], name=row['name'],
                        teacher=random.choice(all_teachers),
                        semester=random.choice(all_semesters),
                        credit=int(row.get('credit', 3)),
                        schedule=random.choice(schedules),
                        venue=random.choice(all_venues),
                        faculty=row.get('faculty', 'FST'),
                    ))
        else:
            for i in range(300):
                course_objs.append(Course(
                    code=f"COMP{3000+i}", name=f"Course {i}",
                    teacher=random.choice(all_teachers),
                    semester=random.choice(all_semesters),
                    credit=random.choice([2, 3, 4]),
                    schedule=random.choice(schedules),
                    venue=random.choice(all_venues), faculty='FST',
                ))
        Course.objects.bulk_create(course_objs, batch_size=BATCH_SIZE)
        all_courses = list(Course.objects.all())

        # 7. Enrollments  (N_STUDENTS × N_ENROLL_PER_STUDENT ≥ 50 000)
        print(f"[7/12] Saving Enrollments ({N_STUDENTS} × {N_ENROLL_PER_STUDENT})...")
        enrollment_objs = []
        k = min(N_ENROLL_PER_STUDENT, len(all_courses))
        now = timezone.now()
        for s in all_students:
            for c in random.sample(all_courses, k=k):
                enrollment_objs.append(
                    Enrollment(student=s, course=c, enrolled_at=now, status='active')
                )
        Enrollment.objects.bulk_create(enrollment_objs, batch_size=BATCH_SIZE)

        # 8. Assignments  (N_ASSIGN_PER_COURSE per course ≥ 6 000 total)
        print(f"[8/12] Saving Assignments ({N_ASSIGN_PER_COURSE} per course)...")
        assignment_objs = []
        priorities = ['high', 'medium', 'low']
        for c in all_courses:
            for i in range(N_ASSIGN_PER_COURSE):
                days_offset = random.randint(7, 120)
                assignment_objs.append(Assignment(
                    course=c,
                    title=f"{c.code} {template_text(ASSIGNMENT_TITLES, i)}",
                    description=ASSIGNMENT_DESCRIPTIONS[i % len(ASSIGNMENT_DESCRIPTIONS)],
                    deadline=now + timedelta(days=days_offset),
                    priority=random.choice(priorities),
                    created_at=now,
                ))
        Assignment.objects.bulk_create(assignment_objs, batch_size=BATCH_SIZE)

        # 9. Events
        print(f"[9/12] Saving Events ({N_EVENTS})...")
        event_objs = []
        event_base_date = now.replace(day=1, hour=8, minute=0, second=0, microsecond=0)
        for i in range(N_EVENTS):
            start, end = event_times_for_index(event_base_date, i)
            event_objs.append(Event(
                title=template_text(EVENT_TITLES, i),
                description=EVENT_DESCRIPTIONS[i % len(EVENT_DESCRIPTIONS)],
                start_time=start,
                end_time=end,
                venue=random.choice(all_venues),
                category=random.choice(all_categories),
                organizer=fake.name(),
                is_public=True,
                created_by=random.choice(all_users),
            ))
        Event.objects.bulk_create(event_objs, batch_size=BATCH_SIZE)

        # 10. CustomTags  (one per user → 5 000+)
        print("[10/12] Saving CustomTags...")
        tag_names  = ['Urgent', 'Important', 'Review', 'Personal', 'Work']
        tag_colors = ['#FF0000', '#F5A623', '#7ED321', '#5B8DEF', '#BD10E0']
        CustomTag.objects.bulk_create(
            [CustomTag(user=u,
                       name=random.choice(tag_names),
                       color=random.choice(tag_colors))
             for u in all_users],
            batch_size=BATCH_SIZE
        )

        # 11. Notifications  (N_NOTIF_EXTRA manual + trigger-generated ones)
        print(f"[11/12] Saving Notifications ({N_NOTIF_EXTRA} extra)...")
        notif_types = ['announcement', 'system']
        notif_objs  = []
        for i in range(N_NOTIF_EXTRA):
            notif_objs.append(Notification(
                user=random.choice(all_users),
                title=template_text(NOTIFICATION_TITLES, i),
                content=NOTIFICATION_CONTENTS[i % len(NOTIFICATION_CONTENTS)],
                type=random.choice(notif_types),
                is_read=random.choice([True, False]),
                created_at=now - timedelta(days=random.randint(0, 180)),
            ))
        Notification.objects.bulk_create(notif_objs, batch_size=BATCH_SIZE)

        # 12. Feedback  (N_FEEDBACK entries)
        print(f"[12/12] Saving Feedbacks ({N_FEEDBACK})...")
        fb_statuses = ['pending', 'resolved', 'rejected']
        Feedback.objects.bulk_create(
            [Feedback(
                user=random.choice(all_users),
                title=template_text(FEEDBACK_TITLES, i),
                content=FEEDBACK_CONTENTS[i % len(FEEDBACK_CONTENTS)],
                status=random.choice(fb_statuses),
                created_at=now - timedelta(days=random.randint(0, 365)),
             ) for i in range(N_FEEDBACK)],
            batch_size=BATCH_SIZE
        )

    print("Successfully populated database!")

def main():
    save_to_database()

if __name__ == '__main__':
    # 独立运行时的 Django 环境配置
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bnbu_calendar.settings')
    django.setup()
    main()
