from django.db import models


class Etudiant(models.Model):
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    date_naissance = models.DateField()

    def __str__(self):
        return self.nom


class Cours(models.Model):
    nom = models.CharField(max_length=100)
    prix = models.DecimalField(max_digits=7, decimal_places=2)
    duree = models.CharField(max_length=50)  
    resume = models.TextField()
    def __str__(self):
        return self.nom
        