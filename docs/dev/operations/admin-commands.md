# Executing Django Admin Commands

Example for journal entry content migrations.

```
ssh root@triptools.net
docker exec -it tt /bin/bash

# Dry run
./manage.py migrate_entry_content

# Execute
./manage.py migrate_entry_content --execute

# Then verify content unchanged.
```
