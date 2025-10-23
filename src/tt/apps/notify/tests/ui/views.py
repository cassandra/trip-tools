from typing import Dict

from django.shortcuts import render
from django.views.generic import View

from tt.apps.notify.tests.synthetic_data import NotifySyntheticData

from tt.testing.ui.email_test_views import EmailTestViewView


class TestUiNotifyHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "notify/tests/ui/home.html", context )

    
class TestUiViewEmailView( EmailTestViewView ):

    @property
    def app_name(self):
        return 'notify'

    def get_extra_context( self, email_type : str ) -> Dict[ str, object ]:
        if email_type == 'notification':
            notification = NotifySyntheticData().create_random_notification()
            return {
                'notification': notification,
            }
        return dict()
