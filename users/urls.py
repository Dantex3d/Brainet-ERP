from django.urls import path
from . import views

urlpatterns = [

    # HOME → go to login (clean entry point)
    path(
        '',
        views.CustomLoginView.as_view(),
        name='home'
    ),

    # LOGIN
    path(
        'login/',
        views.CustomLoginView.as_view(),
        name='login'
    ),

    # DASHBOARD (SINGLE SOURCE OF TRUTH)
    path(
        'dashboards/',
        views.dashboard,
        name='dashboard'
    ),

    path(
        'superuser/two-factor/',
        views.superuser_two_factor,
        name='superuser_two_factor'
    ),

    path(
        'account/',
        views.account_profile,
        name='account_profile'
    ),
    path(
        'resend-verification/',
        views.resend_verification_email,
        name='resend_verification_email'
    ),
    path(
        'verify-email/<str:token>/',
        views.verify_user_email,
        name='verify_user_email'
    ),
    path(
        'verify-code/',
        views.verify_user_code,
        name='verify_user_code'
    ),
    path(
        'resend-code/',
        views.resend_verification_code,
        name='resend_verification_code'
    ),
    path('logout/', views.custom_logout, name='logout')
]