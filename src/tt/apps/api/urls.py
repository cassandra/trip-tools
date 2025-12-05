from django.urls import path, include

from .views import TokenListView, TokenDetailView, CurrentUserView


urlpatterns = [
    # Routes handled by API module directly
    path('v1/tokens/', TokenListView.as_view(), name='api-token-list'),
    path('v1/tokens/<str:lookup_key>/', TokenDetailView.as_view(), name='api-token-detail'),
    path('v1/me/', CurrentUserView.as_view(), name='api-current-user'),

    # Feature-specific delegated API routes
    path('v1/locations/', include('tt.apps.locations.api.urls')),
]
