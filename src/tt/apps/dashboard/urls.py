from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r'^$', views.DashboardHomeView.as_view(), name='dashboard_home'),
]
