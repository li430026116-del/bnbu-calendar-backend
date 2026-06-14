import uuid
from collections import defaultdict
from icalendar import Calendar, Event as ICalEvent
from django.http import HttpResponse
from rest_framework import viewsets, status, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView, exception_handler as drf_exception_handler
from django.db.models import Q, Count, F
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from datetime import timedelta
from datetime import datetime, time
from django_filters.rest_framework import DjangoFilterBackend
from django.http import JsonResponse
from .models import (
    User, Student, Teacher, Course, Assignment, Enrollment,
    Event, EventSubscription, Notification, Category, Venue, Semester, CustomTag,
    ShareLink, AssignmentSubmission, PersonalTask,
)
from .serializers import (
    CourseSerializer, CourseListSerializer, EnrollmentSerializer,
    AssignmentSerializer, EventSerializer, EventListSerializer,
    NotificationSerializer, CalendarEventSerializer,
    StudentSerializer, TeacherSerializer, AssignmentSubmissionSerializer,
    PersonalTaskSerializer, event_image_column_exists,
)
from .permissions import IsStudent, IsAdmin, IsEduAdmin, IsTeacher, is_admin_user
from .api_response import ok, fail

PERSONAL_TASK_COLORS = {
    'high': '#D0021B',
    'medium': '#F5A623',
    'low': '#7ED321',
}


def get_personal_task_color(priority):
    return PERSONAL_TASK_COLORS.get(priority, '#F5A623')


def build_personal_task_urls(request, task):
    token = task.share_token
    origin = f"{'https' if request.is_secure() else 'http'}://{request.get_host()}"
    dashboard_url = f'{origin}/dashboard.html?importTask={token}'
    return {
        'share_url': dashboard_url,
        'import_url': dashboard_url,
        'ics_url': f'{origin}/api/personal-tasks/shared/{token}/ical/',
    }


def build_single_task_ical(task):
    cal = Calendar()
    cal.add('PRODID', '-//BNBU Calendar Personal Task//bnbu.edu.cn//')
    cal.add('VERSION', '2.0')
    cal.add('CALSCALE', 'GREGORIAN')
    cal.add('X-WR-CALNAME', 'BNBU Personal Task')

    ev = ICalEvent()
    ev.add('UID', f'personal-task-{task.id}@bnbu.edu.cn')
    ev.add('SUMMARY', f'[Task] {task.title}')
    ev.add('DTSTART', task.due_at)
    ev.add('DTEND', task.due_at + timedelta(hours=1))
    desc_parts = [f'Priority: {task.priority}']
    if task.description:
        desc_parts.append(task.description)
    ev.add('DESCRIPTION', '\n'.join(desc_parts))
    cal.add_component(ev)
    return cal

def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        detail = response.data
        if isinstance(detail, dict) and 'detail' in detail:
            msg = str(detail['detail'])
        elif isinstance(detail, list):
            msg = '; '.join(str(e) for e in detail)
        else:
            msg = str(detail)
        response.data = {'code': response.status_code, 'msg': msg}
    return response

def index(request):
    return JsonResponse({
        "project": "bnbu_calendar",
        "status": "running",
        "endpoints": [
            "/admin/",
            "/api/auth/register/",
            "/api/auth/login/",
            "/api/auth/me/"
        ]
    })

