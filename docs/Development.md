<img src="../src/tt/static/img/tt-logo-467x200.png" alt="Trip Tools Logo" height="75">

# Development Guide for Contributors

## Requirements and Dependencies

- Python 3.11 (or higher) - installed.
- Redis - installed and running.
- A GitHub account.
- Database
    - MySQL is the default config, but it can be changed to SQLite.

## Tech Stack

- Django 4.2 (back-end)
- Javascript using jQuery 3.7 (front-end)
- Bootstrap 4 (CSS)
- MySQL or SQLite (database)
- Redis (caching)

## Getting Started

Follow these steps in order to begin contributing:

- **[Environment Setup](dev/Setup.md)** - Install and configure your development environment
- **[Contributor Workflow](dev/ContributorWorkflow.md)** - Git workflow and pull request process

## Core Guidelines (Essential Reading)

These documents contain fundamental concepts that apply across all development areas:

- **[Architecture Overview](dev/shared/architecture-overview.md)** - High-level system design and key patterns
- **[Coding Standards](dev/shared/coding-standards.md)** - Code organization, style, and conventions
- **[Data Model](dev/shared/data-model.md)** - Core domain models and relationships
- **[Testing Guidelines](dev/testing/testing-guidelines.md)** - Testing philosophy, best practices, and anti-patterns

## Development Areas

Choose the area that matches your contribution focus and browse the relevant documentation:

- **[Backend Development](dev/backend/)** - Django models, views, and business logic
- **[Frontend Development](dev/frontend/)** - Templates, styling, and user interface
- **[Testing](dev/testing/)** - Testing standards and patterns
- **[Shared Reference](dev/shared/)** - Common concepts used across all areas
