from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('core.urls')),
    #path('accounts/', include('allauth.urls')),
    path('accounts/', include('accounts.urls')),  
    path('admin/', admin.site.urls),
]

# Add browser reload for development
if settings.DEBUG:
    urlpatterns.append(path("__reload__/", include("django_browser_reload.urls")))

# Add media and static URL configuration for both development and production
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)