# Enhanced models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator
from decimal import Decimal

class Cours(models.Model):
    CATEGORY_CHOICES = [
        ('tech', 'Technology'),
        ('lang', 'Languages'),
        ('arts', 'Arts & Design'),
        ('business', 'Business'),
        ('science', 'Science'),
    ]
    
    nom = models.CharField(max_length=150, verbose_name="Course Name")
    prix = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Price"
    )
    duree = models.CharField(max_length=100, verbose_name="Duration")
    resume = models.TextField(verbose_name="Description")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='tech')
    max_students = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        ordering = ['nom']
    
    def __str__(self):
        return self.nom
    
    @property
    def enrolled_count(self):
        return self.inscriptions.filter(status='confirmed').count()
    
    @property
    def available_slots(self):
        return self.max_students - self.enrolled_count

class Etudiant(models.Model):
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nom = models.CharField(max_length=100, verbose_name="Full Name")
    email = models.EmailField(unique=True, verbose_name="Email Address")
    telephone = models.CharField(validators=[phone_regex], max_length=20, verbose_name="Phone Number")
    date_naissance = models.DateField(verbose_name="Date of Birth")
    address = models.TextField(blank=True, null=True, verbose_name="Address")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"
        ordering = ['nom']
    
    def __str__(self):
        return self.nom
    
    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_naissance.year - ((today.month, today.day) < (self.date_naissance.month, self.date_naissance.day))

class Inscription(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, related_name='inscriptions')
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='inscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    inscription_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('etudiant', 'cours')
        verbose_name = "Registration"
        verbose_name_plural = "Registrations"
        ordering = ['-inscription_date']
    
    def __str__(self):
        return f"{self.etudiant.nom} - {self.cours.nom}"