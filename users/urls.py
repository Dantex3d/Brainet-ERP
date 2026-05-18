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
    
    path('logout/', views.custom_logout, name='logout')
    
    
]