# 1. CourseViewSet
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related('teacher', 'semester', 'venue').annotate(
        enrolled_count=Count('enrollments', filter=Q(enrollments__status='active'))
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['semester', 'faculty']
    search_fields = ['name', 'code']

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        return CourseSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [IsTeacher()]
        elif self.action == 'destroy':
            return [IsTeacher()]
        return [AllowAny()]

    def get_queryset(self):
        return Course.objects.select_related('teacher__user', 'semester', 'venue').annotate(
            enrolled_count=Count('enrollments', filter=Q(enrollments__status='active'))
        )

    def _can_manage_course(self, request, course):
        if getattr(request.user, 'is_superuser', False):
            return True
        teacher = getattr(request.user, 'teacher_profile', None)
        return bool(
            getattr(request.user, 'role', None) == 'teacher'
            and teacher
            and course.teacher_id == teacher.id
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        # 嵌套 assignments 列表
        assignments = instance.assignments.all()
        data['assignments'] = AssignmentSerializer(assignments, many=True, context={'request': request}).data
        return ok(data)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        raw = response.data

        return ok({
            "total": raw.get("count", 0),
            "page": 1,
            "page_size": len(raw.get("results", [])),
            "results": raw.get("results", [])
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        save_kwargs = {}
        if getattr(request.user, 'role', None) == 'teacher' and not request.user.is_superuser:
            teacher = getattr(request.user, 'teacher_profile', None)
            if not teacher:
                return fail('Teacher profile not found', code=403, status_code=403)
            save_kwargs['teacher'] = teacher
        instance = serializer.save(**save_kwargs)
        return ok(self.get_serializer(instance).data, status_code=201)

    def update(self, request, *args, **kwargs):
        if not self._can_manage_course(request, self.get_object()):
            return fail('Cannot manage another teacher course', code=403, status_code=403)
        response = super().update(request, *args, **kwargs)
        return ok(response.data)

    def perform_update(self, serializer):
        if getattr(self.request.user, 'role', None) == 'teacher' and not self.request.user.is_superuser:
            serializer.save(teacher=self.request.user.teacher_profile)
        else:
            serializer.save()

    def destroy(self, request, *args, **kwargs):
        if not self._can_manage_course(request, self.get_object()):
            return fail('Cannot manage another teacher course', code=403, status_code=403)
        super().destroy(request, *args, **kwargs)
        return ok({})

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        course = self.get_object()
        enrollments = (
            Enrollment.objects
            .filter(course=course)
            .select_related('student__user')
            .order_by('student__name')
        )
        results = []
        for enrollment in enrollments:
            student = enrollment.student
            results.append({
                'id': student.id,
                'student_id': student.student_id,
                'name': student.name,
                'email': student.user.email if student.user else '',
                'major_name': student.major_name,
                'faculty': student.faculty,
                'grade': student.grade,
                'enrolled_at': enrollment.enrolled_at,
                'status': enrollment.status,
            })
        return ok(results)

# 2. EnrollmentViewSet
class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if not hasattr(request.user, 'student_profile'):
            return fail('只有学生才能选课', code=403, status_code=403)

        student = request.user.student_profile
        course_id = request.data.get('course_id')

        if not course_id:
            return fail('course_id 是必填项', code=400, status_code=400)

        if Enrollment.objects.filter(student=student, course_id=course_id).exists():
            return fail('已选修该课程', code=400, status_code=400)

        enrollment = Enrollment.objects.create(
            student=student,
            course_id=course_id,
            enrolled_at=timezone.now(),
            status='active'
        )

        return ok(EnrollmentSerializer(enrollment).data, status_code=201)

    @action(detail=False, methods=['get'])
    def my(self, request):
        if not hasattr(request.user, 'student_profile'):
            return fail('只有学生才有选课记录', code=403, status_code=403)

        student = request.user.student_profile
        enrollments = Enrollment.objects.filter(student=student)
        serializer = self.get_serializer(enrollments, many=True)
        return ok(serializer.data)

# 3. AssignmentViewSet
class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsTeacher()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == 'teacher':
            return Assignment.objects.select_related('course__teacher__user').all()
        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        course_id = request.data.get('course') or request.data.get('course_id')
        if getattr(request.user, 'role', None) == 'teacher' and not request.user.is_superuser:
            teacher = getattr(request.user, 'teacher_profile', None)
            if not teacher or not Course.objects.filter(id=course_id, teacher=teacher).exists():
                return fail('Cannot manage assignments for another teacher course', code=403, status_code=403)
        response = super().create(request, *args, **kwargs)
        return ok(response.data, status_code=201)

    def perform_update(self, serializer):
        if getattr(self.request.user, 'role', None) == 'teacher' and not self.request.user.is_superuser:
            course = serializer.validated_data.get('course') or serializer.instance.course
            if course.teacher_id != self.request.user.teacher_profile.id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Cannot manage assignments for another teacher course')
        serializer.save()

    @action(detail=False, methods=['get'])
    def my(self, request):
        if not hasattr(request.user, 'student_profile'):
            return Response({'code': 403, 'msg': '只有学生才有作业记录'}, status=status.HTTP_403_FORBIDDEN)
        student = request.user.student_profile
        status_filter = request.query_params.get('status')
        course_id = request.query_params.get('course_id')
        
        # 这里的 Assignment 并没有 status 字段，假设需要结合完成逻辑或简单返回
        # 暂时返回学生所选课程的所有作业
        queryset = Assignment.objects.filter(course__enrollments__student=student)
        
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        sort = request.query_params.get('sort', 'deadline')
        queryset = queryset.order_by(sort)
        
        return ok(AssignmentSerializer(queryset, many=True).data)

    @action(detail=True, methods=['post', 'patch'])
    def complete(self, request, pk=None):
        assignment = self.get_object()
        if assignment.is_completed:
            return Response({'code': 400, 'msg': 'Assignment already completed'}, status=status.HTTP_400_BAD_REQUEST)
        assignment.is_completed = True
        assignment.save(update_fields=['is_completed'])
        # MySQL trigger after_assignment_complete handles credit update.
        # Replicate in Python for SQLite / non-MySQL environments.
        # Use subquery to avoid duplicate rows from JOIN inflating the update.
        from django.db import connection
        if connection.vendor != 'mysql':
            credit = assignment.course.credit
            student_ids = list(
                Student.objects.filter(
                    enrollments__course=assignment.course,
                    enrollments__status='active',
                ).values_list('id', flat=True).distinct()
            )
            Student.objects.filter(id__in=student_ids).update(
                total_credit=F('total_credit') + credit
            )
        return Response({'code': 200, 'msg': 'Assignment marked as completed', 'is_completed': True})

    @action(detail=True, methods=['post'])
    def uncomplete(self, request, pk=None):
        assignment = self.get_object()
        assignment.is_completed = False
        assignment.save(update_fields=['is_completed'])
        data = AssignmentSerializer(assignment).data
        data['status'] = 'pending'
        return Response({
            'code': 0,
            'msg': 'Assignment marked as incomplete',
            'data': data,
        })

    @action(detail=True, methods=['get', 'post', 'delete'], url_path='submission', parser_classes=[MultiPartParser, FormParser])
    def submission(self, request, pk=None):
        assignment = self.get_object()
        if not hasattr(request.user, 'student_profile'):
            return Response({'code': 403, 'msg': 'Only students can submit assignments'}, status=status.HTTP_403_FORBIDDEN)

        student = request.user.student_profile
        is_enrolled = Enrollment.objects.filter(
            student=student,
            course=assignment.course,
            status='active',
        ).exists()
        if not is_enrolled:
            return Response({'code': 403, 'msg': 'You are not enrolled in this course'}, status=status.HTTP_403_FORBIDDEN)

        submission = AssignmentSubmission.objects.filter(assignment=assignment, student=student).first()
        
        if request.method.lower() == 'delete':
            if not submission:
                return Response({
                    'code': 0,
                    'msg': 'No submission to remove',
                    'data': None,
                })

            if submission.file:
                submission.file.delete(save=False)

            submission.delete()

            return Response({
                'code': 0,
                'msg': 'Submission removed successfully',
                'data': None,
            })

        if request.method.lower() == 'get':
            if not submission:
                return Response({'code': 0, 'msg': 'No submission yet', 'data': None})
            return Response({
                'code': 0,
                'msg': 'ok',
                'data': AssignmentSubmissionSerializer(submission, context={'request': request}).data,
            })

        upload_file = request.FILES.get('file')
        if not upload_file:
            return Response({'code': 400, 'msg': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        if submission:
            submission.file = upload_file
            submission.submitted_at = timezone.now()
            submission.save(update_fields=['file', 'submitted_at'])
        else:
            submission = AssignmentSubmission.objects.create(
                assignment=assignment,
                student=student,
                file=upload_file,
            )

        return Response({
            'code': 0,
            'msg': 'Submission uploaded successfully',
            'data': AssignmentSubmissionSerializer(submission, context={'request': request}).data,
        })


class PersonalTaskViewSet(viewsets.ModelViewSet):
    serializer_class = PersonalTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['shared', 'ical']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return PersonalTask.objects.filter(owner=self.request.user).order_by('due_at', '-created_at')

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return ok(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(owner=request.user)
        return ok(self.get_serializer(task).data, status_code=201)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return ok(response.data)

    def perform_update(self, serializer):
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        return ok(response.data)

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return ok({})

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        task = self.get_object()
        if not task.share_token:
            token = uuid.uuid4().hex
            while PersonalTask.objects.filter(share_token=token).exists():
                token = uuid.uuid4().hex
            task.share_token = token
            task.save(update_fields=['share_token', 'updated_at'])
        return ok(build_personal_task_urls(request, task), status_code=201)

    @action(detail=False, methods=['get'], url_path=r'shared/(?P<token>[^/.]+)')
    def shared(self, request, token=None):
        try:
            task = PersonalTask.objects.select_related('owner').get(share_token=token)
        except PersonalTask.DoesNotExist:
            return fail('Shared task not found', code=404, status_code=404)
        return ok(PersonalTaskSerializer(task, context={'request': request}).data)

    @action(detail=False, methods=['post'], url_path=r'shared/(?P<token>[^/.]+)/import_task')
    def import_task(self, request, token=None):
        try:
            task = PersonalTask.objects.get(share_token=token)
        except PersonalTask.DoesNotExist:
            return fail('Shared task not found', code=404, status_code=404)

        imported = PersonalTask.objects.create(
            owner=request.user,
            title=task.title,
            description=task.description,
            due_at=task.due_at,
            priority=task.priority,
            source_task=task,
        )
        return ok(self.get_serializer(imported).data, status_code=201)

    @action(detail=False, methods=['get'], url_path=r'shared/(?P<token>[^/.]+)/ical')
    def ical(self, request, token=None):
        try:
            task = PersonalTask.objects.get(share_token=token)
        except PersonalTask.DoesNotExist:
            return HttpResponse('Shared task not found', status=404, content_type='text/plain; charset=utf-8')

        response = HttpResponse(build_single_task_ical(task).to_ical(), content_type='text/calendar; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="personal_task_{task.id}.ics"'
        return response

# 4. CalendarEventView
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

class CalendarEventView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_str = request.query_params.get('start')
        end_str = request.query_params.get('end')
        event_type = request.query_params.get('type', 'all')

        user = request.user
        events_data = []

        # 如果前端没传 start/end，给默认范围
        has_explicit_range = bool(start_str and end_str)
        if not has_explicit_range:
            now = timezone.now()
            start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(days=32)
            end_dt = end_dt.replace(day=1)
        else:
            try:
                start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            except ValueError:
                try:
                    start_dt = datetime.strptime(start_str, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_str, '%Y-%m-%d')
                except ValueError:
                    return Response([], status=200)

        # 1. Assignments (DDL)
        if event_type in ['all', 'ddl']:
            student = getattr(user, 'student_profile', None)
            if student:
                assignments = Assignment.objects.filter(
                    course__enrollments__student=student,
                    deadline__range=[start_dt, end_dt]
                ).distinct()

                for ddl in assignments:
                    color = "#7ED321"
                    if ddl.priority == 'high':
                        color = "#D0021B"
                    elif ddl.priority == 'medium':
                        color = "#F5A623"

                    events_data.append({
                        "id": f"ddl_{ddl.id}",
                        "title": f"[DDL] {ddl.title}",
                        "start": ddl.deadline,
                        "end": ddl.deadline,
                        "color": color,
                        "type": "ddl",
                        "course_name": ddl.course.name,
                        "priority": ddl.priority
                    })

        # 2. Events
        if event_type in ['all', 'event']:
            events = Event.objects.filter(
                start_time__range=[start_dt, end_dt]
            ).select_related('category').order_by('start_time')
            if not has_explicit_range:
                per_day_counts = defaultdict(int)
                sampled_events = []
                for event in events.iterator(chunk_size=1000):
                    day_key = event.start_time.date()
                    if per_day_counts[day_key] >= 8:
                        continue
                    sampled_events.append(event)
                    per_day_counts[day_key] += 1
                    if len(sampled_events) >= 80:
                        break
                events = sampled_events

            for e in events:
                events_data.append({
                    "id": f"event_{e.id}",
                    "title": e.title,
                    "start": e.start_time,
                    "end": e.end_time,
                    "color": e.category.color if e.category else "#4A90E2",
                    "type": "event"
                })

        # 3. Personal tasks
        if event_type in ['all', 'task']:
            tasks = PersonalTask.objects.filter(
                owner=user,
                due_at__range=[start_dt, end_dt],
            ).order_by('due_at')

            for task in tasks:
                events_data.append({
                    "id": f"task_{task.id}",
                    "title": f"[Task] {task.title}",
                    "start": task.due_at,
                    "end": task.due_at,
                    "color": get_personal_task_color(task.priority),
                    "type": "task",
                    "priority": task.priority,
                    "is_completed": task.is_completed,
                    "description": task.description,
                })

        return ok(events_data)

    def post(self, request):
        if not is_admin_user(request.user):
            return fail('Only administrators can create events', code=403, status_code=403)

        title = request.data.get('title', '')
        start = request.data.get('start')
        end   = request.data.get('end')

        if not title or not start or not end:
            return fail('title、start、end 为必填项', code=400, status_code=400)

        from django.utils.dateparse import parse_datetime
        if isinstance(start, str):
            start = parse_datetime(start.replace('Z', '+00:00'))
        if isinstance(end, str):
            end = parse_datetime(end.replace('Z', '+00:00'))

        if not start or not end:
            return fail('时间格式错误', code=400, status_code=400)

        event = Event.objects.create(
            title=title,
            start_time=start,
            end_time=end,
            is_public=False,
            created_by=request.user,
        )
        return ok({
            'id': f'event_{event.id}',
            'title': event.title,
            'start': event.start_time,
            'end': event.end_time,
            'color': '#4A90E2',
            'type': 'event',
        }, status_code=201)

# 5. EventViewSet
class EventPagination(PageNumberPagination):
    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 1000


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.select_related(
        'venue',
        'category',
        'created_by'
    ).all().order_by( '-id')

    serializer_class = EventSerializer
    pagination_class = EventPagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = []   # category 通过 list() 手动过滤，避免与名称筛选冲突


    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsEduAdmin()]
        if self.action in ['subscribe', 'subscriptions']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def parse_range_datetime(self, value, end_of_day=False):
        if not value:
            return None

        dt = parse_datetime(value)

        if dt is None:
            d = parse_date(value)
            if d:
                dt = datetime.combine(d, time.max if end_of_day else time.min)

        if dt and timezone.is_naive(dt):
            dt = timezone.make_aware(dt)

        return dt

    def get_queryset(self):
        qs = Event.objects.select_related(
            'venue',
            'category',
            'created_by'
        ).all().order_by( '-id')

        start = (
            self.request.query_params.get('start')
            or self.request.query_params.get('start_date')
            or self.request.query_params.get('date_from')
        )

        end = (
            self.request.query_params.get('end')
            or self.request.query_params.get('end_date')
            or self.request.query_params.get('date_to')
        )

        category = self.request.query_params.get('category')
        category_id = self.request.query_params.get('category_id')

        start_dt = self.parse_range_datetime(start)
        end_dt = self.parse_range_datetime(end, end_of_day=True)

        if start_dt:
            qs = qs.filter(start_time__gte=start_dt)

        if end_dt:
            qs = qs.filter(start_time__lte=end_dt)

        if category and category.lower() != 'all':
            qs = qs.filter(category__name__iexact=category)

        if category_id:
            qs = qs.filter(category_id=category_id)

        return qs
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        category = request.query_params.get('category')
        if category and category.lower() != 'all':
            queryset = queryset.filter(category__name=category)

        dow = request.query_params.get('day_of_week')
        if dow is not None:
            try:
                queryset = queryset.filter(start_time__week_day=int(dow) + 1)
            except (ValueError, TypeError):
                pass

        subscribed_ids = set()
        if request.user.is_authenticated:
            subscribed_ids = set(
                EventSubscription.objects.filter(user=request.user)
                .values_list('event_id', flat=True)
            )

        page = self.paginate_queryset(queryset)
        ctx = {'request': request, 'subscribed_ids': subscribed_ids}

        if page is not None:
            raw_results = EventListSerializer(page, many=True, context=ctx).data
            return ok({
                "total": self.paginator.page.paginator.count,
                "page": self.paginator.page.number,
                "page_size": len(raw_results),
                "results": raw_results
            })

        results = EventListSerializer(queryset, many=True, context=ctx).data
        return ok({
            "total": len(results),
            "page": 1,
            "page_size": len(results),
            "results": results
        })

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        is_subscribed = (
                request.user.is_authenticated and
                EventSubscription.objects.filter(user=request.user, event=instance).exists()
        )
        data['is_subscribed'] = is_subscribed
        return ok(data)

    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, pk=None):
        event = self.get_object()
        if request.method == 'POST':
            _, created = EventSubscription.objects.get_or_create(user=request.user, event=event)
            if not created:
                return Response({'code': 400, 'msg': '已订阅该活动'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'code': 200, 'msg': '订阅成功'})
        else:
            deleted, _ = EventSubscription.objects.filter(user=request.user, event=event).delete()
            if not deleted:
                return Response({'code': 404, 'msg': '未找到订阅记录'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'code': 200, 'msg': '已取消订阅'})

    @action(detail=False, methods=['get'], url_path='subscriptions')
    def subscriptions(self, request):
        subs = EventSubscription.objects.filter(user=request.user).select_related('event__category')
        result = []
        for sub in subs:
            e = sub.event
            result.append({
                'id': e.id,
                'title': e.title,
                'start_time': e.start_time,
                'end_time': e.end_time,
                'category': {
                    'name': e.category.name,
                    'color': e.category.color,
                } if e.category else None,
            })
        return ok(result)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return ok(response.data, status_code=201)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return ok(response.data)

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return ok({})

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

# 6. NotificationViewSet
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() == 'true')
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        raw = response.data
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

        return ok({
            "total": raw.get("count", 0),
            "page": 1,
            "page_size": len(raw.get("results", [])),
            "results": raw.get("results", []),
            "unread_count": unread_count
        })

    @action(detail=False, methods=['patch'], url_path='read')
    def mark_read(self, request):
        ids = request.data.get('ids', [])
        all_read = request.data.get('all', False)

        qs = Notification.objects.filter(user=request.user)
        if all_read:
            qs.update(is_read=True)
        else:
            qs.filter(id__in=ids).update(is_read=True)

        return ok({}, msg='success')

# 7. SearchView
class SearchView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '')
        search_type = request.query_params.get('type', 'all')
        results = []

        if search_type in ['all', 'course']:
            courses = Course.objects.filter(name__icontains=query)
            for c in courses:
                results.append({"id": c.id, "title": c.name, "type": "course", "summary": c.code})
        
        if search_type in ['all', 'event']:
            events = Event.objects.filter(title__icontains=query)
            for e in events:
                results.append({"id": e.id, "title": e.title, "type": "event", "summary": e.venue.name if e.venue else ""})

        return Response({"total": len(results), "results": results})


class OptionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        default_categories = [
            {'name': 'Academic', 'name_cn': '学术活动', 'color': '#d93025', 'icon': 'book'},
            {'name': 'Sports', 'name_cn': '体育活动', 'color': '#1a73e8', 'icon': 'trophy'},
            {'name': 'Course', 'name_cn': '课程相关', 'color': '#4A90E2', 'icon': 'calendar'},
            {'name': 'Culture', 'name_cn': '文化活动', 'color': '#188038', 'icon': 'palette'},
            {'name': 'Workshop', 'name_cn': '工作坊', 'color': '#e37400', 'icon': 'tools'},
            {'name': 'Social', 'name_cn': '社交活动', 'color': '#8430ce', 'icon': 'people'},
            {'name': 'Club', 'name_cn': '社团活动', 'color': '#0f9d58', 'icon': 'people-fill'},
            {'name': 'Career', 'name_cn': '职业发展', 'color': '#fbbc04', 'icon': 'briefcase'},
            {'name': 'Other', 'name_cn': '其他活动', 'color': '#616161', 'icon': 'circle'},
        ]
        for item in default_categories:
            Category.objects.update_or_create(
                name=item['name'],
                defaults={
                    'name_cn': item['name_cn'],
                    'color': item['color'],
                    'icon': item['icon'],
                }
            )
        return ok({
            'teachers': [
                {'id': item.id, 'name': item.name, 'title': item.title}
                for item in Teacher.objects.order_by('name')
            ],
            'semesters': [
                {'id': item.id, 'name': item.name, 'is_current': item.is_current}
                for item in Semester.objects.order_by('-is_current', '-start_date')
            ],
            'venues': [
                {'id': item.id, 'name': item.name, 'building': item.building, 'type': item.type}
                for item in Venue.objects.order_by('building', 'name')
            ],
            'categories': [
                {'id': item.id, 'name': item.name, 'color': item.color, 'icon': item.icon}
                for item in Category.objects.order_by('name')
            ],
        }, msg='ok', code=0)

# 8. AdminDashboardView
class AdminDashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        data = {
            "published_events": Event.objects.count(),
            "upcoming_events": Event.objects.filter(start_time__gte=timezone.now()).count(),
            "total_subscriptions": EventSubscription.objects.count(),
            "event_types": Event.objects.exclude(category__isnull=True).values('category_id').distinct().count(),
        }
        return ok(data)


class TeacherDashboardView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        if request.user.is_superuser:
            courses = Course.objects.all()
        else:
            teacher = getattr(request.user, 'teacher_profile', None)
            if not teacher:
                return fail('Teacher profile not found', code=403, status_code=403)
            courses = Course.objects.filter(teacher=teacher)

        course_ids = courses.values_list('id', flat=True)
        now = timezone.now()
        week_later = now + timedelta(days=7)
        data = {
            "my_courses": courses.count(),
            "my_assignments": Assignment.objects.filter(course_id__in=course_ids).count(),
            "enrolled_students": Enrollment.objects.filter(
                course_id__in=course_ids,
                status='active',
            ).values('student_id').distinct().count(),
            "upcoming_deadlines": Assignment.objects.filter(
                course_id__in=course_ids,
                deadline__gte=now,
                deadline__lte=week_later,
            ).count(),
        }
        return ok(data)


# 9. AdminStatsView
class AdminStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return ok({
            "completion_rate": "85%"
        })


# 10. ActivityLogView
_ACTION_DETAIL = {
    'enrolled':        '学生完成选课操作',
    'added_event':     '管理员添加校历活动',
    'completed_ddl':   '学生提交并完成作业',
    'profile_updated': '用户更新个人资料信息',
    'system_sync':     '系统执行数据自动同步',
    'cache_cleared':   '管理员清除系统缓存',
}
_ACTION_KEYS = list(_ACTION_DETAIL.keys())

class ActivityLogView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = list(User.objects.order_by('-date_joined'))
        if len(users) < len(_ACTION_KEYS):
            users = (users * len(_ACTION_KEYS))[:len(_ACTION_KEYS)]

        entries = []
        for i, user in enumerate(users[:20]):
            action = _ACTION_KEYS[i % len(_ACTION_KEYS)]
            entries.append({
                'id': i + 1,
                'user': user.username,
                'action': action,
                'detail': _ACTION_DETAIL[action],
                'timestamp': (timezone.now() - timedelta(hours=i * 2)).isoformat(),
            })

        return ok(entries)


# ================================================================
# 11. CalendarExportView  GET /api/calendar/export/ical/
# ================================================================
def _build_ical(assignments, events, personal_tasks=None):
    """Build and return an icalendar.Calendar from assignments + events + personal tasks."""
    cal = Calendar()
    cal.add('PRODID', '-//BNBU Calendar//bnbu.edu.cn//')
    cal.add('VERSION', '2.0')
    cal.add('CALSCALE', 'GREGORIAN')
    cal.add('X-WR-CALNAME', 'BNBU Calendar')

    for a in assignments:
        ev = ICalEvent()
        ev.add('UID', f'assignment-{a.id}@bnbu.edu.cn')
        ev.add('SUMMARY', f'[DDL] {a.title}')
        ev.add('DTSTART', a.deadline)
        ev.add('DTEND', a.deadline + timedelta(hours=1))
        ev.add('DESCRIPTION', f'课程: {a.course.name}\n优先级: {a.priority}\n{a.description}')
        cal.add_component(ev)

    for e in events:
        ev = ICalEvent()
        ev.add('UID', f'event-{e.id}@bnbu.edu.cn')
        ev.add('SUMMARY', e.title)
        ev.add('DTSTART', e.start_time)
        ev.add('DTEND', e.end_time)
        desc_parts = [e.description]
        if e.organizer:
            desc_parts.append(f'主办: {e.organizer}')
        ev.add('DESCRIPTION', '\n'.join(p for p in desc_parts if p))
        cal.add_component(ev)

    for task in personal_tasks or []:
        ev = ICalEvent()
        ev.add('UID', f'personal-task-{task.id}@bnbu.edu.cn')
        ev.add('SUMMARY', f'[Task] {task.title}')
        ev.add('DTSTART', task.due_at)
        ev.add('DTEND', task.due_at + timedelta(hours=1))
        desc_parts = [f'Priority: {task.priority}']
        if task.description:
            desc_parts.append(task.description)
        ev.add('DESCRIPTION', '\n'.join(desc_parts))
        cal.add_component(ev)

    return cal


class CalendarExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 1. 当前用户选课的 Assignments
        student = getattr(user, 'student_profile', None)
        if student:
            assignments = list(
                Assignment.objects.filter(
                    course__enrollments__student=student,
                    course__enrollments__status='active',
                ).select_related('course').distinct()
            )
        else:
            assignments = []

        # 2. 订阅的 Events
        subscribed_event_ids = EventSubscription.objects.filter(
            user=user
        ).values_list('event_id', flat=True)

        # 3. 自定义事件（当前用户创建的）
        created_event_ids = Event.objects.filter(
            created_by=user
        ).values_list('id', flat=True)

        all_event_ids = set(subscribed_event_ids) | set(created_event_ids)
        events = list(Event.objects.filter(id__in=all_event_ids).select_related('category'))
        personal_tasks = list(PersonalTask.objects.filter(owner=user).order_by('due_at'))

        cal = _build_ical(assignments, events, personal_tasks)

        response = HttpResponse(cal.to_ical(), content_type='text/calendar; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="bnbu_calendar.ics"'
        return response


# ================================================================
# 12. ShareLinkCreateView  POST /api/calendar/share/
# ================================================================
class ShareLinkCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = uuid.uuid4().hex[:8]
        # Retry on the rare collision
        while ShareLink.objects.filter(token=token).exists():
            token = uuid.uuid4().hex[:8]

        ShareLink.objects.create(user=request.user, token=token)

        host = request.get_host()
        scheme = 'https' if request.is_secure() else 'http'
        share_url = f'{scheme}://{host}/api/shared/{token}/'
        return ok({'share_url': share_url}, status_code=201)


# ================================================================
# 13. SharedCalendarView  GET /api/shared/{token}/
# ================================================================
class SharedCalendarView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            link = ShareLink.objects.select_related('user').get(token=token)
        except ShareLink.DoesNotExist:
            return Response({'detail': '链接无效或已失效'}, status=status.HTTP_404_NOT_FOUND)

        user = link.user
        now = timezone.now()
        week_later = now + timedelta(days=7)

        items = []

        # Assignments within next 7 days (student only)
        student = getattr(user, 'student_profile', None)
        if student:
            assignments = Assignment.objects.filter(
                course__enrollments__student=student,
                course__enrollments__status='active',
                deadline__range=[now, week_later],
            ).select_related('course').distinct()
            for a in assignments:
                items.append({
                    'type': 'assignment',
                    'id': a.id,
                    'title': f'[DDL] {a.title}',
                    'start': a.deadline,
                    'end': a.deadline + timedelta(hours=1),
                    'description': a.description,
                    'course': a.course.name,
                    'priority': a.priority,
                })

        # Public Events within next 7 days
        events = Event.objects.filter(
            is_public=True,
            start_time__range=[now, week_later],
        ).select_related('category')
        for e in events:
            items.append({
                'type': 'event',
                'id': e.id,
                'title': e.title,
                'start': e.start_time,
                'end': e.end_time,
                'description': e.description,
                'category': e.category.name if e.category else None,
            })

        items.sort(key=lambda x: x['start'])

        return Response({
            'owner': user.username,
            'generated_at': now,
            'range_days': 7,
            'count': len(items),
            'events': items,
        })


# ================================================================
# 14. CalendarEventDetailView  GET/PUT/DELETE /api/calendar/events/<event_id>/
#
# event_id format: 'event_<pk>'  → operates on Event model
#                  'ddl_<pk>'    → operates on Assignment model
# ================================================================
class CalendarEventDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _parse(self, event_id):
        if event_id.startswith('event_'):
            return 'event', int(event_id[6:])
        if event_id.startswith('ddl_'):
            return 'ddl', int(event_id[4:])
        raise ValueError

    def _can_manage_assignment(self, request, assignment):
        if getattr(request.user, 'is_superuser', False):
            return True
        teacher = getattr(request.user, 'teacher_profile', None)
        return bool(
            getattr(request.user, 'role', None) == 'teacher'
            and teacher
            and assignment.course.teacher_id == teacher.id
        )

    def get(self, request, event_id):
        try:
            kind, pk = self._parse(event_id)
        except (ValueError, IndexError):
            return fail('无效的事件ID', code=400, status_code=400)

        if kind == 'event':
            try:
                e = Event.objects.get(pk=pk)
            except Event.DoesNotExist:
                return fail('活动不存在', code=404, status_code=404)
            return ok({
                'id': event_id, 'title': e.title,
                'start': e.start_time, 'end': e.end_time,
                'color': e.category.color if e.category else '#4A90E2',
                'type': 'event',
            })
        else:
            try:
                a = Assignment.objects.get(pk=pk)
            except Assignment.DoesNotExist:
                return fail('作业不存在', code=404, status_code=404)
            return ok({
                'id': event_id, 'title': a.title,
                'start': a.deadline, 'end': a.deadline,
                'type': 'ddl', 'is_completed': a.is_completed,
                'priority': a.priority,
            })

    def put(self, request, event_id):
        try:
            kind, pk = self._parse(event_id)
        except (ValueError, IndexError):
            return fail('无效的事件ID', code=400, status_code=400)

        from django.utils.dateparse import parse_datetime

        if kind == 'event':
            try:
                e = Event.objects.get(pk=pk)
            except Event.DoesNotExist:
                return fail('活动不存在', code=404, status_code=404)
            if not IsEduAdmin().has_permission(request, self):
                return fail('无权修改此活动', code=403, status_code=403)
            e.title = request.data.get('title', e.title)
            for field, attr in (('start', 'start_time'), ('end', 'end_time')):
                val = request.data.get(field)
                if val:
                    if isinstance(val, str):
                        val = parse_datetime(val.replace('Z', '+00:00')) or getattr(e, attr)
                    setattr(e, attr, val)
            e.save(update_fields=['title', 'start_time', 'end_time'])
            return ok({'id': event_id, 'title': e.title,
                       'start': e.start_time, 'end': e.end_time, 'type': 'event'})
        else:
            try:
                a = Assignment.objects.get(pk=pk)
            except Assignment.DoesNotExist:
                return fail('作业不存在', code=404, status_code=404)
            if not self._can_manage_assignment(request, a):
                return fail('无权修改此作业', code=403, status_code=403)
            a.title = request.data.get('title', a.title)
            a.priority = request.data.get('priority', a.priority)
            deadline = request.data.get('deadline')
            if deadline:
                if isinstance(deadline, str):
                    deadline = parse_datetime(deadline.replace('Z', '+00:00'))
                if deadline:
                    a.deadline = deadline
            a.save(update_fields=['title', 'priority', 'deadline'])
            return ok({'id': event_id, 'title': a.title,
                       'start': a.deadline, 'end': a.deadline, 'type': 'ddl'})

    def delete(self, request, event_id):
        try:
            kind, pk = self._parse(event_id)
        except (ValueError, IndexError):
            return fail('无效的事件ID', code=400, status_code=400)

        if kind == 'event':
            try:
                e = Event.objects.get(pk=pk)
            except Event.DoesNotExist:
                return fail('活动不存在', code=404, status_code=404)
            if not IsEduAdmin().has_permission(request, self):
                return fail('无权删除此活动', code=403, status_code=403)
            e.delete()
        else:
            try:
                a = Assignment.objects.get(pk=pk)
            except Assignment.DoesNotExist:
                return fail('作业不存在', code=404, status_code=404)
            if not self._can_manage_assignment(request, a):
                return fail('无权删除此作业', code=403, status_code=403)
            a.delete()
        return ok({}, msg='删除成功')


# ================================================================
# 15. CalendarEventCompleteView  PATCH /api/calendar/events/<event_id>/complete/
# ================================================================
class CalendarEventCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, event_id):
        if not event_id.startswith('ddl_'):
            return fail('只有作业DDL支持标记完成', code=400, status_code=400)
        try:
            pk = int(event_id[4:])
        except ValueError:
            return fail('无效的事件ID', code=400, status_code=400)

        try:
            assignment = Assignment.objects.select_related('course').get(pk=pk)
        except Assignment.DoesNotExist:
            return fail('作业不存在', code=404, status_code=404)

        if assignment.is_completed:
            return fail('作业已标记完成', code=400, status_code=400)

        assignment.is_completed = True
        assignment.save(update_fields=['is_completed'])

        # MySQL trigger after_assignment_complete handles credit update.
        # Replicate in Python for SQLite / non-MySQL environments.
        # Use subquery to avoid duplicate rows from JOIN inflating the update.
        from django.db import connection
        if connection.vendor != 'mysql':
            credit = assignment.course.credit
            student_ids = list(
                Student.objects.filter(
                    enrollments__course=assignment.course,
                    enrollments__status='active',
                ).values_list('id', flat=True).distinct()
            )
            Student.objects.filter(id__in=student_ids).update(
                total_credit=F('total_credit') + credit
            )

        return ok({'id': event_id, 'is_completed': True}, msg='作业已标记完成')
