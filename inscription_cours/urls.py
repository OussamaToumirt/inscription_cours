from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def redirect_to_etape1(request):
    return redirect('etape1')  # redirige la racine vers /etape1/

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('gestion_inscriptions.urls')),  # inclut urls de l'app
]
