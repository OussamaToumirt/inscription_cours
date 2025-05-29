# Enhanced tests.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta
from .models import Cours, Etudiant, Inscription
from .forms import EtudiantForm, CoursChoiceForm

class CourseModelTest(TestCase):
    def setUp(self):
        self.cours = Cours.objects.create(
            nom="Test Course",
            prix=Decimal('199.99'),
            duree="8 weeks",
            resume="Test course description",
            category="tech",
            max_students=30
        )

    def test_course_creation(self):
        self.assertEqual(self.cours.nom, "Test Course")
        self.assertEqual(self.cours.prix, Decimal('199.99'))
        self.assertTrue(self.cours.is_active)
        self.assertEqual(self.cours.available_slots, 30)

    def test_course_str_method(self):
        self.assertEqual(str(self.cours), "Test Course")

    def test_available_slots_calculation(self):
        # Create student and inscription
        user = User.objects.create_user(username='test', email='test@test.com', password='testpass123')
        student = Etudiant.objects.create(
            user=user,
            nom="Test Student",
            email="test@test.com",
            telephone="+1234567890",
            date_naissance=date(1990, 1, 1)
        )
        Inscription.objects.create(etudiant=student, cours=self.cours, status='confirmed')
        
        self.assertEqual(self.cours.available_slots, 29)

class StudentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.student = Etudiant.objects.create(
            user=self.user,
            nom="Test Student",
            email="test@test.com",
            telephone="+1234567890",
            date_naissance=date(1990, 1, 1)
        )

    def test_student_creation(self):
        self.assertEqual(self.student.nom, "Test Student")
        self.assertEqual(self.student.email, "test@test.com")
        self.assertEqual(self.student.user, self.user)

    def test_age_calculation(self):
        # Student born in 1990 should be around 33-34 years old
        age = self.student.age
        self.assertGreaterEqual(age, 33)
        self.assertLessEqual(age, 35)

class InscriptionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.student = Etudiant.objects.create(
            user=self.user,
            nom="Test Student",
            email="test@test.com",
            telephone="+1234567890",
            date_naissance=date(1990, 1, 1)
        )
        self.cours = Cours.objects.create(
            nom="Test Course",
            prix=Decimal('199.99'),
            duree="8 weeks",
            resume="Test course description",
            max_students=30
        )

    def test_inscription_creation(self):
        inscription = Inscription.objects.create(
            etudiant=self.student,
            cours=self.cours,
            status='pending'
        )
        self.assertEqual(inscription.etudiant, self.student)
        self.assertEqual(inscription.cours, self.cours)
        self.assertEqual(inscription.status, 'pending')

    def test_unique_together_constraint(self):
        # Create first inscription
        Inscription.objects.create(etudiant=self.student, cours=self.cours)
        
        # Try to create duplicate - should raise IntegrityError
        with self.assertRaises(Exception):
            Inscription.objects.create(etudiant=self.student, cours=self.cours)

class FormsTest(TestCase):
    def test_student_form_valid_data(self):
        form_data = {
            'nom': 'Test Student',
            'email': 'test@test.com',
            'telephone': '+1234567890',
            'date_naissance': date(1990, 1, 1),
            'address': 'Test Address'
        }
        form = EtudiantForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_student_form_invalid_age(self):
        # Test with age under 16
        form_data = {
            'nom': 'Young Student',
            'email': 'young@test.com',
            'telephone': '+1234567890',
            'date_naissance': date.today() - timedelta(days=15*365),  # 15 years old
        }
        form = EtudiantForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('date_naissance', form.errors)

class ViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.cours = Cours.objects.create(
            nom="Test Course",
            prix=Decimal('199.99'),
            duree="8 weeks",
            resume="Test course description",
            max_students=30
        )

    def test_auth_view_anonymous(self):
        response = self.client.get(reverse('auth'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In')

    def test_auth_view_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('auth'))
        self.assertEqual(response.status_code, 302)  # Should redirect

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_with_login(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')

    def test_courses_list_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('courses_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Course')

    def test_course_filtering(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('courses_list'), {'category': 'tech'})
        self.assertEqual(response.status_code, 200)

# Docker configuration - Dockerfile
DOCKERFILE = '''
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
        postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations
RUN python manage.py migrate

# Create superuser (for development only)
RUN echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
'''

# Docker Compose configuration
DOCKER_COMPOSE = '''
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - DEBUG=1
      - DATABASE_URL=sqlite:///db.sqlite3
    depends_on:
      - db

  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      - POSTGRES_DB=course_registration
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres

volumes:
  postgres_data:
'''

# GitHub Actions CI/CD - .github/workflows/django.yml
GITHUB_ACTIONS = '''
name: Django CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      max-parallel: 4
      matrix:
        python-version: [3.9, 3.10, 3.11]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
        
    - name: Install Dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        
    - name: Run Migrations
      run: |
        python manage.py migrate
        
    - name: Run Tests
      run: |
        python manage.py test
        
    - name: Generate Coverage Report
      run: |
        pip install coverage
        coverage run --source='.' manage.py test
        coverage xml
        
    - name: Upload Coverage to Codecov
      uses: codecov/codecov-action@v3
'''

# Production settings - settings_production.py
PRODUCTION_SETTINGS = '''
from .settings import *
import os
from decouple import config

# Production settings
DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS settings
USE_TLS = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Database for production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

# Static files for production
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files for production
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Logging for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/error.log',
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'gestion_inscriptions': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
'''

# Environment variables template - .env.example
ENV_EXAMPLE = '''
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL for production)
DB_NAME=course_registration
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# Email Settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Redis (for caching)
REDIS_URL=redis://127.0.0.1:6379/1

# Security
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
'''

# Management command for backup - backup_data.py
BACKUP_COMMAND = '''
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Backup database and media files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directory to store backups'
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create backup directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Backup database
        db_backup_file = os.path.join(output_dir, f'db_backup_{timestamp}.json')
        
        self.stdout.write('Creating database backup...')
        with open(db_backup_file, 'w') as f:
            call_command('dumpdata', stdout=f, indent=2)
        
        self.stdout.write(
            self.style.SUCCESS(f'Database backup created: {db_backup_file}')
        )
        
        # Backup media files (if any)
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if media_root and os.path.exists(media_root):
            import shutil
            media_backup_dir = os.path.join(output_dir, f'media_backup_{timestamp}')
            shutil.copytree(media_root, media_backup_dir)
            self.stdout.write(
                self.style.SUCCESS(f'Media backup created: {media_backup_dir}')
            )
        
        self.stdout.write(
            self.style.SUCCESS('Backup completed successfully!')
        )
'''

# Performance monitoring middleware
PERFORMANCE_MIDDLEWARE = '''
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """Monitor request performance and log slow requests"""
    
    def process_request(self, request):
        request.start_time = time.time()
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log slow requests (over 2 seconds)
            if duration > 2.0:
                logger.warning(
                    f'Slow request: {request.method} {request.path} '
                    f'took {duration:.2f}s - User: {request.user}'
                )
            
            # Add performance header for debugging
            response['X-Response-Time'] = f'{duration:.3f}s'
        
        return response
'''

# Security middleware for additional protection
SECURITY_MIDDLEWARE = '''
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware(MiddlewareMixin):
    """Additional security checks"""
    
    SUSPICIOUS_PATTERNS = [
        'wp-admin', 'admin.php', '.env', 'phpinfo',
        'eval(', 'base64_decode', '<script', 'javascript:'
    ]
    
    def process_request(self, request):
        # Check for suspicious patterns in URL
        path = request.path.lower()
        query = request.META.get('QUERY_STRING', '').lower()
        
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in path or pattern in query:
                logger.warning(
                    f'Suspicious request blocked: {request.path} '
                    f'from {self.get_client_ip(request)}'
                )
                return HttpResponseForbidden('Access denied')
        
        return None
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
'''

# API views for mobile app or external integration
API_VIEWS = '''
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from .models import Cours, Etudiant, Inscription
from .serializers import CoursSerializer, EtudiantSerializer, InscriptionSerializer

class CoursViewSet(viewsets.ReadOnlyModelViewSet):
    """API for courses - read only"""
    queryset = Cours.objects.filter(is_active=True)
    serializer_class = CoursSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        return queryset
    
    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        """Enroll user in course"""
        cours = self.get_object()
        
        try:
            etudiant = Etudiant.objects.get(user=request.user)
        except Etudiant.DoesNotExist:
            return Response(
                {'error': 'Please complete your profile first'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already enrolled
        if Inscription.objects.filter(etudiant=etudiant, cours=cours).exists():
            return Response(
                {'error': 'Already enrolled in this course'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check available slots
        if cours.available_slots <= 0:
            return Response(
                {'error': 'Course is full'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create inscription
        inscription = Inscription.objects.create(
            etudiant=etudiant,
            cours=cours,
            status='confirmed'
        )
        
        return Response(
            InscriptionSerializer(inscription).data,
            status=status.HTTP_201_CREATED
        )

class EtudiantViewSet(viewsets.ModelViewSet):
    """API for student profile management"""
    serializer_class = EtudiantSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Etudiant.objects.filter(user=self.request.user)

class InscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """API for user's registrations"""
    serializer_class = InscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            etudiant = Etudiant.objects.get(user=self.request.user)
            return Inscription.objects.filter(etudiant=etudiant)
        except Etudiant.DoesNotExist:
            return Inscription.objects.none()
'''

# Serializers for API
SERIALIZERS = '''
from rest_framework import serializers
from .models import Cours, Etudiant, Inscription

class CoursSerializer(serializers.ModelSerializer):
    available_slots = serializers.ReadOnlyField()
    enrolled_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Cours
        fields = ['id', 'nom', 'category', 'prix', 'duree', 'resume', 
                 'max_students', 'available_slots', 'enrolled_count', 'created_at']

class EtudiantSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()
    
    class Meta:
        model = Etudiant
        fields = ['id', 'nom', 'email', 'telephone', 'date_naissance', 
                 'address', 'age', 'created_at']
        read_only_fields = ['created_at']

class InscriptionSerializer(serializers.ModelSerializer):
    cours = CoursSerializer(read_only=True)
    etudiant = EtudiantSerializer(read_only=True)
    
    class Meta:
        model = Inscription
        fields = ['id', 'cours', 'etudiant', 'status', 'inscription_date', 
                 'payment_status', 'notes']
'''

# Deployment script
DEPLOY_SCRIPT = '''#!/bin/bash

# Deployment script for Django Course Registration System

set -e

echo "Starting deployment..."

# Pull latest code
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Run tests
python manage.py test

# Restart application server (adjust for your setup)
# sudo systemctl restart gunicorn
# sudo systemctl restart nginx

echo "Deployment completed successfully!"

# Optional: Create backup before deployment
# python manage.py backup_data

# Optional: Send notification
# curl -X POST -H 'Content-type: application/json' \
#   --data '{"text":"Course Registration System deployed successfully!"}' \
#   YOUR_SLACK_WEBHOOK_URL
'''

# Load testing script with locust
LOAD_TEST = '''
from locust import HttpUser, task, between
import random

class CourseRegistrationUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login user"""
        self.client.post("/auth/login/", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
    
    @task(3)
    def view_dashboard(self):
        """View dashboard"""
        self.client.get("/")
    
    @task(2)
    def browse_courses(self):
        """Browse courses"""
        self.client.get("/courses/")
        
        # Filter by category
        categories = ['tech', 'business', 'arts', 'science', 'lang']
        category = random.choice(categories)
        self.client.get(f"/courses/?category={category}")
    
    @task(1)
    def view_registrations(self):
        """View my registrations"""
        self.client.get("/my-registrations/")
    
    @task(1)
    def search_courses(self):
        """Search courses"""
        search_terms = ['python', 'design', 'business', 'language']
        term = random.choice(search_terms)
        self.client.get(f"/courses/?search={term}")

# To run: locust -f locustfile.py --host=http://localhost:8000
'''

print("Enhanced Django Course Registration System completed!")
print("\n=== Key Improvements Made ===")
print("✅ Enhanced Models with proper relationships and validation")
print("✅ Improved Authentication system with better error handling") 
print("✅ Modern responsive UI with Bootstrap 5")
print("✅ Comprehensive admin interface")
print("✅ Multi-step registration process")
print("✅ Course filtering and pagination")
print("✅ User dashboard with statistics")
print("✅ Proper error handling and logging")
print("✅ Security enhancements")
print("✅ Comprehensive test suite")
print("✅ Docker configuration for deployment")
print("✅ CI/CD pipeline with GitHub Actions")
print("✅ Production-ready settings")
print("✅ API endpoints for mobile integration")
print("✅ Performance monitoring")
print("✅ Backup and deployment scripts")

print("\n=== Fixed Issues ===")
print("🔧 Fixed model relationships and constraints")
print("🔧 Improved form validation with better error messages")
print("🔧 Enhanced security with CSRF protection and input validation")
print("🔧 Fixed authentication flow and session management")
print("🔧 Improved URL routing and view logic")
print("🔧 Added proper error pages (404, 500)")
print("🔧 Fixed database queries for better performance")
print("🔧 Added proper logging and monitoring")

print("\n=== Next Steps ===")
print("1. Run migrations: python manage.py makemigrations && python manage.py migrate")
print("2. Create superuser: python manage.py createsuperuser")
print("3. Populate sample data: python manage.py populate_courses")
print("4. Run tests: python manage.py test")
print("5. Start development server: python manage.py runserver")