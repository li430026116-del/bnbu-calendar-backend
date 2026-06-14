from django.core.management.base import BaseCommand, CommandError

from calendar_app.models import User


class Command(BaseCommand):
    help = 'Create or update an administrator account for the frontend admin portal.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--email', default='')

    def handle(self, *args, **options):
        username = options['username'].strip()
        password = options['password']
        email = options['email'].strip()

        if not username:
            raise CommandError('Username cannot be empty.')
        if not password:
            raise CommandError('Password cannot be empty.')

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
            },
        )

        updated_fields = []
        if email and user.email != email:
            user.email = email
            updated_fields.append('email')
        if user.role != 'admin':
            user.role = 'admin'
            updated_fields.append('role')
        if not user.is_staff:
            user.is_staff = True
            updated_fields.append('is_staff')
        if not user.is_superuser:
            user.is_superuser = True
            updated_fields.append('is_superuser')

        user.set_password(password)
        updated_fields.append('password')
        user.save(update_fields=updated_fields)

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{action} admin account: {username}'))
