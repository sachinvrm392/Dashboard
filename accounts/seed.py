from accounts.models import User, BusinessPartner

def seed_initial_data():
    # 1. Super Admin Accounts
    if not User.objects.filter(username='devadmin').exists():
        u = User.objects.create_superuser('devadmin', 'icgriddeb@gmail.com', 'admin123')
        u.role = User.Role.SUPER_ADMIN
        u.save()
    elif not User.objects.get(username='devadmin').check_password('admin123'):
        u = User.objects.get(username='devadmin')
        u.set_password('admin123')
        u.save()

    if not User.objects.filter(username='admin').exists():
        u = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        u.role = User.Role.SUPER_ADMIN
        u.save()

    # 2. Business Partner Accounts
    bp_data = [
        ('infinitycardano', 'Infinity Cardano', 'Parmanad', 'icgriddeb@gmail.com', 10.00),
        ('quantumaudio', 'QuantumAudio', "Liam O'Connor", 'liam@quantumaudio.ie', 0.00),
        ('omnisound', 'OmniSound Global', 'Thomas Wright', 'twright@omnisound.co.uk', 0.00),
        ('echosphere', 'EchoSphere Digital', 'Rachel Adams', 'radams@echosphere.io', 0.00),
        ('vocalmatrix', 'VocalMatrix Inc', 'David Kim', 'david@vocalmatrix.ai', 0.00),
        ('nexismedia', 'Nexis Media Group', 'Elena Rostova', 'elena@nexismedia.com', 0.00),
        ('globalaudio', 'Global Audio Networks', 'Michael Chang', 'mchang@globalaudio.net', 0.00),
    ]

    for username, company_name, contact_person, email, cost_per_min in bp_data:
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123',
                role=User.Role.BUSINESS_PARTNER
            )
            BusinessPartner.objects.create(
                user=user,
                company_name=company_name,
                contact_person=contact_person,
                email=email,
                cost_per_minute=cost_per_min
            )
