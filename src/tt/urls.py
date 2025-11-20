from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView

from . import views

urlpatterns = [

    # Favicons are tricky to get 100% right and some browsers will try
    # this no matter what.
    re_path( r'^favicon.ico$',
             RedirectView.as_view( url = staticfiles_storage.url('favicon.ico'),
                                   permanent = False),
             name="favicon"
             ),

    re_path(r'^(?P<filename>(service-worker.js))$',
            views.home_javascript_files, name='home-javascript-files'),

    re_path( r'^manifest.json$', views.ManifestView.as_view(), name='manifest' ),


    path('admin/', admin.site.urls),

    re_path( r'^$', views.HomeView.as_view(), name='home' ),
    re_path( r'^index.html$', views.HomeView.as_view(), name='home_index' ),
    re_path( r'^start$', views.StartView.as_view(), name='start' ),
    re_path( r'^health$', views.HealthView.as_view(), name='health' ),

    re_path( r'^env/', include('tt.environment.urls' )),
    re_path( r'^user/', include('tt.apps.user.urls' )),
    re_path( r'^config/', include('tt.apps.config.urls' )),
    re_path( r'^notify/', include('tt.apps.notify.urls' )),
    re_path( r'^dashboard/', include('tt.apps.dashboard.urls' )),
    re_path( r'^trips/', include('tt.apps.trips.urls' )),
    re_path( r'^itineraries/', include('tt.apps.itineraries.urls' )),
    re_path( r'^notebook/', include('tt.apps.notebook.urls' )),
    re_path( r'^images/', include('tt.apps.images.urls' )),
    re_path( r'^journal/', include('tt.apps.journal.urls' )),
    re_path( r'^travelog/', include('tt.apps.travelog.urls' )),
    re_path( r'^', include('tt.apps.members.urls' )),

    # Custom error pages
    re_path( r'^400.html$', views.bad_request_response, name='bad_request' ),
    re_path( r'^403.html$', views.not_authorized_response, name='not_authorized' ),
    re_path( r'^404.html$', views.page_not_found_response, name='page_not_found' ),
    re_path( r'^405.html$', views.method_not_allowed_response, name='method_not_allowed' ),
    re_path( r'^500.html$', views.internal_error_response, name='internal_error' ),
    re_path( r'^503.html$', views.transient_error_response, name='transient_error' ),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'tt.views.custom_404_handler'


if settings.DEBUG:
    urlpatterns += [
        re_path( r'^testing/', include('tt.testing.urls' )),
    ]
