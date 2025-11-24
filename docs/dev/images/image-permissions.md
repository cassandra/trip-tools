# Image Permission System

## Overview

The image permission system enables collaborative journal editing by allowing trip members to access each other's images when editing journal entries. Images remain global entities (no trip FK), but permission is granted through trip membership context.

## Permission Model

### Core Rules

1. **Uploader always has access**: Users can always access their own images
2. **Trip context grants access**: Current trip members can access each other's images
3. **Query-time permission**: No caching, checks current membership at query time
4. **Former members lose access**: Removing a user from trip immediately revokes browse access
5. **MEDIA_ROOT URLs persist**: Existing journal image URLs remain accessible via MEDIA_ROOT (security by obscurity with UUID)

### Access Modes

The system supports two access modes:

1. **With trip context**: Trip members can access all member images
2. **Without trip context**: Only uploader has access (private mode)

## API Reference

### Model Methods

#### `TripImage.user_can_access(user, trip=None)`

Check if user has permission to access an image.

**Parameters:**
- `user` (User): User to check permission for
- `trip` (Trip, optional): Trip context for permission check

**Returns:**
- `bool`: True if user can access this image

**Examples:**
```python
# Check uploader access (no trip context)
if image.user_can_access(request.user):
    # User is the uploader
    pass

# Check trip member access (with trip context)
if image.user_can_access(request.user, trip=journal.trip):
    # User is current trip member
    pass
```

### Manager Methods

#### `TripImageManager.accessible_to_user_in_trip(user, trip)`

Get all images accessible to user in a trip context.

Returns images from all current trip members.

**Parameters:**
- `user` (User): User requesting access
- `trip` (Trip): Trip context for permission check

**Returns:**
- `QuerySet`: TripImage instances accessible to user in this trip

**Example:**
```python
# Get all images accessible to user in this trip
images = TripImage.objects.accessible_to_user_in_trip(
    user=request.user,
    trip=trip
)
```

#### `TripImageManager.accessible_to_user_in_trip_for_date_range(user, trip, start_datetime, end_datetime)`

Get images accessible to user in trip, filtered by date range.

**Primary method for journal entry editing** - shows images from all current trip members within the entry's day boundaries.

**Parameters:**
- `user` (User): User requesting access
- `trip` (Trip): Trip context for permission check
- `start_datetime` (datetime): Start of date range (timezone-aware)
- `end_datetime` (datetime): End of date range (timezone-aware)

**Returns:**
- `QuerySet`: TripImage instances within date range

**Note**: Images with null `datetime_utc` are excluded from results.

**Example:**
```python
from datetime import datetime
import pytz

# Get images for specific date range
start = datetime(2025, 1, 15, 0, 0, tzinfo=pytz.UTC)
end = datetime(2025, 1, 16, 0, 0, tzinfo=pytz.UTC)

images = TripImage.objects.accessible_to_user_in_trip_for_date_range(
    user=request.user,
    trip=trip,
    start_datetime=start,
    end_datetime=end
)
```

#### `TripImageManager.for_trip(trip)`

Get all images from trip members (follows codebase `.for_trip()` pattern).

**Note**: This doesn't check permissions, just returns images from trip members. For permission-aware queries, use `accessible_to_user_in_trip()`.

**Parameters:**
- `trip` (Trip): Trip instance

**Returns:**
- `QuerySet`: TripImage instances from trip members

**Example:**
```python
# Get all images from trip members (no permission check)
images = TripImage.objects.for_trip(trip)
```

### Validators

#### `ImagePermissionValidator(trip=None)`

Validator for image access permissions with optional trip context support.

**Parameters:**
- `trip` (Trip, optional): Trip instance for trip-context permission check

**Raises:**
- `ValidationError`: If user does not have permission

**Example:**
```python
from tt.apps.images.validators import ImagePermissionValidator

# Create validator with trip context
validator = ImagePermissionValidator(trip=journal.trip)

# Validate access
try:
    validator(trip_image, request.user)
except ValidationError:
    # User does not have permission
    pass
```

