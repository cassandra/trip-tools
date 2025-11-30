"""
Icon template tags for consistent SVG icon rendering throughout the application.

This module provides template tags for rendering inline SVG icons with consistent
styling and accessibility features. All icons are self-contained (no external
dependencies) and integrate with the existing CSS variable system.

Usage:
    {% load icons %}
    {% icon "plus" size="md" color="primary" aria_label="Add item" %}
    {% icon "chevron-up" %}
"""

from django import template
from django.template.loader import get_template
from django.utils.safestring import mark_safe

register = template.Library()

# Define available icon names to prevent arbitrary file inclusion
AVAILABLE_ICONS = {
    'audio-disabled',
    'audio-enabled',
    'bold',
    'book',
    'book-open',
    'calendar',
    'camera',
    'x',
    'check-circle',
    'chevron-double-left',
    'chevron-double-right',
    'chevron-down',
    'chevron-left',
    'chevron-right',
    'chevron-up',
    'clock',
    'close',
    'cloud',
    'code',
    'document',
    'trash',
    'circle-slash',
    'download',
    'pencil',
    'exclamation-circle',
    'eye',
    'eye-off',
    'cloud-check',
    'globe',
    'heading',
    'clock-rotate',
    'house',
    'indent',
    'info-circle',
    'italic',
    'keyboard',
    'layers',
    'lightbulb',
    'link',
    'list-ol',
    'list-ul',
    'lock',
    'map-pin',
    'minus-circle',
    'move',
    'outdent',
    'plug',
    'star',
    'triangle-right',
    'plus',
    'question-circle',
    'rocket',
    'rotate',
    'check',
    'gear',
    'shield',
    'moon',
    'sync',
    'document-list',
    'times-circle',
    'unlock',
    'upload',
    'video',
    'grid',
    'exclamation-triangle',
    'magnifying-glass-plus',
}

# Define available sizes
ICON_SIZES = {'sm', 'md', 'lg', 'xl'}

# Define available semantic colors (matching CSS variables)
ICON_COLORS = {
    'primary',
    'secondary',
    'success',
    'warning',
    'error',
    'muted'
}

# Aliases map contextual names to canonical visual names
# Canonical names describe what the icon looks like (e.g., 'warning' is a triangle)
# Aliases describe contextual uses (e.g., 'alert-triangle' for warning scenarios)
ICON_ALIASES = {
    'alert-triangle': 'exclamation-triangle',
    'warning': 'exclamation-triangle',
    'file-text': 'book',
    'save': 'check',
    'delete': 'trash',
    'cancel': 'x',
    'settings': 'gear',
    'home': 'house',
    'edit': 'pencil',
    'disabled': 'circle-slash',
    'forecast': 'cloud-check',
    'sleep': 'moon',
    'history': 'clock-rotate',
    'zoom': 'magnifying-glass-plus',
    'view': 'grid',
    'tasks': 'document-list',
    'collection': 'document',
    'path': 'star',
    'play': 'triangle-right',
}


def resolve_icon_name(name: str) -> str:
    """
    Resolve an icon name, following aliases if present.

    Args:
        name: Icon name (may be an alias or canonical name)

    Returns:
        Canonical icon name
    """
    return ICON_ALIASES.get(name, name)


@register.simple_tag
def icon(name, size='md', color=None, aria_label=None, title=None, css_class=''):
    """
    Render an inline SVG icon with consistent styling and accessibility.

    Args:
        name (str): Icon name (canonical name or alias)
        size (str): Icon size ('sm', 'md', 'lg', 'xl'). Default: 'md'
        color (str): Semantic color ('primary', 'secondary', etc.). Default: None
        aria_label (str): Accessibility label. If provided, icon is meaningful.
                         If None, icon is decorative (aria-hidden="true")
        title (str): Tooltip text. Default: None
        css_class (str): Additional CSS classes. Default: ''

    Returns:
        SafeString: Rendered SVG icon HTML

    Raises:
        template.TemplateSyntaxError: If icon name is not available
    """

    # Resolve alias to canonical name
    canonical_name = resolve_icon_name(name)

    # Validate icon name
    if canonical_name not in AVAILABLE_ICONS:
        all_names = AVAILABLE_ICONS | set(ICON_ALIASES.keys())
        raise template.TemplateSyntaxError(
            f'Icon "{name}" is not available. '
            f'Available icons: {", ".join(sorted(all_names))}'
        )
    
    # Validate size
    if size not in ICON_SIZES:
        size = 'md'  # Default fallback
    
    # Validate color
    if color and color not in ICON_COLORS:
        color = None  # Invalid color, use default
    
    # Build CSS classes
    classes = ['tt-icon', f'tt-icon-{size}']
    
    if color:
        classes.append(f'tt-icon-{color}')
    
    if css_class:
        classes.append(css_class)
    
    class_attr = ' '.join(classes)
    
    # Build accessibility attributes
    accessibility_attrs = []
    
    if aria_label:
        # Meaningful icon - has semantic meaning
        accessibility_attrs.append(f'aria-label="{aria_label}"')
        accessibility_attrs.append('role="img"')
    else:
        # Decorative icon - no semantic meaning
        accessibility_attrs.append('aria-hidden="true"')
    
    if title:
        accessibility_attrs.append(f'title="{title}"')
    
    accessibility_str = ' '.join(accessibility_attrs)
    
    try:
        # Load the specific icon template (using canonical name)
        icon_template = get_template(f'icons/{canonical_name}.html')

        # Create context for the icon template
        icon_context = {
            'class_attr': class_attr,
            'accessibility_attrs': accessibility_str,
        }

        # Render the icon template
        rendered_icon = icon_template.render(icon_context)

        return mark_safe(rendered_icon)

    except template.TemplateDoesNotExist:
        # Fallback if icon template doesn't exist
        return mark_safe(
            f'<span class="{class_attr}" {accessibility_str}>[{canonical_name}]</span>'
        )


@register.simple_tag
def icon_list(include_aliases=False):
    """
    Return a sorted list of available icon names.
    Useful for documentation or debugging.

    Args:
        include_aliases: If True, include alias names in the list

    Returns:
        list: Sorted list of available icon names
    """
    icons = set(AVAILABLE_ICONS)
    if include_aliases:
        icons |= set(ICON_ALIASES.keys())
    return sorted(icons)


@register.filter
def has_icon(name):
    """
    Template filter to check if an icon is available.
    Checks both canonical names and aliases.

    Args:
        name (str): Icon name to check (canonical or alias)

    Returns:
        bool: True if icon is available, False otherwise
    """
    canonical_name = resolve_icon_name(name)
    return canonical_name in AVAILABLE_ICONS
