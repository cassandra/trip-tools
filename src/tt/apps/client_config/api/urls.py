from django.urls import path

from .views import ClientConfigView


urlpatterns = [
    path('', ClientConfigView.as_view(), name='api_client_config'),
]
