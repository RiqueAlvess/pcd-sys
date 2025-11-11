from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import landing

urlpatterns = [
    path('', landing, name='landing'),
    path('admin/', admin.site.urls, name='adminpage'),
    path('core/', include('core.urls')),
    path('userpcd/', include('userpcd.urls')),
    path('usercompany/', include('usercompany.urls')),

    # API REST endpoints
    path('api/pcd/', include('userpcd.urls_api')),
    path('api/empresa/', include('usercompany.urls_api')),
]

# Servir arquivos de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)