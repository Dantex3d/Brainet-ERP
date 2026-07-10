from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from users import views as user_views
from schools.views import landing_page
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.sitemaps.views import sitemap
from sitemaps import StaticSitemap


urlpatterns = [
    path("admin/", admin.site.urls),

    # Authentication
    path("login/", LoginView.as_view(template_name="teachers/login.html"), name="login"),


    # Teachers app
    path("teachers/", include("teachers.urls")),
]

urlpatterns = [

    # admin panel
    path('admin/', admin.site.urls),

    # landing page (public entry)
    path('', landing_page, name='landing'),

    # users app (login, dashboard, auth)
    path('users/', include('users.urls')),
    path("superuser/create-user/", user_views.create_custom_user, name="create_custom_user"),
    path("exams/", include("exams.urls")),
    path("assignments/", include("assignments.urls")),
    path("subjects/", include("subjects.urls")),
    path("fees/", include("fees.urls")),


    # schools app (school management, vouchers, DOS, etc.)
    path('schools/', include('schools.urls')),
    path('students/', include('students.urls')),
    path('teachers/', include('teachers.urls')),
    path('sitemaps.xml', sitemap, {'sitemaps': {'static': StaticSitemap()}}, name='django.contrib.sitemaps.views.sitemap'),
    path('sitemaps', sitemap, {'sitemaps': {'static': StaticSitemap()}}, name='django.contrib.sitemaps.views.sitemap-plain'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )



