from django.core.management.base import BaseCommand
from calendar_app.data_generator import main as generate_main
from calendar_app.models import (
    Notification, Feedback, CustomTag, Event, Assignment, 
    Enrollment, Course, Venue, Category, Semester, 
    Student, Teacher, User
)

class Command(BaseCommand):
    help = '生成 BNBU 校园日程系统的测试数据'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='清空所有表后再生成')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing all tables...')
            # 按反向依赖顺序清空
            models_to_clear = [
                Notification, Feedback, CustomTag, Event, Assignment, 
                Enrollment, Course, Venue, Category, Semester, 
                Student, Teacher, User
            ]
            for model in models_to_clear:
                model.objects.all().delete()
            self.stdout.write('All tables cleared.')

        self.stdout.write('Starting data generation...')
        try:
            generate_main()
            self.stdout.write(self.style.SUCCESS('Successfully generated test data.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during data generation: {e}'))
