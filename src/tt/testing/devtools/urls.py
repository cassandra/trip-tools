import importlib

from django.apps import apps
from django.urls import include, re_path

from . import views


def get_tests_devtools_urls():
    urlpatterns = []
    for app_config in apps.get_app_configs():
        try:
            module = importlib.import_module( f'{app_config.name}.tests.devtools.urls' )
            short_name = app_config.name.split('.')[-1]
            urlpatterns.append( re_path( f'{short_name}/', include(module) ))
        except ModuleNotFoundError:
            pass
        continue
    return urlpatterns


urlpatterns = [
    re_path( r'^$',
             views.DevtoolsHomeView.as_view(), 
             name='testing_devtools_home'),
]

urlpatterns += get_tests_devtools_urls()



