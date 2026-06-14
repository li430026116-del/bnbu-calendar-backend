from django.core.management.base import BaseCommand, CommandError

from calendar_app.models import Teacher, User


class Command(BaseCommand):
    help = 'Create or update a teacher account and teacher profile.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--email', required=True)
        parser.add_argument('--teacher-id', required=True)
        parser.add_argument('--name', required=True)
        parser.add_argument('--faculty', required=True)
        parser.add_argument('--title', required=True)

    def handle(self, *args, **options):
        username = options['username'].strip()
        password = options['password']
        email = options['email'].strip()
        teacher_id = options['teacher_id'].strip()
        name = options['name'].strip()
        faculty = options['faculty'].strip()
        title = options['title'].strip()

        if not username:
            raise CommandError('Username cannot be empty.')
        if not password:
            raise CommandError('Password cannot be empty.')
        if not teacher_id:
            raise CommandError('Teacher ID cannot be empty.')

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'role': 'teacher',
                'is_active': True,
            },
        )

        user.email = email
        user.role = 'teacher'
        user.is_active = True
        user.set_password(password)
        user.save(update_fields=['email', 'role', 'is_active', 'password'])

        Teacher.objects.update_or_create(
            user=user,
            defaults={
                'teacher_id': teacher_id,
                'name': name,
                'faculty': faculty,
                'title': title,
            },
        )

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{action} teacher account: {username}'))
