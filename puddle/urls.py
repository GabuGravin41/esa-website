from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('core.urls')),
    # Comment out non-existent apps
    # path('inbox/', include('conversation.urls')),
    # path('dashboard/', include('dashboard.urls')),
    # path('items/', include('item.urls')),
    path('accounts/', include('allauth.urls')),
    path('account/', include('accounts.urls')),  # Include custom accounts app URLs
    path('admin/', admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
]

# Add media URL configuration in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)