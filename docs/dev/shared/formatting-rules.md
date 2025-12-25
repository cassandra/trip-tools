# Formatting Rules for Code Conformance

This document defines the formatting conventions for this project. It is designed
for AI agents to reference when checking or fixing code formatting.

**Purpose**: Apply these rules exactly as shown. Focus only on formatting, not logic.

---

## Rule 1: Parentheses Spacing

Add spaces inside parentheses for function calls, conditionals, and expressions.

### Good
```python
result = calculate( x, y )
if ( condition ):
    process( data )
items = list( generator )
value = func( arg1, arg2 )
```

### Bad
```python
result = calculate(x, y)
if (condition):
    process(data)
items = list(generator)
value = func(arg1, arg2)
```

### Exceptions - Do NOT add spaces for:

1. **Empty parentheses**:
```python
# Good - no spaces
def foo():
    return bar()
```

2. **Single self/cls in method definitions**:
```python
# Good - no spaces
def get_name(self):
    return self.name

@classmethod
def create(cls):
    return cls()
```

3. **Single string argument (including f-strings)**:
```python
# Good - no spaces when ONLY argument is a string
name = request.GET.get('name')
logger.info('Starting process')
logger.info(f'Processing {item}')
raise ValueError('Invalid input')
entry.date.strftime('%Y-%m-%d')
queryset.order_by('date')

# Bad - needs spaces when string + other arguments
cache.get('key', default)      # Bad
cache.get( 'key', default )    # Good
```

4. **Class inheritance**:
```python
# Good - no spaces
class MyError(Exception):
    pass

class UserService(BaseService):
    pass
```

5. **Decorators**:
```python
# Good - no spaces
@property
@lru_cache(maxsize=100)
@transaction.atomic
def process(self):
    pass
```

6. **Indexing and simple type parameters (brackets)**:
```python
# Good - no spaces for indexing
items[0]
data['key']
matrix[i][j]

# Good - no spaces for simple type parameters
journal : List[str]
user    : Optional[User]
config  : Dict[str, int]

# Acceptable - spaces for complex/nested types (readability)
handlers : Dict[ str, Callable[ [Request], Response ] ]
nested   : List[ Tuple[ int, Dict[ str, Any ] ] ]

# Bad
items[ 0 ]
data[ 'key' ]
```

### Method Chaining

Each call site is evaluated independently. Chaining does not affect spacing rules:

```python
# Good - each call follows its own rules
queryset.filter( status = 'active' ).order_by('date').distinct()
#        ^^^ needs spaces           ^^^ single string   ^^^ empty
```

### Adjacent Closing Symbols

The spacing rule aims to separate readable text from symbols. Adjacent closing
symbols (like `})` or `))`) do NOT need spaces between them:

```python
# Good - no space between adjacent closing symbols
reverse( 'journal_home', kwargs = { 'journal_uuid': journal.uuid })
visibility_form.add_error( None, str( e ))
cache.set( key, { 'data': value })

# Bad - unnecessary space between closing symbols
reverse( 'journal_home', kwargs = { 'journal_uuid': journal.uuid } )
visibility_form.add_error( None, str( e ) )
```

### Dict Literals

Dict literals follow similar rules to function calls:
- Spaces after `{` and before `}`
- Exception: singleton string key/value follows single-string exception

```python
# Good - spaces inside dict braces
config = { 'name': 'value', 'count': 42 }
reverse( 'url', kwargs = { 'uuid': obj.uuid })

# Good - singleton string exception (quotes provide separation)
data = {'key'}
simple = {'only_key': 'only_value'}

# Bad - missing spaces
config = {'name': 'value', 'count': 42}
```

---

## Rule 2: Keyword Argument Spacing

Use spaces around `=` in function calls with keyword arguments.

### Good
```python
result = fetch_data( user_id = 123, include_deleted = False )
entry.save( update_fields = ['title', 'content'] )
cache.set( key = cache_key, value = data, timeout = 3600 )
```

### Bad
```python
result = fetch_data(user_id=123, include_deleted=False)
entry.save(update_fields=['title', 'content'])
cache.set(key=cache_key, value=data, timeout=3600)
```

### Exception - Function definitions use NO spaces:
```python
# Good - no spaces in defaults
def process( self,
             user_id    : int,
             max_items  : int  = 100,
             active     : bool = True ) -> List[Item]:
```

---

