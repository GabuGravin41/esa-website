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
if getattr(settings, 'ENABLE_DEBUG_TOOLBAR', False):
    try:
        import django_browser_reload
        urlpatterns.append(path("__reload__/", include("django_browser_reload.urls")))
    except ImportError:
        pass

    # Register Django Debug Toolbar URLs when available
    try:
        import debug_toolbar
        urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
    except ImportError:
        pass

# Add media and static URL configuration for both development and production
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)