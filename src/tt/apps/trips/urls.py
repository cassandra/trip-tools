from django.urls import path

from . import views


urlpatterns = [
    path(
        '',
        views.TripsHomeView.as_view(),
        name='trips_home'
    ),
    path(
        'create',
        views.TripCreateModalView.as_view(),
        name='trips_trip_create'
    ),
    path(
        '<uuid:trip_uuid>',
        views.TripOverviewView.as_view(),
        name='trips_trip_overview'
    ),
    path(
        '<uuid:trip_uuid>/edit',
        views.TripEditModalView.as_view(),
        name='trips_trip_edit'
    ),
    path(
        '<uuid:trip_uuid>/reference-image-picker/',
        views.TripImagePickerView.as_view(),
        name='trips_trip_image_picker'
    ),
    path(
        '<uuid:trip_uuid>/upload-image/',
        views.TripImageUploadView.as_view(),
        name='trips_trip_image_upload'
    ),
]
