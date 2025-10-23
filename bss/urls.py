from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from django.conf import settings

handler404 = 'hr.views.handler404'

urlpatterns = [
    path('', include('hr.urls')),
    path('leave/', include('leave.urls')),
    path('setup/', include('setup.urls')),
    path('ledger/', include('ledger.urls')),
    path('admin/', admin.site.urls),
    path('medical/', include('medical.urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
