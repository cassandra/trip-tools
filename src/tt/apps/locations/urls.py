from django.urls import path

from . import views


urlpatterns = [
    path(r'trip/<uuid:trip_uuid>', views.LocationsHomeView.as_view(), name='locations_home'),
]
