from django.urls import path

from . import views


urlpatterns = [
    path(
        'create',
        views.TripCreateModalView.as_view(),
        name='trips_create'
    ),
    path(
        '<uuid:trip_uuid>',
        views.TripHomeView.as_view(),
        name='trips_home'
    ),
]
