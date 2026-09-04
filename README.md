# Leads Management CRM — ElevenLabs Partner & Quota Platform

A modern, enterprise-grade Django CRM dashboard for managing ElevenLabs credit limits, voice models, partner registries, and usage quotas.

![CRM Preview](https://img.shields.io/badge/Status-Operational-brightgreen)
![Django](https://img.shields.io/badge/Django-5.0+-092E20?logo=django&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind-3.0+-38B2AC?logo=tailwind-css&logoColor=white)
![ChartJS](https://img.shields.io/badge/Chart.js-4.4+-FF6384?logo=chartdotjs&logoColor=white)

---

## Key Features

- **Credit & Quota Intelligence**: Real-time aggregation of ElevenLabs subscription data, characters consumed, remaining quotas, and velocity metrics.
- **Dynamic Dual-Theme**: Sleek Deep Navy Dark Theme and Crisp Pure White Light Theme with instantaneous `localStorage` switching and anti-flicker loading.
- **Interactive Analytics**: 7-day credit activity bar chart powered by Chart.js with dynamic axis and grid repainting on theme toggle.
- **Business Partner Registry**:
  - Latest 5 Partners quick view on Dashboard.
  - Complete, paginated Partner Directory with search and active/inactive/trash filters.
  - Real-time client-side and server-side validation.
  - Secure random password auto-generation.
- **Super Admin Soft Delete & Restore**: Safely archive partners to trash with user deactivation and one-click restoration.
- **User Profile Management**: Dedicated interface to update account names, email, contact information, and security credentials.
- **Voice Quotas**: Live inspection of provisioned ElevenLabs voice models and synthesis profiles.

---

## Tech Stack

- **Backend**: Python 3.10+, Django 5.0, SQLite (default dev) / PostgreSQL-ready
- **Frontend**: Django Template Language, Tailwind CSS, Iconify Icons, Chart.js 4.4
- **Security**: Custom Role-based Auth (Super Admin / Business Partner), CSRF Protection, Password Hashing

---

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/sachinvrm392/Dashboard.git
cd Dashboard
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
Copy the example environment file:
```bash
cp .env.example .env
```

### 5. Run migrations
```bash
python manage.py migrate
```

### 6. Create Super Admin
```bash
python manage.py createsuperuser
# Or use the custom command:
python manage.py createsuperadmin
```

### 7. Run the development server
```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## License
Proprietary &bull; Leads Management CRM &copy; 2026. All rights reserved.
