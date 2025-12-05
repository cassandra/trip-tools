from django.urls import path

from .views import LocationListView


urlpatterns = [
    path('location/trip/<uuid:trip_uuid>/', LocationListView.as_view(), name='api-location-list'),
]
