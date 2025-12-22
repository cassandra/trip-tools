from django.urls import path

from . import views


urlpatterns = [
    path( '', views.LocationCollectionView.as_view(), name = 'api_location_collection' ),
    path( '<uuid:location_uuid>/', views.LocationItemView.as_view(), name = 'api_location_item' ),
    path(
        'by-gmm-id/<uuid:trip_uuid>/<str:gmm_id>/',
        views.LocationByGmmIdView.as_view(),
        name = 'api_location_by_gmm_id',
    ),
]
