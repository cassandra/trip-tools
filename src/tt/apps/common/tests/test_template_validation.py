"""
Tests for Django template validation.

This module validates that all Django templates in the project can be loaded
and parsed without errors. It catches common issues like:
- Template syntax errors (unclosed tags, invalid syntax)
- Missing {% load %} tags for template tags being used
- Non-existent template names in {% include %} statements
- Malformed template inheritance

These tests do NOT validate:
- Missing context variables (requires rendering)
- Template logic correctness
- Runtime errors in custom template tags
"""
import logging
import re
from pathlib import Path

from django.template import TemplateSyntaxError, TemplateDoesNotExist
from django.template.loader import get_template
from django.test import TestCase

logging.disable(logging.CRITICAL)


class TemplateDiscoveryTestCase(TestCase):
    """
    Validates all Django templates can be loaded and parsed without errors.

    This test auto-discovers templates and validates them without requiring
    manual maintenance when templates are added or removed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.all_templates = cls._discover_all_templates()

    @classmethod
    def _discover_all_templates(cls):
        """
        Auto-discover all .html files in template directories.

        Returns list of Django template paths (e.g., 'journal/pages/entry.html')
        """
        templates = []

        # Get the tt/apps directory
        test_file_path = Path(__file__)
        apps_path = test_file_path.parent.parent.parent

        # Find all template directories within apps
        for app_dir in apps_path.iterdir():
            if not app_dir.is_dir():
                continue

            templates_dir = app_dir / 'templates'
            if not templates_dir.exists():
                continue

            # Find all .html files and convert to Django template paths
            for template_file in templates_dir.rglob('*.html'):
                # Convert filesystem path to Django template path
                # e.g., /path/to/tt/apps/journal/templates/journal/pages/entry.html
                # becomes: journal/pages/entry.html
                rel_path = template_file.relative_to(templates_dir)
                templates.append(str(rel_path))

        # Also check project-level templates directory if it exists
        project_templates = apps_path.parent / 'templates'
        if project_templates.exists():
            for template_file in project_templates.rglob('*.html'):
                rel_path = template_file.relative_to(project_templates)
                templates.append(str(rel_path))

        return sorted(set(templates))  # Remove duplicates and sort

    def test_templates_discovered(self):
        """Verify template auto-discovery is working."""
        self.assertGreater(
            len(self.all_templates),
            50,
            "Expected to find at least 50 templates in the project"
        )

        # Verify we found templates from multiple apps
        apps_with_templates = set()
        for template_path in self.all_templates:
            app_name = template_path.split('/')[0]
            apps_with_templates.add(app_name)

        self.assertGreater(
            len(apps_with_templates),
            5,
            "Expected to find templates from at least 5 different apps"
        )

    def test_all_templates_can_be_loaded(self):
        """
        Each template should load without TemplateSyntaxError or TemplateDoesNotExist.

        This catches:
        - Syntax errors (unclosed tags, invalid syntax)
        - Missing {% load %} tags when tags are actually used
        - Template inheritance errors
        """
        failures = []

        for template_name in self.all_templates:
            with self.subTest(template=template_name):
                try:
                    template = get_template(template_name)
                    # Just loading it is enough - Django parses on load
                    self.assertIsNotNone(template)

                except TemplateSyntaxError as e:
                    error_msg = f"{template_name}: SYNTAX ERROR - {e}"
                    failures.append(error_msg)

                except TemplateDoesNotExist as e:
                    error_msg = f"{template_name}: NOT FOUND - {e}"
                    failures.append(error_msg)

                except Exception as e:
                    error_msg = f"{template_name}: UNEXPECTED ERROR - {type(e).__name__}: {e}"
                    failures.append(error_msg)

        if failures:
            failure_summary = "\n  ".join(failures)
            self.fail(
                f"\n\nTemplate validation failures ({len(failures)} total):\n  {failure_summary}"
            )

    def test_template_include_targets_exist(self):
        """
        Validate that all {% include %} targets point to existing templates.

        This catches broken includes that would cause runtime errors.
        """
        # Regex to find {% include "path/to/template.html" %}
        include_pattern = re.compile(r'{%\s*include\s+["\']([^"\']+)["\']')

        failures = []

        for template_name in self.all_templates:
            try:
                template = get_template(template_name)

                # Get the raw template source
                source = template.template.source

                # Find all include statements
                includes = include_pattern.findall(source)

                for include_path in includes:
                    # Check if the included template exists
                    try:
                        get_template(include_path)
                    except TemplateDoesNotExist:
                        error_msg = (
                            f"{template_name} includes non-existent template: "
                            f"{include_path}"
                        )
                        failures.append(error_msg)

            except (TemplateSyntaxError, TemplateDoesNotExist):
                # Already caught in previous test, skip
                pass
            except Exception:
                # Unexpected error, skip (not testing this here)
                pass

        if failures:
            failure_summary = "\n  ".join(failures)
            self.fail(
                f"\n\nInclude validation failures ({len(failures)} total):\n  {failure_summary}"
            )
