# Enhanced forms.py - Fixed version
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Count, Q, F
from .models import Etudiant, Cours, Inscription
from datetime import date, timedelta

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    first_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user

class EtudiantForm(forms.ModelForm):
    class Meta:
        model = Etudiant
        fields = ['nom', 'email', 'telephone', 'date_naissance', 'address']
        labels = {
            'nom': 'Full Name',
            'email': 'Email Address',
            'telephone': 'Phone Number',
            'date_naissance': 'Date of Birth',
            'address': 'Address (Optional)'
        }
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your full name',
                'required': True,
                'minlength': '2'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com',
                'required': True
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1234567890 or 0123456789',
                'required': True,
                'pattern': r'[\+]?[0-9\s\-\(\)]+'
            }),
            'date_naissance': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Your address (optional)'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set date limits
        today = date.today()
        min_date = today - timedelta(days=100*365)  # 100 years ago
        max_date = today - timedelta(days=16*365)   # 16 years ago
        
        self.fields['date_naissance'].widget.attrs.update({
            'min': min_date.strftime('%Y-%m-%d'),
            'max': max_date.strftime('%Y-%m-%d')
        })
    
    def clean_nom(self):
        nom = self.cleaned_data.get('nom', '').strip()
        if len(nom) < 2:
            raise forms.ValidationError("Name must be at least 2 characters long.")
        if not nom.replace(' ', '').isalpha():
            raise forms.ValidationError("Name should only contain letters and spaces.")
        return nom
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if email is already used by another student (excluding current instance)
        queryset = Etudiant.objects.filter(email=email)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise forms.ValidationError("A student with this email already exists.")
        return email
    
    def clean_telephone(self):
        telephone = self.cleaned_data.get('telephone', '').strip()
        # Remove spaces and special characters for validation
        clean_phone = ''.join(char for char in telephone if char.isdigit() or char == '+')
        
        if len(clean_phone) < 10:
            raise forms.ValidationError("Phone number must be at least 10 digits long.")
        if len(clean_phone) > 15:
            raise forms.ValidationError("Phone number cannot exceed 15 digits.")
        
        return telephone
    
    def clean_date_naissance(self):
        date_naissance = self.cleaned_data.get('date_naissance')
        if not date_naissance:
            raise forms.ValidationError("Date of birth is required.")
        
        today = date.today()
        age = today.year - date_naissance.year - ((today.month, today.day) < (date_naissance.month, date_naissance.day))
        
        if age < 16:
            raise forms.ValidationError("You must be at least 16 years old to register.")
        if age > 100:
            raise forms.ValidationError("Please enter a valid birth date.")
        
        # Check if date is not in the future
        if date_naissance > today:
            raise forms.ValidationError("Birth date cannot be in the future.")
        
        return date_naissance

class CoursChoiceForm(forms.Form):
    cours = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        empty_label=None,
        required=True,
        label="Select a Course"
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Get available courses
        available_courses = Cours.objects.filter(is_active=True).annotate(
            enrolled_count=Count('inscriptions', filter=Q(inscriptions__status='confirmed'))
        )
        
        # Filter out full courses (unless max_students is 0 which means unlimited)
        available_courses = available_courses.filter(
            Q(max_students__gt=F('enrolled_count')) | Q(max_students=0)
        )
        
        # If user is provided, exclude courses they're already enrolled in
        if user and hasattr(user, 'etudiant'):
            try:
                etudiant = user.etudiant
                enrolled_course_ids = Inscription.objects.filter(
                    etudiant=etudiant
                ).values_list('cours_id', flat=True)
                available_courses = available_courses.exclude(id__in=enrolled_course_ids)
            except Etudiant.DoesNotExist:
                pass
        
        self.fields['cours'].queryset = available_courses.order_by('category', 'nom')
        
        # If no courses available, show a helpful message
        if not available_courses.exists():
            self.fields['cours'].empty_label = "No courses available at the moment"
            self.fields['cours'].required = False
    
    def clean_cours(self):
        cours = self.cleaned_data.get('cours')
        if not cours:
            return cours
        
        # Double-check course availability
        if not cours.is_active:
            raise forms.ValidationError("This course is no longer available.")
        
        # Check if course is full
        if cours.max_students > 0 and cours.available_slots <= 0:
            raise forms.ValidationError("This course is full. Please select another course.")
        
        return cours

class InscriptionForm(forms.ModelForm):
    """Form for admin to manage inscriptions"""
    class Meta:
        model = Inscription
        fields = ['etudiant', 'cours', 'status', 'payment_status', 'notes']
        widgets = {
            'etudiant': forms.Select(attrs={'class': 'form-control'}),
            'cours': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'payment_status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes...'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        etudiant = cleaned_data.get('etudiant')
        cours = cleaned_data.get('cours')
        
        if etudiant and cours:
            # Check for duplicate inscription (excluding current instance)
            existing = Inscription.objects.filter(etudiant=etudiant, cours=cours)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise forms.ValidationError(
                    f"{etudiant.nom} is already enrolled in {cours.nom}"
                )
            
            # Check course capacity
            if cours.max_students > 0:
                confirmed_count = Inscription.objects.filter(
                    cours=cours, 
                    status='confirmed'
                ).count()
                
                if self.instance.pk and self.initial.get('status') == 'confirmed':
                    confirmed_count -= 1  # Don't count current instance if it was confirmed
                
                if (cleaned_data.get('status') == 'confirmed' and 
                    confirmed_count >= cours.max_students):
                    raise forms.ValidationError(
                        f"Course {cours.nom} is full (max {cours.max_students} students)"
                    )
        
        return cleaned_data

class ContactForm(forms.Form):
    """Contact form for general inquiries"""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your full name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject of your message'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Your message...'
        })
    )
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters long.")
        return name
    
    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if len(message) < 10:
            raise forms.ValidationError("Message must be at least 10 characters long.")
        return message

class CourseSearchForm(forms.Form):
    """Form for searching and filtering courses"""
    CATEGORY_CHOICES = [('', 'All Categories')] + Cours.CATEGORY_CHOICES
    
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search courses...'
        })
    )
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    min_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price',
            'step': '0.01'
        })
    )
    max_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price',
            'step': '0.01'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        
        if min_price and max_price and min_price > max_price:
            raise forms.ValidationError("Minimum price cannot be greater than maximum price.")
        
        return cleaned_data