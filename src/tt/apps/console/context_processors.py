from tt.apps.console.console_helper import ConsoleSettingsHelper


def settings_context(request):
    console_helper = ConsoleSettingsHelper()
    return {
        'USER_TIMEZONE': console_helper.get_tz_name( user = request.user ),
    }
