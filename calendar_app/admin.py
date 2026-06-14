from django.contrib import admin
from .models import (
    User, Student, Teacher, Semester, Venue, Category,
    Course, Assignment, Enrollment, Event, Notification,
    CustomTag, Feedback
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'is_staff']
    list_filter = ['role', 'is_staff']
    search_fields = ['username', 'email']

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'name', 'major_name', 'grade']
    search_fields = ['student_id', 'name']

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['teacher_id', 'name', 'faculty', 'title']
    search_fields = ['teacher_id', 'name']

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_current']

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'building', 'type', 'capacity']
    list_filter = ['type', 'building']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_cn', 'color']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'teacher', 'semester']
    search_fields = ['code', 'name']
    list_filter = ['semester', 'faculty']

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'deadline', 'priority']
    list_filter = ['priority', 'deadline']
    search_fields = ['title', 'course__code']

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'status', 'enrolled_at']
    list_filter = ['status']
    search_fields = ['student__student_id', 'course__code']
    list_per_page = 50

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_time', 'end_time', 'venue', 'is_public']
    list_filter = ['is_public', 'category']
    search_fields = ['title']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read']
    search_fields = ['title']
    list_per_page = 50

@admin.register(CustomTag)
class CustomTagAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'color']

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['title']
