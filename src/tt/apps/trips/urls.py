from django.urls import path

from . import views


urlpatterns = [
    path(
        '',
        views.TripsAllView.as_view(),
        name='trips_all'
    ),
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
    path(
        '<uuid:trip_uuid>/edit',
        views.TripEditModalView.as_view(),
        name='trips_edit'
    ),
    path(
        '<uuid:trip_uuid>/reference-image-picker/',
        views.TripReferenceImagePickerView.as_view(),
        name='trip_reference_image_picker'
    ),
    path(
        '<uuid:trip_uuid>/upload-image/',
        views.TripImageUploadView.as_view(),
        name='trip_image_upload'
    ),
]
