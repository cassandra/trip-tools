from django.urls import include, re_path

from . import views


urlpatterns = [

    re_path( r'^$',
             views.TestingHomeView.as_view(),
             name='testing_home' ),

    re_path( r'^signin/$',
             views.E2ESigninView.as_view(),
             name='testing_e2e_signin' ),

    re_path( r'^ui/', include( 'tt.testing.ui.urls' ) ),
    re_path( r'^devtools/', include( 'tt.testing.devtools.urls' ) ),

]
