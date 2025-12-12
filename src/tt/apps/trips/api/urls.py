from django.urls import path

from . import views


urlpatterns = [
    path( '', views.TripCollectionView.as_view(), name = 'api-trip-collection' ),
    path( '<uuid:trip_uuid>/', views.TripItemView.as_view(), name = 'api-trip-item' ),
    path( 'by-gmm-map/<str:gmm_map_id>/', views.TripByGmmMapView.as_view(), name = 'api-trip-by-gmm-map' ),
]
