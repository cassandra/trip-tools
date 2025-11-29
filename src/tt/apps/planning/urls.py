from django.urls import path

from . import views


urlpatterns = [
    path(r'trip/<uuid:trip_uuid>', views.PlanningHomeView.as_view(), name='planning_home'),
]
