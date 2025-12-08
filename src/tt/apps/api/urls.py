from django.urls import path, include

from .views import TokenCollectionView, TokenItemView, CurrentUserView


urlpatterns = [
    # Routes handled by API module directly
    path('v1/tokens/', TokenCollectionView.as_view(), name='api-token-collection'),
    path('v1/tokens/<str:lookup_key>/', TokenItemView.as_view(), name='api-token-item'),
    path('v1/me/', CurrentUserView.as_view(), name='api-current-user'),

    # Feature-specific delegated API routes
    path('v1/locations/', include('tt.apps.locations.api.urls')),
]
