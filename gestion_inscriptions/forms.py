from django import forms
from .models import Etudiant

class EtudiantForm(forms.ModelForm):
    class Meta:
        model = Etudiant
        fields = ['nom', 'email', 'telephone', 'date_naissance']

from django import forms

class InfosPersonnellesForm(forms.Form):
    nom = forms.CharField(label='Nom', max_length=100)
    prenom = forms.CharField(label='Prénom', max_length=100)
    email = forms.EmailField(label='Email')
    