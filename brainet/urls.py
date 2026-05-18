from django.contrib import admin
from django.urls import path, include
from schools.views import landing_page
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [

    # admin panel
    path('admin/', admin.site.urls),

    # landing page (public entry)
    path('', landing_page, name='landing'),

    # users app (login, dashboard, auth)
    path('users/', include('users.urls')),

    # schools app (school management, vouchers, DOS, etc.)
    path('schools/', include('schools.urls')),
    path('students/', include('students.urls')),
]

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)

