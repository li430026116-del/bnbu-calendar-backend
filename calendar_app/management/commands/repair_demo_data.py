import random
import re
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from calendar_app.models import (
    Assignment,
    Category,
    Course,
    Enrollment,
    Event,
    Feedback,
    Notification,
    Semester,
    Student,
    Teacher,
    User,
    Venue,
)


TARGET_COUNT = 50001
BATCH_SIZE = 2000

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

DEMO_COURSES = [
    ('COMP3013', 'Database Systems', 'FST', 3, 'Mon/Wed 10:00-11:50'),
    ('ENGL1101', 'Academic Writing', 'FBM', 3, 'Tue/Thu 09:00-10:50'),
    ('BUSN2201', 'Business Analytics', 'FBM', 3, 'Mon/Wed 14:00-15:50'),
    ('COMP1010', 'Python Programming', 'FST', 4, 'Tue/Thu 14:00-15:50'),
    ('RESM2001', 'Research Methodology', 'FST', 3, 'Fri 09:00-11:50'),
    ('MKTG2001', 'Marketing Management', 'FBM', 3, 'Mon/Wed 16:00-17:50'),
    ('AI3001', 'Artificial Intelligence', 'FST', 4, 'Tue/Thu 16:00-17:50'),
    ('PMGT2101', 'Project Management', 'FBM', 3, 'Fri 14:00-16:50'),
]


def clean_display_title(value):
    if not value:
        return value
    return re.sub(r'(?:\s*(?:#\d{3,}|\[DEMO-\d+\]))+\s*$', '', str(value)).strip()


def chunked(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]