## Rule 3: Multi-line Method Signatures with Column Alignment

When a method has 3+ parameters, use one line per parameter with aligned columns.

### Good
```python
def publish_journal( self,
                     journal              : Journal,
                     selected_entry_uuids : List[str],
                     visibility_form      : JournalVisibilityForm,
                     user                 : User                   ) -> Travelog:

def set_entity_path( self,
                     entity_id    : int,
                     location     : Location,
                     svg_path_str : str       ) -> EntityPath:
```

### Bad
```python
# Not aligned
def publish_journal( self,
                     journal : Journal,
                     selected_entry_uuids : List[str],
                     visibility_form : JournalVisibilityForm,
                     user : User ) -> Travelog:

# All on one line (too many params)
def set_entity_path( self, entity_id : int, location : Location, svg_path_str : str ) -> EntityPath:

# Mixed lines
def set_entity_path( self, entity_id : int,
                     location : Location, svg_path_str : str ) -> EntityPath:
```

### Alignment Details
- Parameter names: right-pad to align the colons
- Type annotations: right-pad to align closing paren or default values
- The `:` should form a vertical column
- Default `=` signs should align when present

---

## Rule 4: Multi-line Method Calls

When a method call has 3+ arguments, use one line per argument.

### Good
```python
cls._update_entry_selections(
    journal = journal,
    selected_entry_uuids = selected_entry_uuids,
)

travelog = PublishingService.publish_journal(
    journal = journal,
    user = user,
)

result = complex_function(
    first_arg = value1,
    second_arg = value2,
    third_arg = value3,
)
```

### Bad
```python
# All on one line (too many args)
cls._update_entry_selections( journal = journal, selected_entry_uuids = selected_entry_uuids )

# Missing trailing comma
result = complex_function(
    first_arg = value1,
    second_arg = value2,
    third_arg = value3
)
```

---

## Rule 5: Dataclass and Enum Alignment

Align field names, types, and default values in columns.

### Good
```python
@dataclass
class JournalEntry:
    journal    : Journal
    date       : date
    title      : str
    text       : str            = ''
    timezone   : str            = 'UTC'
    published  : bool           = False


class EntryStatus( LabeledEnum ):
    DRAFT     = 'draft',     'Draft'
    PUBLISHED = 'published', 'Published'
    ARCHIVED  = 'archived',  'Archived'
```

### Bad
```python
@dataclass
class JournalEntry:
    journal : Journal
    date : date
    title : str
    text : str = ''
    timezone : str = 'UTC'
    published : bool = False


class EntryStatus( LabeledEnum ):
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'
    ARCHIVED = 'archived', 'Archived'
```

---

## Rule 6: List/Dict Comprehensions

Spacing rules apply inside comprehension brackets:

### Good
```python
items = [ x for x in data ]
result = [ item.name for item in items if item.active ]
mapping = { k: v for k, v in pairs }
unique = { item.id for item in items }
```

### Bad
```python
items = [x for x in data]
result = [item.name for item in items if item.active]
mapping = {k: v for k, v in pairs}
```

---

## Rule 7: Trailing Commas

Include trailing commas in multi-line structures **when the closing delimiter is on its own line**.

### Good
```python
# Closing delimiter on own line - trailing comma required
items = [
    'first',
    'second',
    'third',
]

config = {
    'name': 'value',
    'other': 'data',
}

result = function(
    arg1 = value1,
    arg2 = value2,
)

# Closing delimiter on same line as last element - no trailing comma
update_fields = [ 'modified_by',
                  'modified_datetime',
                  'title',
                  'description',
                  'reference_image' ]
```

### Bad
```python
# Missing trailing comma when closing delimiter is on own line
items = [
    'first',
    'second',
    'third'
]

config = {
    'name': 'value',
    'other': 'data'
}
```

---

## Rule 8: Explicit Control Flow

End all loops with explicit `continue`. End all functions with explicit `return`.

### Good
```python
def process_items( self, items: List[Item] ) -> List[Result]:
    results = []
    for item in items:
        if not item.valid:
            continue

        result = self.transform( item )
        results.append( result )
        continue

    return results


def get_count( self ) -> int:
    return len( self.items )
```

### Bad
```python
def process_items( self, items: List[Item] ) -> List[Result]:
    results = []
    for item in items:
        if not item.valid:
            continue  # OK here

        result = self.transform( item )
        results.append( result )
        # Missing continue at end of loop

    return results  # OK - has return


def get_count( self ) -> int:
    return len( self.items )
    # This is fine - has return
```

