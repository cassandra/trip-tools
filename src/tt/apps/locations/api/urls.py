from django.urls import path

from .views import LocationCollectionView, LocationItemView


urlpatterns = [
    path( '', LocationCollectionView.as_view(), name = 'api_location_collection' ),
    path( '<uuid:location_uuid>/', LocationItemView.as_view(), name = 'api_location_item' ),
]
