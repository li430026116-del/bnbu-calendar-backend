from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    avatar_url = models.URLField(blank=True, null=True, default='/static/default.png')
    email_notifications = models.BooleanField(default=True)
    dark_mode = models.BooleanField(default=False)
    auto_sync = models.BooleanField(default=True)

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    major_code = models.CharField(max_length=10)
    major_name = models.CharField(max_length=100)
    faculty = models.CharField(max_length=10)
    grade = models.IntegerField()
    total_credit = models.IntegerField(default=0)

    class Meta:
        db_table = 'students'

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    teacher_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    faculty = models.CharField(max_length=10)
    title = models.CharField(max_length=50)

    class Meta:
        db_table = 'teachers'

class Semester(models.Model):
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        db_table = 'semesters'

class Venue(models.Model):
    TYPE_CHOICES = [
        ('classroom', 'Classroom'),
        ('lab', 'Lab'),
        ('auditorium', 'Auditorium'),
        ('gym', 'Gym'),
        ('library', 'Library'),
        ('meeting', 'Meeting Room'),
        ('online', 'Online'),
    ]
    name = models.CharField(max_length=50)
    building = models.CharField(max_length=20)
    capacity = models.IntegerField(default=50)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='classroom')

    class Meta:
        db_table = 'venues'

class Category(models.Model):
    name = models.CharField(max_length=50)
    name_cn = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=10, default='#5B8DEF')
    icon = models.CharField(max_length=30, blank=True)

    class Meta:
        db_table = 'categories'

class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, related_name='courses')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='courses')
    credit = models.IntegerField(default=3)
    schedule = models.CharField(max_length=100)
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, related_name='courses')
    faculty = models.CharField(max_length=10)
    max_students = models.IntegerField(default=120)

    class Meta:
        db_table = 'courses'

class Assignment(models.Model):
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    deadline = models.DateTimeField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    created_at = models.DateTimeField(default=timezone.now)
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'assignments'
        indexes = [
            models.Index(fields=['course', 'deadline']),
            models.Index(fields=['deadline']),
        ]


class PersonalTask(models.Model):
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_at = models.DateTimeField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_completed = models.BooleanField(default=False)
    share_token = models.CharField(max_length=32, unique=True, null=True, blank=True, db_index=True)
    source_task = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='imported_tasks',
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'personal_tasks'
        indexes = [
            models.Index(fields=['owner', 'due_at']),
            models.Index(fields=['due_at']),
        ]

class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assignment_submissions')
    file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'assignment_submissions'
        unique_together = ['assignment', 'student']
        indexes = [
            models.Index(fields=['assignment', 'student']),
        ]

class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('dropped', 'Dropped'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    class Meta:
        db_table = 'enrollments'
        unique_together = ['student', 'course']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['course']),
        ]

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, related_name='events')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='events')
    organizer = models.CharField(max_length=100, blank=True)
    is_public = models.BooleanField(default=True)
    image = models.ImageField(upload_to='event_images/', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_events')

    class Meta:
        db_table = 'events'
        indexes = [
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['category']),
        ]

class Notification(models.Model):
    TYPE_CHOICES = [
        ('ddl_reminder', 'DDL Reminder'),
        ('announcement', 'Announcement'),
        ('system', 'System'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    related_id = models.IntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
        ]

class CustomTag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_tags')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=10, default='#5B8DEF')

    class Meta:
        db_table = 'custom_tags'

class Feedback(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'feedback'

class EventSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_subscriptions')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='subscriptions')
    subscribed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'event_subscriptions'
        unique_together = ['user', 'event']


class ShareLink(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='share_links')
    token = models.CharField(max_length=8, unique=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'share_links'
