"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin # Importa o módulo de administração do Django
from django.urls import path, include # Importa a função include, que vai permitir incluir as URLs do app principal
from django.conf import settings # Importa as configurações do projeto
from django.conf.urls.static import static # Importa a função static, que vai permitir servir arquivos estáticos (como imagens) durante o desenvolvimento

urlpatterns = [
    path('splixson/', admin.site.urls), # Estamos dizendo: "Qualquer endereço que não seja o /admin, mande para as URLs do 'app'"
    path('', include('app.urls')),
    path('master/', include('master_control.urls')), # Adicionando as URLs do app master_control
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)