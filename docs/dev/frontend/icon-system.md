# Icon System

## Icon System Overview

Use the standardized `{% icon %}` template tag for consistent icon rendering. See `tt/apps/common/templatetags/icons.py` for available icons and parameters.

## Icon Naming Guidelines

- **Canonical names** should describe the visual appearance of the SVG (e.g., `triangle`, `check`, `check-circle`)
- **Aliases** provide contextual names for different uses (e.g., `warning` → `triangle`, `save` → `check`)
- When creating new icons, name them for what they look like, then add aliases for how they're used

## UX Principles for Icon Usage

### Primary Value
Icons provide faster recognition, universal language, space efficiency, and visual hierarchy.

### ALWAYS Add Icons When
- **Universal Actions**: Add (+), Delete (trash), Edit (pencil), Save (checkmark), Cancel (×)
- **Navigation**: Back/Forward arrows, Up/Down, Expand/Collapse
- **Media Controls**: Play, Pause, Video, Camera
- **Status/Feedback**: Success, Warning, Error, Info

### Key Design Principle
Focus on **ACTION TYPE** (add, delete, edit), not object specificity. "Add Item" and "Add Rule" both get the same + icon because they're both "add" actions.

## Implementation Requirements

- Always include `{% load icons %}` at top of templates
- Icons should supplement text, not replace it for important actions
- Use semantic size and color parameters when available
- Include appropriate ARIA labels for accessibility
- Maintain consistency: same action = same icon across the application

## Icon Parameters

### Size Options
- `xs` - Extra small (12px)
- `sm` - Small (16px) - **Most common**
- `md` - Medium (20px) - Default
- `lg` - Large (24px)
- `xl` - Extra large (32px)

### CSS Classes
- `tt-icon-left` - Icon positioned to the left of text
- `tt-icon-right` - Icon positioned to the right of text
- `tt-icon-only` - Icon without accompanying text
- `tt-icon-spin` - Spinning animation for loading states

### Color Options
When available through the icon system:
- `text-primary` - Primary theme color
- `text-success` - Success/positive actions
- `text-warning` - Warning/caution
- `text-danger` - Danger/destructive actions
- `text-muted` - Subtle/disabled state

## Template Usage Examples

### Basic Icon Usage

```django
{% load icons %}

<!-- Primary action with icon -->
<button class="btn btn-primary">
  {% icon "plus" size="sm" css_class="tt-icon-left" %}
  Add New Rule
</button>

<!-- Edit action -->
<a class="btn btn-secondary" href="/edit/">
  {% icon "edit" size="sm" css_class="tt-icon-left" %}
  Edit
</a>

<!-- Save/Submit action -->
<button class="btn btn-success" type="submit">
  {% icon "save" size="sm" css_class="tt-icon-left" %}
  Save Changes
</button>
```

### Icon-Only Actions

Use for space-constrained areas with proper accessibility:

```django
<!-- Delete action - icon-only for space constraints -->
<button class="btn btn-danger btn-sm" aria-label="Delete item">
  {% icon "delete" size="sm" %}
</button>

<!-- Modal close - icon-only (universal convention) -->
<button type="button" class="close" data-dismiss="modal" aria-label="Close">
  {% icon "close" size="sm" %}
</button>
```

### Status and Feedback Icons

```django
<!-- Success message -->
<div class="alert alert-success">
  {% icon "check-circle" size="sm" css_class="tt-icon-left" %}
  Operation completed successfully!
</div>

<!-- Warning message -->
<div class="alert alert-warning">
  {% icon "exclamation-triangle" size="sm" css_class="tt-icon-left" %}
  Please review your settings before continuing.
</div>
```

## Accessibility Considerations

### ARIA Labels

Always provide ARIA labels for icon-only buttons:

```django
<button class="btn btn-primary" aria-label="Edit entity settings">
  {% icon "edit" size="sm" %}
</button>
```

### Screen Reader Support

For decorative icons, use `aria-hidden="true"`:

```django
<h2>
  {% icon "user" size="sm" aria_hidden="true" %}
  User Profile
</h2>
```

### Focus Indicators

Ensure icon buttons have visible focus indicators:

```css
.btn:focus {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
```

## Icon Aliases

Icons can be referenced by alternative names using aliases. See `ICON_ALIASES` in `icons.py` for current mappings.

Both canonical names and aliases work with `{% icon %}`, `has_icon`, and `icon_list`:

```django
{% icon "save" %}                               {# Canonical name #}
{% icon "confirm" %}                            {# Alias (if defined) #}
{% icon_list include_aliases=True as icons %}   {# Include aliases in list #}
```

## Icon Discovery and Creation

For finding appropriate icons or creating new ones, use the `/icon` command which will:
- Search existing icons for semantic matches
- Recommend existing icons when appropriate
- Guide creation of new icons when needed
- Maintain consistency with the icon system

## Related Documentation
- Frontend guidelines: [Frontend Guidelines](frontend-guidelines.md)
- Style guidelines: [Style Guidelines](style-guidelines.md)
- Template conventions: [Template Conventions](template-conventions.md)
