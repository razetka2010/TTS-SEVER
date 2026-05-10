from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.templatetags.static import static as static_url

urlpatterns = [
    path(
        'favicon.ico',
        RedirectView.as_view(url=static_url('logo.svg'), permanent=False),
    ),
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('requests/', include('apps.requests.urls')),
    path('', lambda request: redirect('my_requests')),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
