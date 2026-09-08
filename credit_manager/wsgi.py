import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'credit_manager.settings')
application = get_wsgi_application()
app = application

# Automatic database setup for Vercel serverless functions
if os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    try:
        from django.core.management import call_command
        from django.db import connection
        tables = connection.introspection.table_names()
        if 'accounts_user' not in tables:
            call_command('migrate', interactive=False)
            from accounts.models import User
            if not User.objects.filter(role='SUPER_ADMIN').exists():
                admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
                admin_user.role = User.Role.SUPER_ADMIN
                admin_user.save()
    except Exception as err:
        print("Vercel auto-migration status:", err)


