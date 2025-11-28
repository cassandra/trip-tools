# Project Structure

## Directory Structure

### Top-level Directory
- `src`: application source code
- `deploy`: helper scripts and files for deploying and setting up the application
- `package`: extra items that need to be packaged up to support running the application in Docker
- `Makefile`: provides convenience wrappers around commands for building, packaging and running
- `docs`: all documentation suitable to be in markdown files and part of repository
- `venv`: The Python virtual environment (not checked into repository!)
- `data` - For local data to be ignored by git, docker, etc

### The `src` Directory
- `tt`: entry point urls/views and some app-wide helper classes
- `tt/apps/${APPNAME}`: For normal application modules
- `tt/environment`: Environment definitions for client (Javascript) and server (Python)
- `tt/settings`: Django settings, including runtime population from environment variables
- `tt/static`: Static files for Javascript, CSS, IMG, etc.
- `tt/templates`: For top-level views and app-wide common base templates
- `tt/testing`: Test-specific code not used in production
- `tt/requirements`: Python package dependencies
- `custom`: Custom user model and other general customizations
- `bin`: Helper scripts needed with the code to run inside a Docker container

## Module Structure

All new files should adhere to these naming and directory organization conventions.

### Application Module Structure

**Filenames: Django Conventions**:
- `admin.py` : Django standard for Django admin models
- `apps.py` : Django standard for app metadata and initializations
- `migrations.py` : Django standard for migrations
- `models.py` : Django standard for database ORM models
- `urls.py` : Django standard for urls
- `views.py` : Django standard for views

**Filenames: App Conventions**:
- `constants.py` : For shared constants
- `context_processors.py` : For new Django context processors
- `decorators.py` : For Django decorators 
- `enums.py` : For all enums relevant to this module
- `forms.py` : For Django forms
- `middleware.py` : Django standard for middleware
- `signals.py` : For new Django signal definitions
- `schemas.py` : For non-DB, in-memory container models with little business logic in them
- `mixins.py` : For view helpers that use HttpRequest/HttpResponse
- `services.py` : Encapsulated business logic
- `tests/synthetic_data.py` : For re-usable model building to support tests
- `context`  : If a module needs an app-wide encapsulated execution context

**Filenames: Reserved for Auto-discovery Mechanisms**:
- `monitors.py` : For auto-discovered background monitor tasks
- `settings.py` : For auto-discovered user-configuration options

**Filename Patterns**:
- `*_data.py` : For larger in-memory data classes needing their own module
- `*_helpers.py` : For general helpers with micellaneous responsibilities
- `*_manager.py` : For central control module, usually extending Singleton
- `*_mixin.py` : For larger mixins best included in their own module

**Directories: Django Per-app Conventions**:
- `management/commands` : Django standard for managemtn commands
- `templates` : Django standard for templates
- `templatetags` : Django standard for defining template tags

**Directories: Per App Conventions**:
- `tests/` : All module-specifc tests go here
- `tests/data/` : Non-code data supporting tests
- `assets/` : For non-code files and data that business logic depends on.
- `templates/{app_name}/modals/` : Templates for modal dialogs
- `templates/{app_name}/pages/` : Templates representing and entire HTML page or sub-page
- `templates/{app_name}/components/` : Templates representing an HTML fragment
- `tests/ui/` : For develoment-only UI tests and development tools (urls.py auto-discovered)
- `templates/tests/ui` : Templates supporting the UI testing and devtools views


