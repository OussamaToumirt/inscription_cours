# Enhanced views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import transaction
from django.urls import reverse
import json
import logging
from .models import Etudiant, Cours, Inscription
from .forms import EtudiantForm, CoursChoiceForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

def auth_view(request):
    """Display the authentication page"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'auths.html')

@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    """Handle login requests with improved error handling"""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            email = data.get('email', '').strip()
            password = data.get('password', '')
            remember_me = data.get('remember_me', False)
        else:
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '')
            remember_me = request.POST.get('remember-me') == 'on'
        
        if not email or not password:
            return JsonResponse({
                'success': False,
                'error': 'Email and password are required'
            }, status=400)
        
        # Find user by email
        try:
            User = get_user_model()
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid email or password'
            }, status=400)
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_active:
            login(request, user)
            
            # Set session expiry
            if not remember_me:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600)  # 2 weeks
            
            logger.info(f"User {email} logged in successfully")
            return JsonResponse({
                'success': True,
                'message': 'Login successful',
                'redirect_url': reverse('dashboard')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid email or password'
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred during login'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def signup_view(request):
    """Handle signup requests with improved validation"""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        terms = data.get('terms', False)
        
        # Validation
        errors = {}
        
        if not name:
            errors['name'] = 'Name is required'
        elif len(name) < 2:
            errors['name'] = 'Name must be at least 2 characters'
        
        if not email:
            errors['email'] = 'Email is required'
        elif User.objects.filter(email=email).exists():
            errors['email'] = 'Email already exists'
        
        # Password validation
        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters'
        elif not any(c.isupper() for c in password):
            errors['password'] = 'Password must contain at least one uppercase letter'
        elif not any(c.isdigit() for c in password):
            errors['password'] = 'Password must contain at least one number'
        elif not any(c in '!@#$%^&*(),.?":{}|<>' for c in password):
            errors['password'] = 'Password must contain at least one special character'
        
        if password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match'
        
        if not terms:
            errors['terms'] = 'You must accept the terms and conditions'
        
        if errors:
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        
        # Create user
        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=name.split()[0] if name.split() else name,
                last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            )
            
            # Auto login after signup
            user = authenticate(request, username=email, password=password)
            if user:
                login(request, user)
        
        logger.info(f"New user {email} registered successfully")
        return JsonResponse({
            'success': True,
            'message': 'Account created successfully',
            'redirect_url': reverse('dashboard')
        })
        
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred during signup'
        }, status=500)

@login_required
def logout_view(request):
    """Handle logout requests"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('auth')

@login_required
def dashboard_view(request):
    """User dashboard showing enrolled courses and available courses"""
    user_student = None
    user_inscriptions = []
    
    try:
        user_student = Etudiant.objects.get(user=request.user)
        user_inscriptions = Inscription.objects.filter(etudiant=user_student).select_related('cours')
    except Etudiant.DoesNotExist:
        pass
    
    available_courses = Cours.objects.filter(is_active=True)[:6]  # Show 6 latest courses
    
    context = {
        'user_student': user_student,
        'user_inscriptions': user_inscriptions,
        'available_courses': available_courses,
    }
    return render(request, 'dashboard.html', context)

@login_required
def etape1_view(request):
    """Step 1: Student information form"""
    # Check if user already has a student profile
    try:
        student = Etudiant.objects.get(user=request.user)
        # If student exists, redirect to course selection
        return redirect('etape2')
    except Etudiant.DoesNotExist:
        pass
    
    if request.method == "POST":
        form = EtudiantForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    student = form.save(commit=False)
                    student.user = request.user
                    student.save()
                    
                    messages.success(request, 'Your information has been saved successfully!')
                    return redirect('etape2')
            except Exception as e:
                logger.error(f"Error saving student: {str(e)}")
                messages.error(request, 'An error occurred while saving your information.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Pre-fill form with user data
        initial_data = {
            'nom': f"{request.user.first_name} {request.user.last_name}".strip(),
            'email': request.user.email,
        }
        form = EtudiantForm(initial=initial_data)
    
    return render(request, 'etape1_etudiant.html', {'form': form})

@login_required
def etape2_view(request):
    """Step 2: Course selection"""
    try:
        student = Etudiant.objects.get(user=request.user)
    except Etudiant.DoesNotExist:
        messages.error(request, 'Please complete your profile first.')
        return redirect('etape1')
    
    if request.method == "POST":
        form = CoursChoiceForm(request.POST)
        if form.is_valid():
            cours = form.cleaned_data['cours']
            
            # Check if already enrolled
            if Inscription.objects.filter(etudiant=student, cours=cours).exists():
                messages.warning(request, 'You are already enrolled in this course.')
                return redirect('dashboard')
            
            # Check available slots
            if cours.available_slots <= 0:
                messages.error(request, 'This course is full. Please choose another course.')
                return render(request, 'etape2.html', {'form': form})
            
            # Store course selection in session
            request.session['selected_course_id'] = cours.id
            return redirect('confirmation')
    else:
        form = CoursChoiceForm()
    
    return render(request, 'etape2.html', {'form': form})

@login_required
def confirmation_view(request):
    """Step 3: Confirmation of registration"""
    try:
        student = Etudiant.objects.get(user=request.user)
    except Etudiant.DoesNotExist:
        messages.error(request, 'Please complete your profile first.')
        return redirect('etape1')
    
    course_id = request.session.get('selected_course_id')
    if not course_id:
        messages.error(request, 'Please select a course first.')
        return redirect('etape2')
    
    try:
        cours = Cours.objects.get(id=course_id, is_active=True)
    except Cours.DoesNotExist:
        messages.error(request, 'Selected course is not available.')
        return redirect('etape2')
    
    if request.method == "POST":
        try:
            with transaction.atomic():
                # Final check for availability
                if cours.available_slots <= 0:
                    messages.error(request, 'This course is full.')
                    return redirect('etape2')
                
                # Create inscription
                inscription = Inscription.objects.create(
                    etudiant=student,
                    cours=cours,
                    status='confirmed'
                )
                
                # Clear session
                request.session.pop('selected_course_id', None)
                
                messages.success(request, 'Registration completed successfully!')
                return render(request, 'confirmation_success.html', {
                    'etudiant': student,
                    'cours': cours,
                    'inscription': inscription
                })
                
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            messages.error(request, 'An error occurred during registration.')
    
    context = {
        'etudiant': student,
        'cours': cours,
    }
    return render(request, 'confirmation.html', context)

@login_required
def courses_list_view(request):
    """List all available courses with pagination and filtering"""
    courses = Cours.objects.filter(is_active=True)
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        courses = courses.filter(category=category)
    
    # Search
    search = request.GET.get('search')
    if search:
        courses = courses.filter(nom__icontains=search)
    
    # Pagination
    paginator = Paginator(courses, 9)  # 9 courses per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': Cours.CATEGORY_CHOICES,
        'current_category': category,
        'search_query': search,
    }
    return render(request, 'courses_list.html', context)

@login_required
def my_registrations_view(request):
    """View user's registrations"""
    try:
        student = Etudiant.objects.get(user=request.user)
        inscriptions = Inscription.objects.filter(etudiant=student).select_related('cours').order_by('-inscription_date')
    except Etudiant.DoesNotExist:
        inscriptions = []
        student = None
    
    return render(request, 'my_registrations.html', {
        'inscriptions': inscriptions,
        'student': student
    })
