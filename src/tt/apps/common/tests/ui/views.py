from django.shortcuts import render
from django.views.generic import View

from tt.apps.common.templatetags.icons import AVAILABLE_ICONS, ICON_SIZES, ICON_COLORS, ICON_ALIASES


class TestUiCommonHomeView(View):
    """Home view for common app UI testing."""

    def get(self, request, *args, **kwargs):
        context = {}
        return render(request, "common/tests/ui/home.html", context)


class TestUiIconBrowserView(View):
    """
    Auto-discovery view for browsing all available icons.
    Automatically displays any new icons added to the system without manual updates.
    """

    def get(self, request, *args, **kwargs):
        # Build unified list of all icon names (canonical + aliases)
        all_icons = []
        for name in AVAILABLE_ICONS:
            all_icons.append({'name': name, 'is_alias': False})
        for alias, canonical in ICON_ALIASES.items():
            all_icons.append({'name': alias, 'is_alias': True, 'canonical': canonical})
        all_icons.sort(key=lambda x: x['name'])

        available_sizes = sorted(ICON_SIZES)
        available_colors = sorted(ICON_COLORS)

        context = {
            'all_icons': all_icons,
            'available_sizes': available_sizes,
            'available_colors': available_colors,
            'total_canonical': len(AVAILABLE_ICONS),
            'total_aliases': len(ICON_ALIASES),
        }
        return render(request, "common/tests/ui/icon_browser.html", context)
    
