from rest_framework import serializers
from django.db import connection
from .models import (
    User, Student, Teacher, Semester, Venue, Category,
    Course, Assignment, Enrollment, Event, Notification,
    CustomTag, Feedback, AssignmentSubmission, PersonalTask
)

_EVENT_IMAGE_COLUMN_EXISTS = None


def event_image_column_exists():
    global _EVENT_IMAGE_COLUMN_EXISTS
    if _EVENT_IMAGE_COLUMN_EXISTS is None:
        try:
            with connection.cursor() as cursor:
                columns = [col.name for col in connection.introspection.get_table_description(cursor, 'events')]
            _EVENT_IMAGE_COLUMN_EXISTS = 'image' in columns
        except Exception:
            _EVENT_IMAGE_COLUMN_EXISTS = False
    return _EVENT_IMAGE_COLUMN_EXISTS

DOT_COLOR_MAP = {
    'Academic': '#5B8DEF',
    'Clubs':    '#F5A623',
    'Sports':   '#7ED321',
    'Arts':     '#BD10E0',
    'Career':   '#E6A23C',
}

# 1. User Serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']

# 2. Student Serializer
class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Student
        fields = ['id', 'user', 'student_id', 'name', 'major_code', 'major_name', 'faculty', 'grade', 'total_credit']

# 3. Teacher Serializer
class TeacherSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Teacher
        fields = ['id', 'user', 'teacher_id', 'name', 'faculty', 'title']

# 4. Semester Serializer
class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = '__all__'

# 5. Venue Serializer
class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__'

# 6. Category Serializer
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

# 7. Course Serializers
class CourseSerializer(serializers.ModelSerializer):
    teacher = serializers.SerializerMethodField(read_only=True)
    is_owner = serializers.SerializerMethodField()
    semester = serializers.CharField(source='semester.name', read_only=True)
    venue = serializers.CharField(source='venue.name', read_only=True)

    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='teacher',
        write_only=True,
        required=False,
        allow_null=True
    )
    semester_id = serializers.PrimaryKeyRelatedField(
        queryset=Semester.objects.all(),
        source='semester',
        write_only=True,
        required=True
    )
    venue_id = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.all(),
        source='venue',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Course
        fields = '__all__'

    def get_teacher(self, obj):
        if obj.teacher:
            return {
                "id": obj.teacher.id,
                "name": obj.teacher.name,
                "title": obj.teacher.title
            }
        return None

    def get_is_owner(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'is_superuser', False):
            return True
        return bool(obj.teacher and obj.teacher.user_id == user.id)

class CourseListSerializer(serializers.ModelSerializer):
    teacher = serializers.CharField(source='teacher.name', read_only=True)
    semester = serializers.CharField(source='semester.name', read_only=True)
    venue = serializers.CharField(source='venue.name', read_only=True)
    teacher_id = serializers.IntegerField(source='teacher.id', read_only=True, allow_null=True)
    semester_id = serializers.IntegerField(source='semester.id', read_only=True)
    venue_id = serializers.IntegerField(source='venue.id', read_only=True, allow_null=True)
    enrolled_count = serializers.IntegerField(read_only=True)
    is_owner = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'code', 'name', 'teacher', 'teacher_id', 'is_owner', 'schedule', 'faculty', 'credit', 'max_students', 'semester', 'semester_id', 'venue', 'venue_id', 'enrolled_count']

    def get_is_owner(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'is_superuser', False):
            return True
        return bool(obj.teacher and obj.teacher.user_id == user.id)

# 8. Assignment Serializer
class AssignmentSerializer(serializers.ModelSerializer):
    course_info = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = '__all__'

    def get_course_info(self, obj):
        return {
            "code": obj.course.code,
            "name": obj.course.name
        }

    def get_submission(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False) or not hasattr(user, 'student_profile'):
            return None
        submission = AssignmentSubmission.objects.filter(
            assignment=obj,
            student=user.student_profile,
        ).first()
        if not submission:
            return None
        return AssignmentSubmissionSerializer(submission, context=self.context).data

class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    assignment_id = serializers.IntegerField(source='assignment.id', read_only=True)
    file_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = AssignmentSubmission
        fields = ['id', 'assignment_id', 'file_name', 'file_url', 'file', 'submitted_at']

    def get_file_name(self, obj):
        return obj.file.name.split('/')[-1] if obj.file else ''

    def get_file_url(self, obj):
        if not obj.file:
            return ''
        request = self.context.get('request')
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url


class PersonalTaskSerializer(serializers.ModelSerializer):
    owner = serializers.IntegerField(source='owner.id', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    source_task = serializers.IntegerField(source='source_task.id', read_only=True, allow_null=True)

    class Meta:
        model = PersonalTask
        fields = [
            'id', 'owner', 'owner_username', 'title', 'description', 'due_at',
            'priority', 'is_completed', 'share_token', 'source_task',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'owner', 'owner_username', 'share_token', 'source_task', 'created_at', 'updated_at']

# 9. Enrollment Serializer
class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'

# 10. Event Serializer
class EventSerializer(serializers.ModelSerializer):
    venue = serializers.CharField(source='venue.name', read_only=True)
    category_info = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    venue_id = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.all(),
        source='venue',
        write_only=True,
        required=False,
        allow_null=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Event
        fields = '__all__'

    def get_category_info(self, obj):
        if obj.category:
            return {
                "name": obj.category.name,
                "color": obj.category.color
            }
        return None

    def get_image_url(self, obj):
        if not event_image_column_exists():
            return ''
        request = self.context.get('request')
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return ''

# 11. Notification Serializer
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

# 12. CustomTag Serializer
class CustomTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomTag
        fields = '__all__'

# 13. Feedback Serializer
class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'

# 14. EventListSerializer — front-end events list (renamed fields + computed fields)
class EventListSerializer(serializers.ModelSerializer):
    desc     = serializers.CharField(source='description', default='')
    time     = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    dotColor = serializers.SerializerMethodField()
    day      = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    venue_id = serializers.IntegerField(source='venue.id', read_only=True, allow_null=True)
    category_id = serializers.IntegerField(source='category.id', read_only=True, allow_null=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'desc', 'time', 'location',
            'category', 'dotColor', 'day',
            'start_time', 'end_time', 'venue_id', 'category_id', 'image_url', 'is_subscribed',
        ]

    def get_time(self, obj):
        s, e = obj.start_time, obj.end_time
        return f"{s.strftime('%b %d')} · {s.strftime('%H:%M')}-{e.strftime('%H:%M')}"

    def get_location(self, obj):
        return obj.venue.name if obj.venue else ''

    def get_category(self, obj):
        return obj.category.name if obj.category else ''

    def get_dotColor(self, obj):
        if obj.category and obj.category.color:
            return obj.category.color
        return '#d93025'

    def get_image_url(self, obj):
        if not event_image_column_exists():
            return ''
        request = self.context.get('request')
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return ''

    def get_day(self, obj):
        # Python weekday(): Mon=0 … Sun=6  →  frontend: Sun=0, Sat=6
        return (obj.start_time.weekday() + 1) % 7

    def get_is_subscribed(self, obj):
        return obj.id in self.context.get('subscribed_ids', set())


# 16. CalendarEventSerializer for FullCalendar
class CalendarEventSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    color = serializers.CharField(required=False)
    type = serializers.CharField() # ddl / event / custom
    course_name = serializers.CharField(required=False)
    is_completed = serializers.BooleanField(default=False)
    priority = serializers.CharField(required=False)
