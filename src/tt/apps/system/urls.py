from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^info$', 
             views.SystemInfoView.as_view(), 
             name = 'system_info' ),
]
