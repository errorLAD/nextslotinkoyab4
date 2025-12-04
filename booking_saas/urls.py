"""
URL configuration for booking_saas project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from subscriptions.urls import webhook_urlpatterns
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Landing page
    path('', TemplateView.as_view(template_name='landing.html'), name='home'),
    
    # App URLs
    path('accounts/', include('accounts.urls')),
    path('provider/', include('providers.urls')),
    path('appointments/', include('appointments.urls')),
    path('pricing/', include('subscriptions.urls')),
]

# Add webhook URLs (outside app namespace)
urlpatterns += webhook_urlpatterns

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customize admin site
admin.site.site_header = "BookingSaaS Admin"
admin.site.site_title = "BookingSaaS Admin Portal"
admin.site.index_title = "Welcome to BookingSaaS Administration"
