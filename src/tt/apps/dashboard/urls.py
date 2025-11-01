from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r'^$', views.DashboardView.as_view(), name='dashboard_home'),
]
