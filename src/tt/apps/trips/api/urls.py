from django.urls import path

from .views import TripCollectionView, TripItemView


urlpatterns = [
    path( '', TripCollectionView.as_view(), name = 'api-trip-collection' ),
    path( '<uuid:trip_uuid>/', TripItemView.as_view(), name = 'api-trip-item' ),
]
