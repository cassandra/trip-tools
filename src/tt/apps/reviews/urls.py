from django.urls import path

from . import views


urlpatterns = [
    path(r'trip/<uuid:trip_uuid>', views.ReviewsHomeView.as_view(), name='reviews_home'),
]
