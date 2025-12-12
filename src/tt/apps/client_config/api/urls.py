from django.urls import path

from . import views


urlpatterns = [
    path('', views.ClientConfigView.as_view(), name='api_client_config'),
]
