#!/usr/bin/env python3
"""
Mock server for extension testing.

A simple HTTP server that returns profile-controlled responses for API endpoints.
Uses Python's built-in http.server for zero external dependencies.

Usage:
    python server.py --port 6779 --profile ext_auth_success

Endpoints:
    GET  /api/v1/me/           - Returns profile-controlled user info
    POST /__test__/profile     - Changes active profile at runtime
    GET  /__test__/health      - Health check
    GET  /user/extensions/*    - Serves static test pages
"""

import argparse
import json
import os
import time
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

from profiles import (
    PROFILES,
    get_current_profile_name,
    get_endpoint_config,
    set_current_profile,
)


class MockServerHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with profile-controlled API responses."""

    def __init__(self, *args, test_pages_dir=None, **kwargs):
        self.test_pages_dir = test_pages_dir
        super().__init__(*args, **kwargs)

    def handle(self):
        """Handle requests, suppressing expected connection errors.

        BrokenPipeError and ConnectionResetError are expected during testing
        when clients abort connections (e.g., timeout tests). These are not
        real errors and should not pollute test output.
        """
        try:
            super().handle()
        except BrokenPipeError:
            # Client disconnected before response completed - expected in timeout tests
            pass
        except ConnectionResetError:
            # Client reset connection - expected when aborting requests
            pass

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # API endpoint: /api/v1/me/
        if path == '/api/v1/me/' or path == '/api/v1/me':
            self._handle_api_me()
            return

        # API endpoint: /api/v1/extension/status/
        if path == '/api/v1/extension/status/' or path == '/api/v1/extension/status':
            self._handle_api_extension_status()
            return

        # Test control: health check
        if path == '/__test__/health':
            self._send_json_response(200, {
                'status': 'ok',
                'profile': get_current_profile_name(),
            })
            return

        # Test control: get current profile
        if path == '/__test__/profile':
            self._send_json_response(200, {
                'profile': get_current_profile_name(),
            })
            return

        # Static files: serve test pages
        self._serve_static_file(path)

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Test control: set profile
        if path == '/__test__/profile':
            self._handle_set_profile()
            return

        # Unknown endpoint
        self._send_json_response(404, {'error': 'Not found'})

    def do_DELETE(self):
        """Handle DELETE requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # API endpoint: /api/v1/tokens/<key>/
        if path.startswith('/api/v1/tokens/'):
            self._handle_api_token_delete()
            return

        # Unknown endpoint
        self._send_json_response(404, {'error': 'Not found'})

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def _handle_api_me(self):
        """Handle GET /api/v1/me/ with profile-controlled response."""
        config = get_endpoint_config('api_me')

        # Apply delay if configured
        delay_ms = config.get('delay_ms', 0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

        self._send_json_response(
            config.get('status', 200),
            config.get('body', {}),
        )

    def _handle_api_extension_status(self):
        """Handle GET /api/v1/extension/status/ with profile-controlled response.

        This endpoint is used for auth validation and returns a sync envelope.
        Uses same profile config as api_me for status/auth, but wraps response
        in the expected {data: {...}} format.
        """
        config = get_endpoint_config('api_extension_status')

        # Apply delay if configured
        delay_ms = config.get('delay_ms', 0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

        status = config.get('status', 200)
        body = config.get('body', {})

        # For success responses, wrap in data envelope like real API
        if status == 200:
            wrapped_body = {'data': body}
        else:
            wrapped_body = body

        self._send_json_response(status, wrapped_body)

    def _handle_api_token_delete(self):
        """Handle DELETE /api/v1/tokens/<key>/ with profile-controlled response."""
        config = get_endpoint_config('api_tokens_delete')

        # Apply delay if configured
        delay_ms = config.get('delay_ms', 0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

        status = config.get('status', 204)
        if status == 204:
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()
        else:
            self._send_json_response(status, config.get('body', {}))

    def _handle_set_profile(self):
        """Handle POST /__test__/profile to change active profile."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body) if body else {}

            profile_name = data.get('profile')
            if not profile_name:
                self._send_json_response(400, {'error': 'Missing profile name'})
                return

            if profile_name not in PROFILES:
                self._send_json_response(400, {
                    'error': f'Unknown profile: {profile_name}',
                    'available': list(PROFILES.keys()),
                })
                return

            set_current_profile(profile_name)
            self._send_json_response(200, {'profile': profile_name})

        except json.JSONDecodeError:
            self._send_json_response(400, {'error': 'Invalid JSON'})
        except Exception as e:
            self._send_json_response(500, {'error': str(e)})

    def _serve_static_file(self, path):
        """Serve static files from test_pages directory."""
        # Normalize path
        if path == '/' or path == '':
            path = '/index.html'
        elif path.endswith('/'):
            path = path + 'index.html'

        # Security: prevent directory traversal
        if '..' in path:
            self._send_json_response(403, {'error': 'Forbidden'})
            return

        # Build file path
        file_path = os.path.join(self.test_pages_dir, path.lstrip('/'))

        # If path is a directory, try index.html
        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, 'index.html')

        if not os.path.isfile(file_path):
            self._send_json_response(404, {'error': f'Not found: {path}'})
            return

        # Determine content type
        content_type = 'text/html'
        if file_path.endswith('.js'):
            content_type = 'application/javascript'
        elif file_path.endswith('.css'):
            content_type = 'text/css'
        elif file_path.endswith('.json'):
            content_type = 'application/json'

        # Read and serve file
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(content)

        except IOError:
            self._send_json_response(500, {'error': 'Failed to read file'})

    def _send_json_response(self, status, data):
        """Send a JSON response with CORS headers."""
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_headers(self):
        """Send CORS headers to allow extension access."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def log_message(self, format, *args):
        """Log HTTP requests."""
        print(f'[{get_current_profile_name()}] {self.address_string()} - {format % args}')


def run_server(port, profile, test_pages_dir):
    """Start the mock server."""
    # Set initial profile
    set_current_profile(profile)

    # Create handler with test_pages_dir
    handler = partial(MockServerHandler, test_pages_dir=test_pages_dir)

    # Start server
    server = HTTPServer(('localhost', port), handler)
    print(f'Mock server starting on http://localhost:{port}')
    print(f'Profile: {profile}')
    print(f'Test pages: {test_pages_dir}')
    print(f'Available profiles: {", ".join(PROFILES.keys())}')
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down...')
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description='Mock server for extension testing')
    parser.add_argument(
        '--port',
        type=int,
        default=6779,
        help='Port to run the server on (default: 6779)',
    )
    parser.add_argument(
        '--profile',
        type=str,
        default='ext_auth_success',
        help=f'Initial profile to use. Options: {", ".join(PROFILES.keys())}',
    )
    parser.add_argument(
        '--test-pages',
        type=str,
        default=None,
        help='Directory containing test pages (default: ./test_pages)',
    )

    args = parser.parse_args()

    # Determine test pages directory
    if args.test_pages:
        test_pages_dir = os.path.abspath(args.test_pages)
    else:
        # Default to test_pages relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        test_pages_dir = os.path.join(script_dir, 'test_pages')

    if not os.path.isdir(test_pages_dir):
        print(f'Error: Test pages directory not found: {test_pages_dir}')
        return 1

    # Validate profile
    if args.profile not in PROFILES:
        print(f'Error: Unknown profile: {args.profile}')
        print(f'Available profiles: {", ".join(PROFILES.keys())}')
        return 1

    run_server(args.port, args.profile, test_pages_dir)
    return 0


if __name__ == '__main__':
    exit(main())
