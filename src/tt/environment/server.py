from dataclasses import dataclass, field
import os
import re
from typing import Tuple
import urllib.parse

from django.core.exceptions import ImproperlyConfigured


@dataclass
class EnvironmentSettings:
    """
    Encapsulates the parsing of the environment variables that are needed.
    """

    # If the default value is "None" then the variable is required and its
    # absence will raise an ImproperlyConfigured error.  Optional
    # arguments should have a non-None value (empty string, zero, etc.)
    #
    DJANGO_SETTINGS_MODULE     : str           = None
    DJANGO_SERVER_PORT         : int           = 8000
    VERSION                    : str           = 'unknown'
    SECRET_KEY                 : str           = None
    DJANGO_SUPERUSER_EMAIL     : str           = None
    DJANGO_SUPERUSER_PASSWORD  : str           = None
    SITE_ID                    : str           = 1
    SITE_DOMAIN                : str           = 'localhost'
    SITE_NAME                  : str           = 'Trip Tools'
    ALLOWED_HOSTS              : Tuple[ str ]  = field( default_factory = tuple )
    CORS_ALLOWED_ORIGINS       : Tuple[ str ]  = field( default_factory = tuple )
    EXTRA_CSP_URLS             : Tuple[ str ]  = field( default_factory = tuple )
    # Database settings - either MySQL OR SQLite must be configured
    # MySQL (server-based): TT_DB_HOST, TT_DB_PORT, TT_DB_NAME, TT_DB_USER, TT_DB_PASSWORD
    DATABASE_HOST              : str           = None
    DATABASE_PORT              : str           = None
    DATABASE_NAME              : str           = None
    DATABASE_USER              : str           = None
    DATABASE_PASSWORD          : str           = None
    # SQLite (file-based): TT_DB_PATH
    DATABASES_NAME_PATH        : str           = None
    MEDIA_ROOT                 : str           = ''
    STORAGE_ENDPOINT_URL       : str           = ''
    STORAGE_REGION_NAME        : str           = ''
    STORAGE_BUCKET_NAME        : str           = ''
    STORAGE_ACCESS_KEY_ID      : str           = ''
    STORAGE_SECRET_ACCESS_KEY  : str           = ''
    STORAGE_LOCATION_PREFIX    : str           = ''
    STORAGE_CUSTOM_DOMAIN      : str           = ''
    REDIS_HOST                 : str           = 'localhost'
    REDIS_PORT                 : int           = 6379
    REDIS_KEY_PREFIX           : str           = ''
    EMAIL_SUBJECT_PREFIX       : str           = ''
    DEFAULT_FROM_EMAIL         : str           = ''
    SERVER_EMAIL               : str           = ''
    EMAIL_HOST                 : str           = ''
    EMAIL_PORT                 : int           = 587
    EMAIL_HOST_USER            : str           = ''
    EMAIL_HOST_PASSWORD        : str           = ''
    EMAIL_USE_TLS              : bool          = False
    EMAIL_USE_SSL              : bool          = False
    EMAIL_API_KEY              : str           = ''
    
    @property
    def environment_name(self) -> str:
        """
        Extract environment name from DJANGO_SETTINGS_MODULE.
        """
        if not self.DJANGO_SETTINGS_MODULE:
            return 'unknown'
        
        parts = self.DJANGO_SETTINGS_MODULE.split('.')
        if len(parts) > 1:
            return parts[-1]
        return 'unknown'
    
    @classmethod
    def get( cls ) -> 'EnvironmentSettings':
        env_settings = EnvironmentSettings()
        
        ###########
        # Core Django Settings

        # DJANGO_SETTINGS_MODULE is parsed by Django before this module
        # ever executes.  We include it here for completeness so there is
        # one place to see all env vars required, but it is not used by the
        # application code itself.
        #
        env_settings.DJANGO_SETTINGS_MODULE = cls.get_env_variable(
            'DJANGO_SETTINGS_MODULE',
            env_settings.DJANGO_SETTINGS_MODULE,
        )
        try:
            env_settings.DJANGO_SERVER_PORT = int(
                cls.get_env_variable(
                    'DJANGO_SERVER_PORT',
                    env_settings.DJANGO_SERVER_PORT,
                )
            )
        except ( TypeError, ValueError ):
            pass
        # Read version from TT_VERSION file (single source of truth)
        version_file_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'TT_VERSION')
        try:
            with open(version_file_path, 'r') as f:
                env_settings.VERSION = f.read().strip()
        except (FileNotFoundError, IOError) as e:
            raise ImproperlyConfigured(f"Cannot read version file {version_file_path}: {e}")
        env_settings.SECRET_KEY = cls.get_env_variable(
            'DJANGO_SECRET_KEY',
            env_settings.SECRET_KEY,
        )
        env_settings.DJANGO_SUPERUSER_EMAIL = cls.get_env_variable(
            'DJANGO_SUPERUSER_EMAIL',
            env_settings.DJANGO_SUPERUSER_EMAIL,
        )
        env_settings.DJANGO_SUPERUSER_PASSWORD = cls.get_env_variable(
            'DJANGO_SUPERUSER_PASSWORD',
            env_settings.DJANGO_SUPERUSER_PASSWORD )

        ###########
        # Databases
        # Either MySQL OR SQLite must be configured (validated at end)

        # MySQL/Postgres (server-based) - all 5 vars needed for complete config
        env_settings.DATABASE_HOST = cls.get_env_variable('TT_DB_HOST', '')
        env_settings.DATABASE_PORT = cls.get_env_variable('TT_DB_PORT', '')
        env_settings.DATABASE_NAME = cls.get_env_variable('TT_DB_NAME', '')
        env_settings.DATABASE_USER = cls.get_env_variable('TT_DB_USER', '')
        env_settings.DATABASE_PASSWORD = cls.get_env_variable('TT_DB_PASSWORD', '')

        # SQLite (file-based) - just needs path
        env_settings.DATABASES_NAME_PATH = cls.get_env_variable('TT_DB_PATH', '')

        ###########
        # Media
        
        env_settings.MEDIA_ROOT = cls.get_env_variable(
            'TT_MEDIA_PATH',
            env_settings.MEDIA_ROOT,
        )

        ###########
        # Object Storage (DigitalOcean Spaces)

        env_settings.STORAGE_ENDPOINT_URL = cls.get_env_variable(
            'TT_STORAGE_ENDPOINT_URL',
            env_settings.STORAGE_ENDPOINT_URL,
        )
        env_settings.STORAGE_REGION_NAME = cls.get_env_variable(
            'TT_STORAGE_REGION_NAME',
            env_settings.STORAGE_REGION_NAME,
        )
        env_settings.STORAGE_BUCKET_NAME = cls.get_env_variable(
            'TT_STORAGE_BUCKET_NAME',
            env_settings.STORAGE_BUCKET_NAME,
        )
        env_settings.STORAGE_ACCESS_KEY_ID = cls.get_env_variable(
            'TT_STORAGE_ACCESS_KEY_ID',
            env_settings.STORAGE_ACCESS_KEY_ID,
        )
        env_settings.STORAGE_SECRET_ACCESS_KEY = cls.get_env_variable(
            'TT_STORAGE_SECRET_ACCESS_KEY',
            env_settings.STORAGE_SECRET_ACCESS_KEY,
        )
        env_settings.STORAGE_LOCATION_PREFIX = cls.get_env_variable(
            'TT_STORAGE_LOCATION_PREFIX',
            env_settings.STORAGE_LOCATION_PREFIX,
        )
        env_settings.STORAGE_CUSTOM_DOMAIN = cls.get_env_variable(
            'TT_STORAGE_CUSTOM_DOMAIN',
            env_settings.STORAGE_CUSTOM_DOMAIN,
        )

        ###########
        # Redis
        
        env_settings.REDIS_HOST = cls.get_env_variable(
            'TT_REDIS_HOST',
            env_settings.REDIS_HOST,
        )
        try:
            env_settings.REDIS_PORT = int( cls.get_env_variable('TT_REDIS_PORT') )
        except ( TypeError, ValueError ):
            pass
        env_settings.REDIS_KEY_PREFIX = cls.get_env_variable(
            'TT_REDIS_KEY_PREFIX',
            env_settings.REDIS_KEY_PREFIX,
        )

        ###########
        # Email-related

        # General email settings
        env_settings.EMAIL_SUBJECT_PREFIX = "%s " % cls.get_env_variable(
            'TT_EMAIL_SUBJECT_PREFIX',
            env_settings.EMAIL_SUBJECT_PREFIX,
        )
        env_settings.DEFAULT_FROM_EMAIL = cls.get_env_variable(
            'TT_DEFAULT_FROM_EMAIL',
            env_settings.DEFAULT_FROM_EMAIL,
        )
        env_settings.SERVER_EMAIL = cls.get_env_variable(
            'TT_SERVER_EMAIL',
            env_settings.SERVER_EMAIL,
        )

        # Current: API-based emails (e.g., Resend, Mailgun)
        env_settings.EMAIL_API_KEY = cls.get_env_variable(
            'TT_EMAIL_API_KEY',
            env_settings.EMAIL_API_KEY,
        )

        # Previous: Direct SMTP settings (e.g., GMail)
        env_settings.EMAIL_HOST = cls.get_env_variable(
            'TT_EMAIL_HOST',
            env_settings.EMAIL_HOST,
        )
        try:
            env_settings.EMAIL_PORT = int( cls.get_env_variable(
                'TT_EMAIL_PORT',
                env_settings.EMAIL_PORT,
            ))
        except ( TypeError, ValueError ):
            pass
        env_settings.EMAIL_HOST_USER = cls.get_env_variable(
            'TT_EMAIL_HOST_USER',
            env_settings.EMAIL_HOST_USER,
        )
        env_settings.EMAIL_HOST_PASSWORD = cls.get_env_variable(
            'TT_EMAIL_HOST_PASSWORD',
            env_settings.EMAIL_HOST_PASSWORD,
        )
        env_settings.EMAIL_USE_TLS = cls.to_bool( cls.get_env_variable(
            'TT_EMAIL_USE_TLS',
            env_settings.EMAIL_USE_TLS,
        ))
        if env_settings.EMAIL_USE_TLS:
            env_settings.EMAIL_USE_SSL = False
        else:
            env_settings.EMAIL_USE_SSL = cls.to_bool( cls.get_env_variable(
                'TT_EMAIL_USE_SSL',
                env_settings.EMAIL_USE_SSL,
            ))

        ###########
        # Extras to satisfy security requirements:
        #   - Django strict host checking
        #   - web browser CORS/CSP issues

        allowed_host_list = [
            '127.0.0.1',
            'localhost',
        ]
        cors_allowed_origins_list = [
            f'http://127.0.0.1:{env_settings.DJANGO_SERVER_PORT}',
            f'http://localhost:{env_settings.DJANGO_SERVER_PORT}',
        ]

        extra_host_urls_str = cls.get_env_variable( 'TT_EXTRA_HOST_URLS', '' )
        if extra_host_urls_str:
            host_url_tuple_list = cls.parse_url_list_str( extra_host_urls_str )
            
            # Assume first extra host is the SITE_DOMAIN, but this does not
            # matter until the Django "sites" feature needs to be used (if
            # ever).
            #
            if host_url_tuple_list:
                env_settings.SITE_DOMAIN = host_url_tuple_list[0][0]
                
            for host, url in host_url_tuple_list:
                allowed_host_list.append( host )
                cors_allowed_origins_list.append( url )
                continue
        
        extra_csp_urls_str = cls.get_env_variable( 'TT_EXTRA_CSP_URLS', '' )
        if extra_csp_urls_str:
            host_url_tuple_list = cls.parse_url_list_str( extra_csp_urls_str )
            for host, url in host_url_tuple_list:
                cors_allowed_origins_list.append( url )
                continue

        if allowed_host_list:
            env_settings.ALLOWED_HOSTS += tuple( allowed_host_list )

        # For now, forego any fine-grained control of the allowed urls for CORS and CSP
        if cors_allowed_origins_list:
            env_settings.CORS_ALLOWED_ORIGINS += tuple( cors_allowed_origins_list )
            env_settings.EXTRA_CSP_URLS += tuple( cors_allowed_origins_list )

        ###########
        # Validation
        env_settings.validate_database_config()

        return env_settings

    def validate_database_config(self) -> None:
        """
        Ensure either MySQL OR SQLite database is fully configured.

        Raises ImproperlyConfigured if neither is properly set up.
        """
        # Check MySQL configuration (all 5 vars must be present and non-empty)
        mysql_vars = [
            self.DATABASE_HOST,
            self.DATABASE_PORT,
            self.DATABASE_NAME,
            self.DATABASE_USER,
            self.DATABASE_PASSWORD,
        ]
        has_mysql = all(v is not None and v != '' for v in mysql_vars)

        # Check SQLite configuration (just needs the path)
        has_sqlite = self.DATABASES_NAME_PATH is not None and self.DATABASES_NAME_PATH != ''

        if not has_mysql and not has_sqlite:
            raise ImproperlyConfigured(
                "Database not configured. Provide either:\n"
                "  - MySQL: TT_DB_HOST, TT_DB_PORT, TT_DB_NAME, TT_DB_USER, TT_DB_PASSWORD\n"
                "  - SQLite: TT_DB_PATH"
            )
    
    @classmethod
    def get_env_variable( cls, var_name, default = None ) -> str:
        try:
            return os.environ[var_name]
        except KeyError:
            if default is not None:
                return default
            error_msg = "Set the %s environment variable" % var_name
            raise ImproperlyConfigured(error_msg)

    @classmethod
    def to_bool( cls, value: object ) -> bool:
        if isinstance( value, bool ):
            return value
        if isinstance( value, str ):
            truthy_values = {'true', '1', 'on', 'yes', 'y', 't', 'enabled'}
            if isinstance( value, str ):
                return value.strip().lower() in truthy_values
            return False
        return bool( value )

    @classmethod
    def parse_url_list_str( cls, a_string : str ):
        url_str_list = re.split( r'[\s\;\,]+', a_string )
        host_url_tuple_list = list()
        for url_str in url_str_list:
            try:
                parsed_url = cls.parse_url( url_str )
                scheme = parsed_url.scheme
                host = parsed_url.hostname
                port = parsed_url.port
                if port:
                    normalized_url_str = f'{scheme}://{host}:{port}' 
                else:
                    normalized_url_str = f'{scheme}://{host}'
                host_url_tuple_list.append( ( host, normalized_url_str ) )

            except ( TypeError, ValueError ):
                pass
            continue
        return host_url_tuple_list
            
    @classmethod
    def parse_url( cls, url_str : str ) -> urllib.parse.ParseResult:
        if not url_str:
            raise ValueError()
        try:
            parsed_url = urllib.parse.urlparse( url_str )
            if not ( parsed_url.scheme and parsed_url.netloc ):
                raise ValueError()
            return parsed_url
        except TypeError:
            pass
        raise ValueError()