---

## Rule 9: Explicit Boolean Wrapping

Use `bool()` when assigning non-boolean expressions or compound boolean expressions to a variable.

### When bool() IS needed:
- Non-boolean expressions: `len(items)`, `user.last_login`, `request.GET.get('x')`
- Compound boolean operators: `a and b`, `x or y`
- Comparisons being assigned: `count > 0`

### When bool() is NOT needed:
- Boolean literals: `True`, `False`
- Variables already typed as bool
- Boolean method returns: `.exists()`, `.is_valid()`

### Good
```python
# Non-boolean needs bool()
is_active = bool( user.last_login )
has_items = bool( len( items ) )

# Compound expressions need bool()
is_valid = bool( has_permission and is_active )
can_edit = bool( is_owner or is_admin )

# Comparisons need bool()
is_over_limit = bool( count > 100 )

# Already boolean - no bool() needed
is_published = entry.is_published
has_entries = queryset.exists()
form_valid = form.is_valid()
is_enabled = True
```

### Bad
```python
is_active = user.last_login              # Non-bool assigned without bool()
is_valid = has_permission and is_active  # Compound without bool()
is_over_limit = count > 100              # Comparison without bool()
```

---

## Rule 10: Complex Boolean Expressions

Use parentheses around each clause in compound boolean expressions.
Use one line per clause for complex conditions.

### Good
```python
if is_editing and location_view:
    pass

if (( state.domain == API.SWITCH_DOMAIN )
      and ( API.LIGHT_DOMAIN in prefixes_seen )):
    pass

if ( condition_one
     and condition_two
     and condition_three ):
    pass
```

### Bad
```python
if state.domain == API.SWITCH_DOMAIN and API.LIGHT_DOMAIN in prefixes_seen:
    pass
```

---

## Rule 11: Single Quotes for Strings

Use single quotes for all Python strings.

### Good
```python
name = 'John'
message = 'Hello, world'
query = 'SELECT * FROM users'
```

### Bad
```python
name = "John"
message = "Hello, world"
query = "SELECT * FROM users"
```

### Exception - Use double quotes when:
- String contains single quotes: `"It's working"`
- Docstrings (always triple double quotes): `"""Docstring here."""`

---

## Rule 12: Import Organization

Group and order imports as follows, with one blank line between groups:

1. Standard library imports
2. Third-party/pip imports
3. Django imports
4. Project imports (tt.*)
5. App-relative imports (from . import)

### Good
```python
import json
from datetime import datetime
from typing import List, Optional

from django.contrib.auth import get_user_model
from django.db import transaction

from tt.core.utils import format_date
from tt.apps.common.models import BaseModel

from .enums import JournalVisibility
from .models import Journal, JournalEntry
```

### Bad
```python
from .models import Journal
from django.db import transaction
import json
from tt.core.utils import format_date
from datetime import datetime
from django.contrib.auth import get_user_model
```

---

## Formatting Checklist

When reviewing code, check each rule:

- [ ] Parentheses have internal spaces (except: empty, self/cls, single-string, inheritance, decorators)
- [ ] Keyword arguments have spaces around `=` (in calls, not definitions)
- [ ] Multi-line signatures have aligned columns
- [ ] Multi-line calls use one arg per line with trailing comma
- [ ] Dataclass/enum fields are aligned
- [ ] Comprehensions have internal spaces `[ x for x in items ]`
- [ ] Multi-line structures have trailing commas
- [ ] Loops end with `continue`
- [ ] Functions end with `return`
- [ ] Non-boolean and compound expressions use `bool()` when assigned
- [ ] Complex conditions use parentheses per clause
- [ ] Strings use single quotes
- [ ] Imports are properly grouped and ordered
- [ ] Indexing and simple type params have NO spaces `items[0]`, `List[str]`
- [ ] Complex nested types MAY use spaces for readability
- [ ] Adjacent closing symbols have NO space between them `})`, `))`
- [ ] Dict literals have spaces except singleton strings `{ 'a': 1 }` but `{'key'}`

---

## Related Documentation

- Coding standards and guidelines: [Coding Standards](coding-standards.md)
- Linting configuration rationale: See "Flake8 Configurations" in [Coding Standards](coding-standards.md)
