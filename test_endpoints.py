import os
import django
import json
from datetime import datetime
from django.utils import timezone

# 1. 初始化 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bnbu_calendar.settings')
django.setup()

from django.test import Client
from calendar_app.models import User, Student, Course, Assignment, Event, Category, Semester, Venue, Enrollment
from rest_framework.authtoken.models import Token

def run_automation_test():
    client = Client()
    print("🚀 开始端到端自动化测试...\n")

    # 2. 造数据：创建测试账号
    username = "e2e_test_student"
    password = "testpassword123"
    
    # 清理旧数据
    User.objects.filter(username=username).delete()
    
    user = User.objects.create_user(
        username=username, 
        password=password, 
        email="e2e@test.com", 
        role="student"
    )
    student = Student.objects.create(
        user=user, 
        student_id="E2E001", 
        name="E2E Student",
        faculty="FST",
        major_code="CST",
        major_name="Computer Science",
        grade=2024
    )
    
    # 3. 造环境：创建课程、选课、DDL 和 Event
    # 创建学期、地点
    semester, _ = Semester.objects.get_or_create(name="2026 Spring", start_date="2026-01-01", end_date="2026-06-30")
    venue, _ = Venue.objects.get_or_create(name="Lab 101", capacity=50)
    
    # 创建课程
    course, _ = Course.objects.get_or_create(
        code="CS101", 
        name="Intro to Programming", 
        semester=semester,
        venue=venue
    )
    
    # 学生选课 (为了让 Calendar 能查到该学生的 DDL)
    Enrollment.objects.get_or_create(
        student=student, 
        course=course,
        defaults={'enrolled_at': timezone.now(), 'status': 'active'}
    )

    # 创建 2026-04-15 的 Assignment (DDL)
    target_date = datetime(2026, 4, 15, 23, 59, 0, tzinfo=timezone.get_current_timezone())
    Assignment.objects.create(
        course=course,
        title="E2E Project DDL",
        deadline=target_date,
        priority="high"
    )

    # 创建 2026-04-15 的 Event
    category, _ = Category.objects.get_or_create(name="Academic", color="#4A90E2")
    Event.objects.create(
        title="E2E Seminar",
        start_time=datetime(2026, 4, 15, 14, 0, 0, tzinfo=timezone.get_current_timezone()),
        end_time=datetime(2026, 4, 15, 16, 0, 0, tzinfo=timezone.get_current_timezone()),
        venue=venue,
        category=category
    )

    print("✅ 数据准备完成：已创建学生、课程、选课记录、DDL(4/15) 和 Event(4/15)。")

    # 4. 模拟登录获取 Token
    token, _ = Token.objects.get_or_create(user=user)
    headers = {"HTTP_AUTHORIZATION": f"Token {token.key}"}
    print(f"🔑 Token 获取成功: {token.key[:10]}...")

    # 5. 发起请求：/api/calendar/events/
    print("\n📡 正在请求日历数据 API...")
    url = "/api/calendar/events/"
    params = {
        "start": "2026-04-01",
        "end": "2026-04-30",
        "type": "all"
    }
    
    response = client.get(url, params, **headers)

    # 6. 打印结果与分析
    if response.status_code == 200:
        data = response.json()
        print("\n✨ [API 返回结果] ✨")
        print(json.dumps(data, indent=4, ensure_ascii=False))
        
        # 检查是否包含造的数据
        has_ddl = any(item['type'] == 'ddl' and "E2E Project DDL" in item['title'] for item in data)
        has_event = any(item['type'] == 'event' and "E2E Seminar" in item['title'] for item in data)
        
        print("\n📊 [测试分析报告]")
        if has_ddl and has_event:
            print("✅ 成功：返回数据中包含了预期的 DDL 和 Event！")
        else:
            print("❌ 失败：部分数据缺失。")
            if not has_ddl: print("- 缺失 DDL 数据")
            if not has_event: print("- 缺失 Event 数据")
            
        # 检查 FullCalendar 关键字段
        required_fields = ['id', 'title', 'start', 'end', 'color', 'type']
        field_check = all(all(field in item for field in required_fields) for item in data)
        if field_check:
            print("✅ 成功：所有数据项均符合 FullCalendar 字段要求。")
        else:
            print("❌ 警告：部分数据项缺失 FullCalendar 必要字段。")

    else:
        print(f"\n❌ 错误：API 请求失败，状态码: {response.status_code}")
        print(f"响应内容: {response.content.decode()}")

if __name__ == "__main__":
    run_automation_test()
