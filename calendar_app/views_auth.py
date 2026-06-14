from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
import logging
from django.db.models import Count, Q
from django.utils import timezone
from .models import User, Student, Teacher, Course, Enrollment
from .api_response import ok, fail

logger = logging.getLogger(__name__)

PREFERENCE_FIELDS = ['email_notifications', 'dark_mode', 'auto_sync']
DEFAULT_STUDENT_COURSE_CODES = ['UCLC1033', 'COMP3013']


def enroll_student_in_default_courses(student):
    warnings = []

    for course_code in DEFAULT_STUDENT_COURSE_CODES:
        course = (
            Course.objects
            .annotate(active_enrollment_count=Count(
                'enrollments',
                filter=Q(enrollments__status='active'),
            ))
            .filter(code=course_code)
            .first()
        )

        if not course:
            warning = f'Default course {course_code} does not exist; skipped auto enrollment.'
            logger.warning(warning)
            warnings.append(warning)
            continue

        already_enrolled = Enrollment.objects.filter(student=student, course=course).exists()
        if (
            not already_enrolled
            and course.max_students is not None
            and course.active_enrollment_count >= course.max_students
        ):
            warning = f'Default course {course_code} is full; skipped auto enrollment.'
            logger.warning(warning)
            warnings.append(warning)
            continue

        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            course=course,
            defaults={
                'enrolled_at': timezone.now(),
                'status': 'active',
            }
        )
        if not created and enrollment.status != 'active':
            enrollment.status = 'active'
            enrollment.save(update_fields=['status'])

    return warnings

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        role = 'student'

        if not username or not password:
            return fail('Username and password are required', code=400, status_code=400)

        if User.objects.filter(username=username).exists():
            return fail('Username already exists', code=400, status_code=400)

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            role=role
        )

        if role == 'student':
            student = Student.objects.create(
                user=user,
                student_id=username,
                name=username,
                grade=2024,
                faculty='FST',
                major_code='CST',
                major_name='Computer Science'
            )
            warnings = enroll_student_in_default_courses(student)
        elif role == 'teacher':
            Teacher.objects.create(
                user=user,
                teacher_id=username,
                name=username,
                faculty='FST',
                title='Lecturer'
            )
            warnings = []
        else:
            warnings = []

        token, _ = Token.objects.get_or_create(user=user)

        return ok({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            },
            'warnings': warnings
        })

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        login_type = (
            request.data.get('login_type') or
            request.data.get('role') or
            request.data.get('portal_type')
        )

        user = authenticate(username=username, password=password)
        if not user:
            return fail('Invalid credentials', code=401, status_code=401)

        if login_type:
            login_type = str(login_type).strip().lower()
            if login_type == 'administrator':
                login_type = 'admin'
            if login_type != user.role:
                msg = 'No admin permission' if login_type == 'admin' else 'Login portal does not match account role'
                return fail(msg, code=403, status_code=403)

        token, _ = Token.objects.get_or_create(user=user)

        return ok({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        })

class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'avatar_url': user.avatar_url,
            'preferences': {
                'email_notifications': user.email_notifications,
                'dark_mode': user.dark_mode,
                'auto_sync': user.auto_sync,
            }
        }
        return ok(data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({'code': 200, 'msg': '已成功登出'})


class PreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return ok({
            'email_notifications': user.email_notifications,
            'dark_mode': user.dark_mode,
            'auto_sync': user.auto_sync,
        })

    def put(self, request):
        user = request.user
        for field in PREFERENCE_FIELDS:
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        return ok({
            'email_notifications': user.email_notifications,
            'dark_mode': user.dark_mode,
            'auto_sync': user.auto_sync,
        }, msg='settings updated')

    def patch(self, request):
        return self.put(request)
