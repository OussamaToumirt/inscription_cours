from django.contrib import admin
from .models import Cours, Etudiant

admin.site.register(Etudiant)

class CoursAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom', 'prix', 'duree', 'resume')
    list_filter = ('nom', 'prix', 'duree','resume')
    search_fields = ('nom', 'prix', 'duree','resume')
    

admin.site.register(Cours, CoursAdmin)