### Utility Functions

#### `journal.utils.get_entry_date_boundaries(entry_date, timezone_str)`

Calculate timezone-aware datetime boundaries for a journal entry's day.

**Parameters:**
- `entry_date` (date): Date object for the journal entry
- `timezone_str` (str): Pytz timezone string (e.g., 'America/New_York')

**Returns:**
- `tuple`: (start_datetime, end_datetime) as timezone-aware datetimes

**Example:**
```python
from datetime import date
from tt.apps.journal.utils import get_entry_date_boundaries

entry_date = date(2025, 1, 15)
timezone = 'America/New_York'

start_dt, end_dt = get_entry_date_boundaries(entry_date, timezone)
# start_dt = 2025-01-15 00:00:00-05:00
# end_dt = 2025-01-16 00:00:00-05:00
```

## Integration Guide for Journal Entry Editor

### Step 1: Calculate Date Boundaries

Use the entry's date and timezone to calculate day boundaries in UTC:

```python
from tt.apps.journal.utils import get_entry_date_boundaries

# Get timezone-aware boundaries for the entry's day
start_dt, end_dt = get_entry_date_boundaries(
    entry.date,
    entry.timezone
)
```

### Step 2: Fetch Accessible Images

Query images from trip members within the date range:

```python
from tt.apps.images.models import TripImage

# Get images accessible to user for this date range
accessible_images = TripImage.objects.accessible_to_user_in_trip_for_date_range(
    user=request.user,
    trip=entry.journal.trip,
    start_datetime=start_dt,
    end_datetime=end_dt
)
```

### Step 3: Pass to Template

Include images and trip context in template context:

```python
context = {
    'entry': entry,
    'accessible_images': accessible_images,
    'trip': entry.journal.trip,
    # ... other context
}
```

### Step 4: Generate Inspect URLs

When rendering image preview/inspect modals, include trip_id:

```html
<!-- Image inspect URL with trip context -->
<a href="/trip-image/{{ image.uuid }}/inspect/?trip_id={{ trip.id }}">
    <img src="{{ image.thumbnail_image.url }}" alt="{{ image.caption }}">
</a>
```

### Step 5: Handle Metadata Editing

The `TripImageInspectView` returns `can_edit_metadata` in context:

```html
{% if can_edit_metadata %}
    <!-- Show edit metadata button -->
    <button>Edit Metadata</button>
{% else %}
    <!-- View-only mode -->
    <p>Uploaded by {{ image.uploaded_by.get_full_name }}</p>
{% endif %}
```

## Complete Journal Entry Editor Example

```python
from django.views.generic import View
from tt.apps.images.models import TripImage
from tt.apps.journal.models import JournalEntry
from tt.apps.journal.utils import get_entry_date_boundaries

class JournalEntryEditView(LoginRequiredMixin, TripViewMixin, View):
    def get(self, request, trip_id, entry_id):
        # Get trip member (validates membership)
        request_member = self.get_trip_member(request, trip_id=trip_id)
        self.assert_is_editor(request_member)

        # Get journal entry
        entry = get_object_or_404(
            JournalEntry,
            pk=entry_id,
            journal__trip=request_member.trip
        )

        # Calculate date boundaries for entry
        start_dt, end_dt = get_entry_date_boundaries(
            entry.date,
            entry.timezone
        )

        # Get accessible images for this date
        accessible_images = TripImage.objects.accessible_to_user_in_trip_for_date_range(
            user=request.user,
            trip=request_member.trip,
            start_datetime=start_dt,
            end_datetime=end_dt
        )

        context = {
            'entry': entry,
            'trip': request_member.trip,
            'accessible_images': accessible_images,
            'can_edit_entry': request_member.can_edit_trip,
        }

        return render(request, 'journal/pages/entry_edit.html', context)
```

## View Integration: TripImageInspectView

The inspect view supports both trip and non-trip contexts:

### With Trip Context

