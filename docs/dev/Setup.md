<img src="../../src/tt/static/img/tt-logo-467x200.png" alt="Trip Tools Logo" height="75">

# Development Setup (one-time setup for external devevelopment)

## Quick Setup (Recommended)

For a streamlined setup experience, we provide an automated setup script that handles most of the configuration for you.

### Prerequisites
1. Fork the repository on GitHub (see manual steps below for details)
2. Clone your fork locally
3. Ensure Python 3.11 is installed
4. Node.js 20.x (for E2E testing) - see [Dependencies](Dependencies.md#nodejs)

### Automated Setup
After cloning your fork, run the setup script from the project root:
```bash
cd trip-tools
./deploy/dev-setup.sh
```

This script will:
- Configure git settings and remotes
- Generate environment variables
- Create and activate a Python virtual environment
- Install all required packages
- Initialize the database
- Run validation tests

The script is interactive and will prompt you for necessary information. It's safe to run multiple times if needed.

## Manual Setup (Alternative)

If you prefer to set up manually or need more control over the process, follow these detailed steps (details below):
```
git clone https://github.com/${YOURUSERNAME}/trip-tools.git
cd trip-tools
make env-build-dev
python3.11 -m venv venv
. ./init-env-dev.sh
pip install -r src/tt/requirements/development.txt
./src/manage.py check
./src/manage.py migrate
./src/manage.py tt_createsuperuser
./src/manage.py tt_creategroups
./src/manage.py tt_createseeddata
./src/manage.py runserver
```

## Fork the Repository

- Sign into your GitHub account (required).
- Go to the main repository on GitHub: https://github.com/cassandra/trip-tools
- Click the "Fork" button in the upper-right corner. (You will be forking from the `main` branch.)
- This creates a copy of the repository in the your GitHub account (keep same name if you can for simplicity).
- The forked repo will be located at https://github.com/${YOURUSERNAME}/trip-tools.git (if you kept the same repo name).

## Local Repository Setup

Decide where you want to download the code to (adjust the following):
``` shell
PROJ_DIR="${HOME}/proj"
mkdir -p $PROJ_DIR
cd $PROJ_DIR
```

Clone your fork to your local development environment:
``` shell
git clone https://github.com/${YOURUSERNAME}/trip-tools.git

# Or use the SSH URL if you have SSH keys set up:
git clone git@github.com:${YOURUSERNAME}/trip-tools.git
```

Now change into that directory and configure the repo including adding the source as the "upstream" target: 
``` shell
cd trip-tools

git config --global user.name "${YOUR_NAME}"
git config --global user.email "${YOUR_EMAIL}"

git remote add upstream https://github.com/cassandra/trip-tools.git
```

Your "origin" should already be pointing to your forked repository, but check this and the "upstream" settings:
``` shell
git remote -v

# Expect
origin    https://github.com/${YOURUSERNAME}/trip-tools.git (fetch)
origin    https://github.com/${YOURUSERNAME}/trip-tools.git (push)
upstream  https://github.com/cassandra/trip-tools.git (fetch)
upstream  https://github.com/cassandra/trip-tools.git (push)
```

If your origin is not set properly, re-verify after setting with:
``` shell
git remote add origin git@github.com:${YOURUSERNAME}/trip-tools.git

# If no SSH keys were added to GitHub, you'll need this instead:
git remote set-url origin https://github.com/${YOURUSERNAME}/trip-tools.git
```

## Environment Setup

Generate the environment variable file and review with the command below. The file will contain sensitive secrets and are stored in a `.private` directory. Also note that administrative credentials created during this next step.
``` shell
make env-build-dev
```
This generates an environment variable file that we "source" before running:
```
$PROJ_DIR/.private/env/development.sh
```
This `.private` directory and its files should not be checked into the code repository. There is an existing `.gitignore` entry to prevent this.  The adminstrative credentials generated can also be seen in that file.

Next, create the Python virtual environment.
``` shell
cd $PROJ_DIR
python3.11 -m venv venv
```
Now source the environment and virtual environment with this convenience script:
``` shell
. ./init-env-dev.sh
```
In the future, just source'ing this script is all you need to set things up for development (virtual env and env vars).

Next, install all the app's required Python packages (make sure you are in the virtual env).
``` shell
pip install -r src/tt/requirements/development.txt
```

### App and Database Initializations

Initialize the database and add the admin users and groups.
``` shell
cd $PROJ_DIR
./src/manage.py check
./src/manage.py migrate
./src/manage.py tt_createsuperuser
./src/manage.py tt_creategroups
./src/manage.py tt_createseeddata
```

It is a good idea to run the tests to validate that you can and that the installation seem fine.
``` shell
cd $PROJ_DIR
./src/manage.py test
```

### Running

Ensure that the Redis server is running (see the Dependencies page for installation instructions), then:

``` shell
cd $PROJ_DIR
./src/manage.py runserver
```

Then, visit: [http://127.0.0.1:6777](http://127.0.0.1:6777) to access the app.

## Daily Development Commands

Once your environment is set up, these are the common commands for daily development work:

### Environment Activation
```bash
# Daily development setup (run this first each day)
. ./init-env-dev.sh  # Sources virtual env and environment variables
```

### Django Management
```bash
cd $PROJ_DIR/src

# Database operations
./src/manage.py migrate
./src/manage.py makemigrations
./src/manage.py check

# Testing
./src/manage.py test                    # Run all tests
./src/manage.py test weather.tests     # Run specific app tests

# User management
./src/manage.py tt_createsuperuser
./src/manage.py tt_creategroups
./src/manage.py tt_createseeddata

# Development server
./src/manage.py runserver              # Runs on http://127.0.0.1:6777
```

### Code Quality
```bash
# Linting and formatting (from development.txt requirements)
black src/                            # Format code
flake8 --config=src/.flake8-ci src/   # Lint code with CI configuration
autopep8 --in-place --recursive src/  # Auto-format
```

### Docker Operations
```bash
# Build and run in containers
make docker-build
make docker-run-fg                 # Foreground
make docker-run                    # Background
make docker-stop
```

### E2E Testing (Playwright)
```bash
# First-time setup (installs npm packages and Playwright browsers)
make test-e2e-install

# Seed test data (creates test user for authentication)
make test-e2e-seed

# Run all E2E tests
make test-e2e

# Run specific test categories
make test-e2e-webapp-extension-none   # Web application UI tests (no Chrome extension)
make test-e2e-webapp-extension-sim    # Web app tests with simulated Chrome extension
make test-e2e-webapp-extension-real   # Web app tests with real Chrome extension
make test-e2e-extension-isolated      # Chrome extension tests with mocked API server
```

### Documentation

Use `grip` for previewing GitHub markdown documents locally.

```
sudo apt install grip
cd $PROJ_DIR
grip

# Then visit:
http://localhost:6419
```

## Getting Started

A look through these docs might also be a good starting point:
- [Data Model](shared/data-model.md)
- [Architecture](shared/architecture-overview.md)

