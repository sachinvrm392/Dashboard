import os

# Ensure SECRET_KEY is set in environment before Django loads
if not os.environ.get('SECRET_KEY') or not os.environ.get('SECRET_KEY').strip():
    os.environ['SECRET_KEY'] = 'django-insecure-default-secret-key-crm-2026-production-fallback'

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'credit_manager.settings')
application = get_wsgi_application()
app = application


# Automatic database setup and seeding for Vercel serverless functions
if os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    try:
        from django.core.management import call_command
        from django.db import connection
        tables = connection.introspection.table_names()
        if 'accounts_user' not in tables:
            call_command('migrate', interactive=False)
        from accounts.seed import seed_initial_data
        seed_initial_data()
    except Exception as err:
        print("Vercel auto-migration status:", err)