```python
# URL: /trip-image/{uuid}/inspect/?trip_id=123
# Permission: Checks if user is current trip member
# Context: includes can_edit_metadata and trip
```

### Without Trip Context

```python
# URL: /trip-image/{uuid}/inspect/
# Permission: Only uploader has access
# Context: includes can_edit_metadata (always True for uploader)
```

## Permission Scenarios

### Scenario 1: Collaborative Editing

**Setup:**
- Alice and Bob are members of "Europe Trip"
- Alice uploads photo on Jan 15
- Bob is editing journal entry for Jan 15

**Result:**
- Bob can browse Alice's Jan 15 photos
- Bob can view full-size image with ?trip_id=X
- Bob cannot edit Alice's image metadata
- Alice's photo appears in Bob's date-filtered image picker

### Scenario 2: Former Member

**Setup:**
- Alice and Bob are members of "Europe Trip"
- Alice uploads photo on Jan 15
- Bob is removed from trip
- Alice's photo is already in a journal entry

**Result:**
- Bob can no longer browse Alice's photos in image picker
- Bob cannot open inspect modal with trip context
- Existing journal entry image URLs still work (MEDIA_ROOT)
- Journal display is unaffected

### Scenario 3: Non-Trip Context

**Setup:**
- Alice uploads photo
- Bob tries to access via direct URL (no trip_id)

**Result:**
- Only Alice can access (uploader-only mode)
- Bob receives 403 Permission Denied
- No trip membership check performed

## Performance Considerations

### Optimizations

1. **Query efficiency**: Uses `values_list('user_id', flat=True)` for membership IDs
2. **N+1 prevention**: Includes `select_related('uploaded_by')` in date range queries
3. **Index usage**: Leverages existing `datetime_utc` index for date filtering
4. **Query-time checks**: No caching overhead, fresh permission checks

### Typical Query Performance

- **Membership check**: Single EXISTS query with indexed FK
- **Image listing**: Single query with IN clause on indexed field
- **Date range filter**: Uses indexed datetime field

For trips with 5 members and 100 images, expect:
- Membership check: < 1ms
- Image list query: < 10ms
- Date range filter: < 5ms

## Security Model

### Image URL Security

- **Strategy**: Security by obscurity with UUID-based filenames
- **Serving**: Direct MEDIA_ROOT serving (nginx/CDN, not Django)
- **Persistence**: URLs remain accessible even after permission revocation
- **Trade-off**: Performance over strict access control

### Permission Layer

- **Application-level**: Django views check permissions before rendering
- **Browse control**: Image picker only shows permitted images
- **Inspect control**: Modal requires permission check
- **No file-level control**: MEDIA_ROOT URLs accessible if known

### Acceptable Risk

From Issue #28:
> "Acceptable: Users with historical access retain image URLs"

This is a deliberate design choice prioritizing:
- Performance (no Django serving overhead)
- Simplicity (standard MEDIA_ROOT pattern)
- Practicality (revoked users unlikely to retain/share URLs)

## Testing

The image permission system has comprehensive test coverage:

- **Model permission tests**: Uploader, member, non-member, former member access
- **Manager tests**: Trip filtering, date range filtering, for_trip() pattern
- **View tests**: Trip context, can_edit_metadata flag
- **Integration tests**: Full journal entry workflow with timezone boundaries

**Test suite**: `tt/apps/images/tests/test_models.py` (96 tests total, 9 new trip-context tests)

## Related Issues

- **Issue #32**: Image Permission System (this implementation)
- **Issue #28**: Trip Journal Requirements (depends on image permissions)
- **Issue #29**: Trip Journal UX Design (uses image permission API)

## Migration Notes

**No database schema changes required.**

All necessary fields already exist:
- `TripImage.uploaded_by` (FK to User)
- `TripImage.datetime_utc` (indexed DateTimeField)
- `TripMember.trip` and `TripMember.user` (for membership queries)
- `JournalEntry.date` and `JournalEntry.timezone` (for date boundaries)

This is purely a permission/access control enhancement with no data migration needed.
