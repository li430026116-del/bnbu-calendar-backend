"""
URL configuration for bnbu_calendar project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('index.html', TemplateView.as_view(template_name='index.html'), name='index-html'),
    path('login.html', TemplateView.as_view(template_name='login.html'), name='login-html'),
    path('dashboard.html', TemplateView.as_view(template_name='dashboard.html'), name='dashboard-html'),
    path('admin_dashboard.html', TemplateView.as_view(template_name='admin_dashboard.html'), name='admin-dashboard-html'),
    path('teacher_dashboard.html', TemplateView.as_view(template_name='teacher_dashboard.html'), name='teacher-dashboard-html'),
    path('teacher_courses.html', TemplateView.as_view(template_name='teacher_courses.html'), name='teacher-courses-html'),
    path('activity.html', TemplateView.as_view(template_name='activity.html'), name='activity-html'),
    path('course.html', TemplateView.as_view(template_name='course.html'), name='course-html'),
    path('courses.html', TemplateView.as_view(template_name='courses.html'), name='courses-html'),
    path('course_detail.html', TemplateView.as_view(template_name='course_detail.html'), name='course-detail-html'),
    path('event.html', TemplateView.as_view(template_name='event.html'), name='event-html'),
    path('analytics.html', TemplateView.as_view(template_name='analytics.html'), name='analytics-html'),
    path('task_import.html', TemplateView.as_view(template_name='task_import.html'), name='task-import-html'),
    path('admin/', admin.site.urls),
    path('', include('calendar_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