class Command(BaseCommand):
    help = 'Repair demo display text and ensure Event/Notification contain more than 50,000 records without deleting data.'

    def add_arguments(self, parser):
        parser.add_argument('--target', type=int, default=TARGET_COUNT)
        parser.add_argument('--batch-size', type=int, default=BATCH_SIZE)
        parser.add_argument(
            '--clean-display-titles',
            action='store_true',
            help='Remove demo numbering from existing display titles without deleting data.',
        )

    def handle(self, *args, **options):
        random.seed(42)
        self.target_count = options['target']
        self.batch_size = options['batch_size']
        self.event_base_date = timezone.now().replace(day=1, hour=8, minute=0, second=0, microsecond=0)
        self.hour_slots = [8, 9, 10, 11, 14, 15, 16, 18, 19, 20]

        current_event_count = Event.objects.count()
        self.stdout.write('Starting demo data repair...')
        self.stdout.write(f'Current Event count: {current_event_count}')

        users = list(User.objects.all().only('id'))
        if not users:
            user = User.objects.create_user(
                username='demo_student',
                email='demo_student@mail.bnbu.edu.cn',
                password='password123',
                role='student',
            )
            users = [user]

        venues = list(Venue.objects.all().only('id'))
        categories = list(Category.objects.all().only('id'))
        now = timezone.now()

        repaired_existing = 0
        created_events = 0
        created_notifications = 0

        with transaction.atomic():
            self.stdout.write('Repairing Event text and date distribution...')
            repaired_existing += self.repair_events(current_event_count)
            repaired_existing += self.repair_notifications()
            repaired_existing += self.repair_assignments()
            repaired_existing += self.repair_feedback()
            if options['clean_display_titles']:
                repaired_existing += self.clean_existing_display_titles()

            created_events = self.ensure_events(users, venues, categories, now)
            created_notifications = self.ensure_notifications(users, now)
            created_enrollments = self.ensure_student_enrollments(now)

        self.stdout.write(f'Final Event count: {Event.objects.count()}')
        self.stdout.write(f'Final Notification count: {Notification.objects.count()}')
        self.stdout.write(f'Feedback count: {Feedback.objects.count()}')
        self.stdout.write(f'Assignment count: {Assignment.objects.count()}')
        self.stdout.write(f'Repaired existing records: {repaired_existing}')
        self.stdout.write(f'Created new Event records: {created_events}')
        self.stdout.write(f'Created new Notification records: {created_notifications}')
        self.stdout.write(f'Created new Enrollment records: {created_enrollments}')
        self.stdout.write(f'Event count: {Event.objects.count()}')
        self.stdout.write(f'Notification count: {Notification.objects.count()}')
        self.stdout.write('Done. Event dates were redistributed without deleting existing data.')
        self.stdout.write('Done. Database was repaired without deleting existing data.')

    def event_times_for_index(self, index):
        day_offset = index % 365
        hour = self.hour_slots[index % len(self.hour_slots)]
        start_time = self.event_base_date + timedelta(days=day_offset)
        start_time = start_time.replace(hour=hour, minute=0, second=0, microsecond=0)
        return start_time, start_time + timedelta(hours=1)

    def repair_events(self, current_event_count):
        total = 0
        buffer = []
        queryset = Event.objects.order_by('id').only(
            'id', 'title', 'description', 'start_time', 'end_time'
        ).iterator(chunk_size=self.batch_size)
        for index, event in enumerate(queryset):
            start_time, end_time = self.event_times_for_index(index)
            event.title = EVENT_TITLES[index % len(EVENT_TITLES)]
            event.description = EVENT_DESCRIPTIONS[index % len(EVENT_DESCRIPTIONS)]
            event.start_time = start_time
            event.end_time = end_time
            buffer.append(event)
            if len(buffer) >= self.batch_size:
                Event.objects.bulk_update(
                    buffer,
                    ['title', 'description', 'start_time', 'end_time'],
                    batch_size=self.batch_size,
                )
                total += len(buffer)
                self.stdout.write(f'Event repair progress: {total} / {current_event_count}')
                buffer = []
        if buffer:
            Event.objects.bulk_update(
                buffer,
                ['title', 'description', 'start_time', 'end_time'],
                batch_size=self.batch_size,
            )
            total += len(buffer)
            self.stdout.write(f'Event repair progress: {total} / {current_event_count}')
        return total

    def repair_notifications(self):
        total = 0
        buffer = []
        queryset = Notification.objects.order_by('id').only('id', 'title', 'content').iterator(chunk_size=self.batch_size)
        for index, notification in enumerate(queryset):
            notification.title = NOTIFICATION_TITLES[index % len(NOTIFICATION_TITLES)]
            notification.content = NOTIFICATION_CONTENTS[index % len(NOTIFICATION_CONTENTS)]
            buffer.append(notification)
            if len(buffer) >= self.batch_size:
                Notification.objects.bulk_update(buffer, ['title', 'content'], batch_size=self.batch_size)
                total += len(buffer)
                buffer = []
        if buffer:
            Notification.objects.bulk_update(buffer, ['title', 'content'], batch_size=self.batch_size)
            total += len(buffer)
        return total

    def repair_assignments(self):
        total = 0
        buffer = []
        queryset = Assignment.objects.select_related('course').order_by('id').only(
            'id', 'title', 'description', 'course__code'
        ).iterator(chunk_size=self.batch_size)
        for index, assignment in enumerate(queryset):
            assignment.title = f'{assignment.course.code} {ASSIGNMENT_TITLES[index % len(ASSIGNMENT_TITLES)]}'
            assignment.description = ASSIGNMENT_DESCRIPTIONS[index % len(ASSIGNMENT_DESCRIPTIONS)]
            buffer.append(assignment)
            if len(buffer) >= self.batch_size:
                Assignment.objects.bulk_update(buffer, ['title', 'description'], batch_size=self.batch_size)
                total += len(buffer)
                buffer = []
        if buffer:
            Assignment.objects.bulk_update(buffer, ['title', 'description'], batch_size=self.batch_size)
            total += len(buffer)
        return total

    def repair_feedback(self):
        total = 0
        buffer = []
        queryset = Feedback.objects.order_by('id').only('id', 'title', 'content').iterator(chunk_size=self.batch_size)
        for index, feedback in enumerate(queryset):
            feedback.title = FEEDBACK_TITLES[index % len(FEEDBACK_TITLES)]
            feedback.content = FEEDBACK_CONTENTS[index % len(FEEDBACK_CONTENTS)]
            buffer.append(feedback)
            if len(buffer) >= self.batch_size:
                Feedback.objects.bulk_update(buffer, ['title', 'content'], batch_size=self.batch_size)
                total += len(buffer)
                buffer = []
        if buffer:
            Feedback.objects.bulk_update(buffer, ['title', 'content'], batch_size=self.batch_size)
            total += len(buffer)
        return total

    def ensure_events(self, users, venues, categories, now):
        current_count = Event.objects.count()
        missing = max(0, self.target_count - current_count)
        created = 0
        objects = []
        for offset in range(missing):
            sequence = current_count + offset
            start, end = self.event_times_for_index(sequence)
            objects.append(Event(
                title=EVENT_TITLES[sequence % len(EVENT_TITLES)],
                description=EVENT_DESCRIPTIONS[sequence % len(EVENT_DESCRIPTIONS)],
                start_time=start,
                end_time=end,
                venue=random.choice(venues) if venues else None,
                category=random.choice(categories) if categories else None,
                organizer='Academic Affairs Office',
                is_public=True,
                created_by=random.choice(users) if users else None,
            ))
            if len(objects) >= self.batch_size:
                Event.objects.bulk_create(objects, batch_size=self.batch_size)
                created += len(objects)
                objects = []
        if objects:
            Event.objects.bulk_create(objects, batch_size=self.batch_size)
            created += len(objects)
        return created

    def ensure_notifications(self, users, now):
        current_count = Notification.objects.count()
        missing = max(0, self.target_count - current_count)
        created = 0
        objects = []
        types = ['announcement', 'system', 'ddl_reminder']
        for offset in range(missing):
            sequence = current_count + offset
            objects.append(Notification(
                user=random.choice(users),
                title=NOTIFICATION_TITLES[sequence % len(NOTIFICATION_TITLES)],
                content=NOTIFICATION_CONTENTS[sequence % len(NOTIFICATION_CONTENTS)],
                type=types[sequence % len(types)],
                related_id=None,
                is_read=bool(sequence % 2),
                created_at=now - timedelta(days=random.randint(0, 365), minutes=random.randint(0, 1440)),
            ))
            if len(objects) >= self.batch_size:
                Notification.objects.bulk_create(objects, batch_size=self.batch_size)
                created += len(objects)
                objects = []
        if objects:
            Notification.objects.bulk_create(objects, batch_size=self.batch_size)
            created += len(objects)
        return created

    def clean_existing_display_titles(self):
        total = 0
        total += self.clean_model_title_field(Event, 'title')
        total += self.clean_model_title_field(Assignment, 'title')
        total += self.clean_model_title_field(Course, 'name')
        total += self.clean_model_title_field(Notification, 'title')
        total += self.clean_model_title_field(Feedback, 'title')
        self.stdout.write(f'Cleaned display titles: {total}')
        return total

    def clean_model_title_field(self, model, field_name):
        total = 0
        buffer = []
        queryset = model.objects.order_by('id').only('id', field_name).iterator(chunk_size=self.batch_size)
        for instance in queryset:
            original = getattr(instance, field_name, '')
            cleaned = clean_display_title(original)
            if cleaned != original:
                setattr(instance, field_name, cleaned)
                buffer.append(instance)
            if len(buffer) >= self.batch_size:
                model.objects.bulk_update(buffer, [field_name], batch_size=self.batch_size)
                total += len(buffer)
                buffer = []
        if buffer:
            model.objects.bulk_update(buffer, [field_name], batch_size=self.batch_size)
            total += len(buffer)
        return total

    def ensure_demo_courses(self):
        if Course.objects.count() >= 5:
            return list(Course.objects.all().order_by('id')[:8])

        semester = Semester.objects.order_by('-is_current', 'id').first()
        if not semester:
            today = timezone.now().date()
            semester = Semester.objects.create(
                name='Demo Semester',
                start_date=today,
                end_date=today + timedelta(days=120),
                is_current=True,
            )

        teacher = Teacher.objects.order_by('id').first()
        venue = Venue.objects.order_by('id').first()
        courses = []
        for code, name, faculty, credit, schedule in DEMO_COURSES:
            course, _ = Course.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': f'{name} provides practical learning activities for students.',
                    'teacher': teacher,
                    'semester': semester,
                    'credit': credit,
                    'schedule': schedule,
                    'venue': venue,
                    'faculty': faculty,
                    'max_students': 120,
                },
            )
            courses.append(course)
        return courses

    def ensure_student_enrollments(self, now):
        courses = self.ensure_demo_courses()
        if not courses:
            return 0

        created = 0
        for index, student in enumerate(Student.objects.order_by('id').iterator(chunk_size=self.batch_size)):
            if Enrollment.objects.filter(student=student).exists():
                continue

            course_count = min(len(courses), 3 + (index % 3))
            for course in courses[:course_count]:
                _, was_created = Enrollment.objects.get_or_create(
                    student=student,
                    course=course,
                    defaults={
                        'enrolled_at': now,
                        'status': 'active',
                    },
                )
                if was_created:
                    created += 1
        return created
