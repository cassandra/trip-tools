"""
URL configuration for itineraries app.
"""

from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^trip/(?P<trip_id>\d+)/itinerary/$', views.ItineraryHomeView.as_view(), name='itineraries_home'),
]
