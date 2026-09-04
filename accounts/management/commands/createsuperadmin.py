from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import getpass

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a Super Admin user'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Super Admin username')
        parser.add_argument('--email', type=str, help='Super Admin email')
        parser.add_argument('--password', type=str, help='Super Admin password')
        parser.add_argument('--noinput', action='store_true', help='Non-interactive mode')

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')
        password = options.get('password')

        if not options.get('noinput'):
            if not username:
                username = input('Username: ')
            if not email:
                email = input('Email: ')
            if not password:
                password = getpass.getpass('Password: ')

        if not all([username, email, password]):
            self.stdout.write(self.style.ERROR('Username, email, and password are required.'))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User {username} already exists.'))
            return

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        user.role = User.Role.SUPER_ADMIN
        user.save()

        self.stdout.write(self.style.SUCCESS(f'Super Admin {username} created successfully!'))
