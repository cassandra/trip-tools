from django.shortcuts import render
from django.utils import timezone
from django.views.generic import View


class TestUiNotebookHomeView(View):

    def get(self, request, *args, **kwargs):
        context = {}
        return render(request, "notebook/tests/ui/home.html", context)


class TestUiConflictModalView(View):
    """Visual testing for notebook conflict modal."""

    def get(self, request, *args, **kwargs):
        # Create synthetic data for modal preview
        modified_by_name = 'Alice Smith'
        modified_at_datetime = timezone.now()

        # Generate sample diff HTML
        diff_html = (
            '<div class="unified-diff">'
            '<div class="diff-header">--- Server Version (Latest)</div>'
            '<div class="diff-header">+++ Your Changes</div>'
            '<div class="diff-hunk">@@ -1,5 +1,5 @@</div>'
            '<div class="diff-context"> Day 1 - Arrival in Portland</div>'
            '<div class="diff-context"> </div>'
            '<div class="diff-delete">-Checked into hotel downtown. '
            'Weather was rainy.</div>'
            '<div class="diff-add">+Checked into hotel downtown. '
            'Weather was sunny and beautiful!</div>'
            '<div class="diff-context"> Explored Powell\'s Books in the '
            'afternoon.</div>'
            '<div class="diff-context"> </div>'
            '</div>'
        )

        # Render the modal template directly
        context = {
            'modified_by_name': modified_by_name,
            'modified_at_datetime': modified_at_datetime,
            'diff_html': diff_html,
        }

        return render(request, 'notebook/modals/edit_conflict.html', context)


class TestUiConflictModalLongDiffView(View):
    """Visual testing for conflict modal with long diff."""

    def get(self, request, *args, **kwargs):
        # Create synthetic data with a longer diff
        modified_by_name = 'Bob Johnson'
        modified_at_datetime = timezone.now()

        # Generate longer diff with multiple sections
        diff_lines = []
        diff_lines.append('<div class="unified-diff">')
        diff_lines.append('<div class="diff-header">--- Server Version (Latest)</div>')
        diff_lines.append('<div class="diff-header">+++ Your Changes</div>')

        # Hunk 1
        diff_lines.append('<div class="diff-hunk">@@ -1,10 +1,12 @@</div>')
        diff_lines.append('<div class="diff-context"> Day 3 - Hiking in the Gorge</div>')
        diff_lines.append('<div class="diff-context"> </div>')
        diff_lines.append('<div class="diff-delete">-Started early at 7am.</div>')
        diff_lines.append(
            '<div class="diff-add">+Started early at 6:30am to beat '
            'the crowds.</div>'
        )
        diff_lines.append('<div class="diff-context"> Drove to Multnomah Falls.</div>')
        diff_lines.append('<div class="diff-delete">-Trail was crowded.</div>')
        diff_lines.append('<div class="diff-add">+Trail was moderately busy but manageable.</div>')
        diff_lines.append(
            '<div class="diff-add">+Met a friendly couple from Seattle '
            'who recommended other trails.</div>'
        )
        diff_lines.append('<div class="diff-context"> Took lots of photos at the bridge.</div>')
        diff_lines.append('<div class="diff-context"> </div>')

        # Hunk 2
        diff_lines.append('<div class="diff-hunk">@@ -15,8 +17,10 @@</div>')
        diff_lines.append('<div class="diff-context"> Afternoon at Vista House</div>')
        diff_lines.append('<div class="diff-context"> </div>')
        diff_lines.append('<div class="diff-delete">-Views were good.</div>')
        diff_lines.append(
            '<div class="diff-add">+Views were absolutely spectacular! '
            'Crystal clear day.</div>'
        )
        diff_lines.append('<div class="diff-add">+Spotted several eagles soaring over the gorge.</div>')
        diff_lines.append('<div class="diff-context"> Had lunch at a viewpoint.</div>')
        diff_lines.append('<div class="diff-delete">-Sandwiches from the car.</div>')
        diff_lines.append('<div class="diff-add">+Packed sandwiches tasted even better with that view!</div>')
        diff_lines.append('<div class="diff-context"> </div>')

        # Hunk 3
        diff_lines.append('<div class="diff-hunk">@@ -25,5 +29,7 @@</div>')
        diff_lines.append('<div class="diff-context"> Evening back in Portland</div>')
        diff_lines.append('<div class="diff-context"> </div>')
        diff_lines.append('<div class="diff-add">+Discovered an amazing food cart pod near the hotel.</div>')
        diff_lines.append('<div class="diff-add">+Thai food was incredible - definitely going back!</div>')
        diff_lines.append('<div class="diff-context"> Tired but happy after a great day.</div>')

        diff_lines.append('</div>')
        diff_html = ''.join(diff_lines)

        context = {
            'modified_by_name': modified_by_name,
            'modified_at_datetime': modified_at_datetime,
            'diff_html': diff_html,
        }

        return render(request, 'common/modals/edit_conflict.html', context)


class TestUiConflictModalEmptyDiffView(View):
    """Visual testing for conflict modal with no differences."""

    def get(self, request, *args, **kwargs):
        # Synthetic data with identical text (no diff)
        modified_by_name = 'Charlie Davis'
        modified_at_datetime = timezone.now()

        # No differences detected case
        diff_html = '<div class="diff-no-changes">No differences detected</div>'

        context = {
            'modified_by_name': modified_by_name,
            'modified_at_datetime': modified_at_datetime,
            'diff_html': diff_html,
        }

        return render(request, 'common/modals/edit_conflict.html', context)
