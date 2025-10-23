from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$',
             views.TestUiNotifyHomeView.as_view(), 
             name='notify_tests_ui'),

    re_path( r'^email/view/(?P<email_type>\w+)$',
             views.TestUiViewEmailView.as_view(), 
             name='notify_tests_ui_view_email'),
]
