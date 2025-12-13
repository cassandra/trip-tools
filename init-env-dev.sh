# Only activate virtual environment if not already active
# This prevents shell prompt nesting and makes the script idempotent
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "venv/bin/activate" ]; then
        . venv/bin/activate
        echo "✓ Virtual environment activated"
    else
        echo "ERROR: Virtual environment not found at venv/bin/activate"
        echo "Please create it first: python3.11 -m venv venv"
        return 1
    fi
else
    echo "✓ Virtual environment already active: $VIRTUAL_ENV"
    echo "  (Hint: run 'deactivate' first if you need to switch environments)"
fi

# Source development environment variables
if [ -f ".private/env/development.sh" ]; then
    . .private/env/development.sh
    echo "✓ Development environment variables loaded"
else
    echo "ERROR: Environment file not found at .private/env/development.sh"
    echo "Please create it first: make env-build-dev"
    return 1
fi

# Set up Node.js via nvm (for E2E testing)
if [ -f "$HOME/.nvm/nvm.sh" ]; then
    . "$HOME/.nvm/nvm.sh"
    if [ -f "testing/e2e/.nvmrc" ]; then
        nvm use --silent > /dev/null 2>&1
        echo "✓ Node.js $(node --version) activated via nvm"
    fi
elif command -v node > /dev/null 2>&1; then
    echo "✓ Node.js $(node --version) available (not using nvm)"
else
    echo "⚠ Node.js not found (optional, needed for E2E testing)"
fi
