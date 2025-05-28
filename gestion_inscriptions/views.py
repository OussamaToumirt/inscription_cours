# views.py - Add these to your existing views.py file

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import Etudiant, Cours

def auth_view(request):
    """Display the authentication page"""
    if request.user.is_authenticated:
        return redirect('etape1')  # Redirect to your main app if already logged in
    return render(request, 'auths.html')

@csrf_exempt
def login_view(request):
    """Handle login requests"""
    if request.method == 'POST':
        try:
            # Handle both form data and JSON data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                email = data.get('email')
                password = data.get('password')
                remember_me = data.get('remember_me', False)
            else:
                email = request.POST.get('email')
                password = request.POST.get('password')
                remember_me = request.POST.get('remember-me') == 'on'
            
            if not email or not password:
                return JsonResponse({
                    'success': False,
                    'error': 'Email and password are required'
                }, status=400)
            
            # Try to find user by email (since Django uses username by default)
            try:
                user = User.objects.get(email=email)
                username = user.username
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid email or password'
                }, status=400)
            
            # Authenticate user
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Set session expiry based on remember me
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires when browser closes
                else:
                    request.session.set_expiry(1209600)  # 2 weeks
                
                return JsonResponse({
                    'success': True,
                    'message': 'Login successful',
                    'redirect_url': '/etape1/'  # Adjust this to your main page
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
            return JsonResponse({
                'success': False,
                'error': 'An error occurred during login'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@csrf_exempt
def signup_view(request):
    """Handle signup requests"""
    if request.method == 'POST':
        try:
            # Handle both form data and JSON data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                name = data.get('name')
                email = data.get('email')
                password = data.get('password')
                confirm_password = data.get('confirm_password')
                terms = data.get('terms', False)
            else:
                name = request.POST.get('name')
                email = request.POST.get('email')
                password = request.POST.get('password')
                confirm_password = request.POST.get('confirm-password')
                terms = request.POST.get('terms') == 'on'
            
            # Validation
            errors = {}
            
            if not name:
                errors['name'] = 'Name is required'
            
            if not email:
                errors['email'] = 'Email is required'
            elif User.objects.filter(email=email).exists():
                errors['email'] = 'Email already exists'
            
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
            user = User.objects.create_user(
                username=email,  # Use email as username
                email=email,
                password=password,
                first_name=name.split()[0] if name.split() else name,
                last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            )
            
            # Auto login after signup
            user = authenticate(request, username=email, password=password)
            if user:
                login(request, user)
            
            return JsonResponse({
                'success': True,
                'message': 'Account created successfully',
                'redirect_url': '/etape1/'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'An error occurred during signup'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

def logout_view(request):
    """Handle logout requests"""
    logout(request)
    return redirect('auth')

# Update your existing views to require authentication
@login_required
def etape1_view(request):
    if request.method == "POST":
        nom = request.POST.get('nom')
        email = request.POST.get('email')
        telephone = request.POST.get('telephone')
        date_naissance = request.POST.get('date_naissance')

        request.session['etudiant'] = {
            'nom': nom,
            'email': email,
            'telephone': telephone,
            'date_naissance': date_naissance,
        }

        return redirect('etape2')

    return render(request, 'etape1_etudiant.html')

@login_required
def etape2_view(request):
    cours = Cours.objects.filter().values('id', 'nom', 'prix', 'duree','resume')
    if request.method == "POST":
        cours_choisi_id = request.POST.get('cours_id')
        request.session['cours_choisi_id'] = cours_choisi_id
        return redirect('confirmation')

    return render(request, 'etape2.html', {'cours': cours})

@login_required
def confirmation_view(request):
    etudiant_data = request.session.get('etudiant')
    cours_id = request.session.get('cours_choisi_id')

    if not etudiant_data or not cours_id:
        return redirect('etape1')

    cours_disponibles = Cours.objects.filter(id=cours_id).values('id', 'nom', 'prix', 'duree','resume')

    cours_choisi = cours_disponibles.get(cours_id)
    if not cours_choisi:
        return redirect('etape2')

    if request.method == "POST":
        etudiant_obj = Etudiant.objects.create(
            nom=etudiant_data['nom'],
            email=etudiant_data['email'],
            telephone=etudiant_data['telephone'],
            date_naissance=etudiant_data['date_naissance']
        )
        request.session.flush()

        return render(request, 'confirmation_success.html', {
            'etudiant': etudiant_obj,
            'cours': cours_choisi
        })

    return render(request, 'confirmation.html', {
        'etudiant': etudiant_data,
        'cours': cours_choisi
    })