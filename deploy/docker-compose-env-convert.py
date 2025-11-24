#!/usr/bin/env python3
"""
Convert bash export-style environment files to docker-compose .env format.

Transformations:
- Removes 'export ' prefix
- Strips surrounding quotes from values (both single and double)
- Preserves comments and blank lines
- Validates variable names

Usage:
    ./docker-compose-env-convert.py input.sh output.env
    cat input.sh | ./docker-compose-env-convert.py > output.env
    ./docker-compose-env-convert.py --validate input.sh
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, TextIO


class EnvConverter:
    """Convert bash export-style environment files to docker-compose format."""

    # Valid environment variable name pattern
    VAR_NAME_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

    # Pattern to match: export VAR="value" or export VAR='value'
    EXPORT_PATTERN = re.compile(
        r'''^
            \s*export\s+           # 'export' with whitespace
            ([A-Za-z_][A-Za-z0-9_]*)  # Variable name
            =                      # Equals sign
            (?:
                "([^"]*)"          # Double-quoted value (group 2)
                |'([^']*)'         # Single-quoted value (group 3)
                |(.*)              # Unquoted value (group 4)
            )
            \s*$                   # Optional trailing whitespace
        ''',
        re.VERBOSE
    )

    # Pattern to match: VAR="value" (no export)
    ASSIGN_PATTERN = re.compile(
        r'''^
            ([A-Za-z_][A-Za-z0-9_]*)  # Variable name
            =                      # Equals sign
            (?:
                "([^"]*)"          # Double-quoted value (group 2)
                |'([^']*)'         # Single-quoted value (group 3)
                |(.*)              # Unquoted value (group 4)
            )
            \s*$                   # Optional trailing whitespace
        ''',
        re.VERBOSE
    )

    def __init__(self, validate: bool = False, verbose: bool = False):
        self.validate = validate
        self.verbose = verbose
        self.errors = []
        self.warnings = []
        self.line_number = 0

    def convert_line(self, line: str) -> str:
        """
        Convert a single line from bash export format to docker-compose format.

        Args:
            line: Input line to convert

        Returns:
            Converted line (or original if it's a comment/blank)
        """
        self.line_number += 1
        original_line = line
        line = line.rstrip('\n\r')

        # Preserve empty lines and comments
        if not line.strip() or line.strip().startswith('#'):
            return line

        # Try to match export pattern
        match = self.EXPORT_PATTERN.match(line)
        if match:
            var_name = match.group(1)
            # Get value from whichever group matched (double quote, single quote, or unquoted)
            value = match.group(2) or match.group(3) or match.group(4) or ''

            if self.validate:
                self._validate_variable(var_name, value)

            if self.verbose:
                print(f"Line {self.line_number}: export {var_name}=\"...\" -> {var_name}=...",
                      file=sys.stderr)

            return f"{var_name}={value}"

        # Try to match assignment without export
        match = self.ASSIGN_PATTERN.match(line)
        if match:
            var_name = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4) or ''

            if self.validate:
                self._validate_variable(var_name, value)

            if self.verbose:
                print(f"Line {self.line_number}: {var_name}=\"...\" -> {var_name}=...",
                      file=sys.stderr)

            return f"{var_name}={value}"

        # Line doesn't match expected patterns
        warning = f"Line {self.line_number}: Unexpected format: {line[:50]}..."
        self.warnings.append(warning)
        if self.verbose:
            print(f"WARNING: {warning}", file=sys.stderr)

        # Return original line unchanged
        return line

    def _validate_variable(self, var_name: str, value: str):
        """Validate environment variable name and value."""
        if not self.VAR_NAME_PATTERN.match(var_name):
            error = f"Line {self.line_number}: Invalid variable name: {var_name}"
            self.errors.append(error)

        if not value and not value == '':  # Allow empty strings but catch None
            warning = f"Line {self.line_number}: Empty value for {var_name}"
            self.warnings.append(warning)

    def convert_file(self, input_file: TextIO, output_file: TextIO) -> bool:
        """
        Convert an entire file.

        Args:
            input_file: Input file object
            output_file: Output file object

        Returns:
            True if conversion successful (no errors)
        """
        self.errors = []
        self.warnings = []
        self.line_number = 0

        for line in input_file:
            converted = self.convert_line(line)
            output_file.write(converted + '\n')

        if self.verbose:
            print(f"\nProcessed {self.line_number} lines", file=sys.stderr)
            if self.warnings:
                print(f"Warnings: {len(self.warnings)}", file=sys.stderr)
            if self.errors:
                print(f"Errors: {len(self.errors)}", file=sys.stderr)

        return len(self.errors) == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert bash export-style env files to docker-compose .env format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'input',
        nargs='?',
        type=argparse.FileType('r'),
        default=sys.stdin,
        help='Input file (default: stdin)'
    )
    parser.add_argument(
        'output',
        nargs='?',
        type=argparse.FileType('w'),
        default=sys.stdout,
        help='Output file (default: stdout)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate variable names and values'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output (to stderr)'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check syntax only, do not write output'
    )

    args = parser.parse_args()

    converter = EnvConverter(validate=args.validate, verbose=args.verbose)

    try:
        if args.check:
            # Check mode: validate but don't write output
            import io
            null_output = io.StringIO()
            success = converter.convert_file(args.input, null_output)
        else:
            success = converter.convert_file(args.input, args.output)

        # Print errors and warnings to stderr
        if converter.errors:
            print("\nERRORS:", file=sys.stderr)
            for error in converter.errors:
                print(f"  {error}", file=sys.stderr)

        if converter.warnings and args.verbose:
            print("\nWARNINGS:", file=sys.stderr)
            for warning in converter.warnings:
                print(f"  {warning}", file=sys.stderr)

        if not success:
            sys.exit(1)

        if args.check and args.verbose:
            print("\n✓ File is valid", file=sys.stderr)

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except BrokenPipeError:
        # Handle pipe being closed (e.g., | head)
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
