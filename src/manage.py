#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import re
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tt.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    set_runserver_defaults_if_needed()  # TT Customization
    execute_from_command_line( sys.argv )

    
def set_runserver_defaults_if_needed():
    """
    Set default hostname and port for runserver command.

    Defaults:
    - Hostname: 'localhost' (ensures cookie sharing with chrome extension)
    - Port: from DJANGO_SERVER_PORT env var if set

    These defaults are applied only when not explicitly specified by the user.
    """
    if len( sys.argv ) < 2 or sys.argv[1] != 'runserver':
        return

    default_hostname = 'localhost'
    default_port = os.environ.get( 'DJANGO_SERVER_PORT' )

    # Check what the user has already specified
    has_address = runserver_has_address_specified()

    if has_address:
        # User specified something - only add port if they gave hostname only
        if runserver_has_hostname_only_arg() and default_port:
            last_arg = sys.argv[-1]
            sys.argv[-1] = f'{last_arg}:{default_port}'
    else:
        # User specified nothing - add our defaults
        if default_port:
            sys.argv.append( f'{default_hostname}:{default_port}' )
        else:
            sys.argv.append( default_hostname )


def runserver_has_address_specified() -> bool:
    """Check if any address (hostname, port, or both) is specified."""
    if len( sys.argv ) < 3:
        return False

    for arg in sys.argv[2:]:
        if arg.startswith( '--' ):
            continue
        # Any non-flag argument is an address specification
        return True

    return False


def runserver_has_hostname_only_arg() -> bool:
    """Check if the last positional arg is a hostname without port."""
    if len( sys.argv ) < 3:
        return False

    last_arg = sys.argv[-1]
    if last_arg.startswith( '--' ):
        return False
    # Port only (e.g., "8000")
    if re.fullmatch( r'\d+', last_arg ):
        return False
    # Has port (e.g., "localhost:8000" or "127.0.0.1:8000")
    if ':' in last_arg:
        return False
    # IP address or hostname without port
    return True


if __name__ == '__main__':
    main()
