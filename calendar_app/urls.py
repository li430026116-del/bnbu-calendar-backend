from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_auth import RegisterView, LoginView, UserInfoView, LogoutView, PreferencesView
from . import views
from .views import (
    CalendarExportView, ShareLinkCreateView, SharedCalendarView,
    CalendarEventDetailView, CalendarEventCompleteView,
)

# 使用 DefaultRouter 注册 ViewSet
router = DefaultRouter()
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'enrollments', views.EnrollmentViewSet, basename='enrollment')
router.register(r'assignments', views.AssignmentViewSet, basename='assignment')
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'personal-tasks', views.PersonalTaskViewSet, basename='personal-task')

urlpatterns = [
    # 首页
    path('', views.index, name='index'),
    
    # 1. 认证路由 (手动配置)
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/me/', UserInfoView.as_view(), name='user_info'),
    path('api/auth/preferences/', PreferencesView.as_view(), name='preferences'),
    path('api/settings/', PreferencesView.as_view(), name='settings'),
    
    # 2. ViewSet 路由 (Router 自动处理，包含 /my/ 等 action)
    path('api/', include(router.urls)),
    
    # 3. 业务功能路由 (手动配置)
    path('api/calendar/events/', views.CalendarEventView.as_view(), name='calendar_events'),
    path('api/calendar/events/<str:event_id>/complete/', CalendarEventCompleteView.as_view(), name='calendar_event_complete'),
    path('api/calendar/events/<str:event_id>/', CalendarEventDetailView.as_view(), name='calendar_event_detail'),
    path('api/calendar/export/ical/', CalendarExportView.as_view(), name='calendar_export_ical'),
    path('api/calendar/share/', ShareLinkCreateView.as_view(), name='calendar_share'),
    path('api/shared/<str:token>/', SharedCalendarView.as_view(), name='shared_calendar'),
    path('api/search/', views.SearchView.as_view(), name='search'),
    path('api/options/', views.OptionsView.as_view(), name='options'),
    
    # 4. 管理端路由 (手动配置)
    path('api/admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('api/teacher/dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('api/admin/stats/completion/', views.AdminStatsView.as_view(), name='admin_stats'),
    path('api/admin/activity-log/', views.ActivityLogView.as_view(), name='activity_log'),
]
