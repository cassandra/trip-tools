#!/usr/bin/env python3

import argparse
import os
import re
import secrets
import shlex
import stat
import shutil
import string
import sys
import tempfile
from typing import Union

from dataclasses import dataclass

    
@dataclass
class SmtpSettings:
    host     : str
    port     : int
    use_tls  : bool
    use_ssl  : bool

    @property
    def is_valid(self):
        if not self.host:
            return False
        if not self.is_valid_port( self.port ):
            return False
        if not self.is_valid_encryption( use_tls = self.use_tls, use_ssl = self.use_ssl ):
            return False
        return True

    @staticmethod
    def is_valid_port( port: Union[str, int] ) -> bool:
        try:
            port_number = int( port )
            if ( port_number < 1 ) or ( port_number > 65535 ):
                return False
        except (TypeError, ValueError):
            return False
        return True
    
    @staticmethod
    def is_valid_encryption( use_tls: bool, use_ssl : bool ) -> bool:
        if use_tls and use_ssl:
            return False
        if not use_tls and not use_ssl:
            return False
        return True


@dataclass
class EmailSettings:
    email_address  : str
    password       : str
    smtp_settings  : SmtpSettings

    @property
    def is_valid(self):
        if not bool( self.email_address and self.password ):
            return False
        return self.smtp_settings.is_valid

    @staticmethod
    def is_valid_email( email: str ) -> bool:
        # This is approximate, not fully validating to specification.
        email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        return bool( re.match( email_regex, email ))


@dataclass
class EnvironmentConfig:
    label                 : str
    runs_in_docker        : bool  = False
    data_directory        : str   = 'data'
    secrets_directory     : str   = '.private/env'
    secrets_suffix        : str   = 'sh'
    django_server_port    : str   = '8000'
    redis_key_prefix      : str   = ''
    redis_subject_prefix  : str   = ''
    
    @classmethod
    def get( cls, env_name : str ):
        tt_home = os.path.join( os.environ['HOME'], '.tt' )
        if env_name == 'local':
            return EnvironmentConfig(
                label = env_name,
                runs_in_docker = True,
                data_directory = '/data',  # Location relative to internal Docker container
                secrets_directory = os.path.join( tt_home, 'env' ),
                secrets_suffix = 'env',
                django_server_port  = '8000',
                redis_key_prefix = '',
                redis_subject_prefix = '',
            )
        if env_name == 'development':
            return EnvironmentConfig(
                label = env_name,
                runs_in_docker = False,
                data_directory = 'data',
                secrets_directory = '.private/env',
                secrets_suffix = 'sh',
                django_server_port  = '8411',
                redis_key_prefix = 'dev',
                redis_subject_prefix = '[DEV] ',
            )
        return EnvironmentConfig(
            label = env_name,
        )

    
class TtEnvironmentGenerator:

    DEFAULT_ADMIN_EMAIL = 'admin@example.com'
    DATABASE_SUBDIR = 'database'
    MEDIA_SUBDIR = 'media'
    SH_FILE_SUFFIX = 'sh'

    def __init__( self,
                  env_name  : str = 'local',
                  verbose   : bool = False ):

        if env_name not in [ 'development', 'local', 'staging', 'production' ]:
            self.print_warning( f'Non-standard environment name "{env_name}".'
                                f' Ensure that the file "tt/settings/{env_name}.py" exists.' )
        
        self._env_name = env_name
        self._env_config = EnvironmentConfig.get( self._env_name )
        self._verbose = verbose
        
        self._settings_map = {
            'DJANGO_SETTINGS_MODULE': f'tt.settings.{self._env_name}',
            'DJANGO_SERVER_PORT': self._env_config.django_server_port,
            'TT_SUPPRESS_AUTHENTICATION':'true',
            'TT_REDIS_HOST': '127.0.0.1',
            'TT_REDIS_PORT': '6379',
            'TT_REDIS_KEY_PREFIX': self._env_config.redis_key_prefix,
            'TT_EMAIL_SUBJECT_PREFIX': self._env_config.redis_subject_prefix,
            'TT_EXTRA_HOST_URLS': '',  # To be filled in manually if/when running beyond localhost
            'TT_EXTRA_CSP_URLS': '',  # To be filled in manually if/when running beyond localhost
        }
        self._destination_filename = os.path.join(
            self._env_config.secrets_directory,
            f'{self._env_name}.{self._env_config.secrets_suffix}',
        )
        return
    
    def generate_env_file( self ):

        if self._env_name == 'production':
            print( '\n* ERROR * This script should not be used to generate production settings!\n' )
            return

        self.print_important(
            'About:\n'
            '\nThis script will help you generate your initial environment variables.'
            '\nYou usually only need to run this once.'
            '\nNone of the choices you make here are final.'
            '\nYou can modify any of the settings directly in the generated file.'
        )
        
        self._setup_secrets_directory()
        self._check_existing_env_file()

        db_dir, media_dir = self._get_data_directories()
        self._settings_map['TT_DB_PATH'] = db_dir
        self._settings_map['TT_MEDIA_PATH'] = media_dir

        email_settings = self._get_email_settings()

        # Emails are required for signin since it uses emailed codes, not passwords.
        if email_settings.is_valid:
            require_signin = self.input_boolean( 'Configure to require user sign in?', default = False )
            if require_signin:
                self._settings_map['TT_SUPPRESS_AUTHENTICATION'] = 'false'
        
        django_admin_email = email_settings.email_address
        django_admin_password = self._generate_memorable_password()
        
        from_email = email_settings.email_address
        server_email = email_settings.email_address

        self._settings_map['DJANGO_SECRET_KEY'] = self._generate_secret_key()
        self._settings_map['DJANGO_SUPERUSER_EMAIL'] = django_admin_email
        self._settings_map['DJANGO_SUPERUSER_PASSWORD'] = django_admin_password
        self._settings_map['TT_DEFAULT_FROM_EMAIL'] = from_email
        self._settings_map['TT_SERVER_EMAIL'] = server_email
        self._settings_map['TT_EMAIL_HOST_USER'] = email_settings.email_address
        self._settings_map['TT_EMAIL_HOST_PASSWORD'] = email_settings.password
        self._settings_map['TT_EMAIL_HOST'] = email_settings.smtp_settings.host
        self._settings_map['TT_EMAIL_PORT'] = str(email_settings.smtp_settings.port)
        self._settings_map['TT_EMAIL_USE_TLS'] = str(email_settings.smtp_settings.use_tls)
        self._settings_map['TT_EMAIL_USE_SSL'] = str(email_settings.smtp_settings.use_ssl)
        
        self._write_file()

        self.print_important( f'Review your settings file: {self._destination_filename}' )
        self.print_important( 'Your Django admin credentials:'
                              f'\n    Email: {django_admin_email}'
                              f'\n    Password: {django_admin_password}'
                              '\n\nIMPORTANT: Store these credentials securely!' )
        return
    
    def _setup_secrets_directory( self ):
        try:
            if not os.path.exists( self._env_config.secrets_directory ):
                self.print_notice( f'Creating directory: {self._env_config.secrets_directory}' )
                os.makedirs( self._env_config.secrets_directory, exist_ok = True )
                os.chmod( self._env_config.secrets_directory, stat.S_IRWXU )  # Read/write/execute for user only
            elif not os.path.isdir( self._env_config.secrets_directory ):
                self.print_warning( f'Secrets home "{self._env_config.secrets_directory}" not a directory.' )
                exit(1)
        except (OSError, IOError) as e:
            self.print_warning( f'Error setting up secrets directory: {e}' )
            exit(1)
        return
    
    def _check_existing_env_file( self ):

        if os.path.exists( self._destination_filename ):
            self.print_warning( f'WARNING: {self._destination_filename} already exists.' )
            overwrite = self.input_boolean( 'Do you want to overwrite it?', default = False )
            if not overwrite:
                self.print_warning( 'Env file generation cancelled.' )
                exit(1)

            import time
            timestamp = int(time.time())
            backup_filename = f'{self._destination_filename}.BAK.{timestamp}'
            try:
                self.print_notice( f'Creating backup: {backup_filename}' )
                shutil.copy2( self._destination_filename, backup_filename )
            except (OSError, IOError) as e:
                self.print_warning( f'Error creating backup: {e}' )
                exit(1)
        return

    def _get_data_directories( self ):
        
        if self._env_config.runs_in_docker:
            database_dir = os.path.join( self._env_config.data_directory, self.DATABASE_SUBDIR )
            media_dir = os.path.join( self._env_config.data_directory, self.MEDIA_SUBDIR )
            return ( database_dir, media_dir )
        
        self.print_important( 'Data Directory:\n'
                              '\nDefine a data directory for your database and uploaded "media" files.'
                              '\nThis script assumes these two will live in the same directory.'
                              '\nYou can alter this manually in the generated file if needed.' )

        while True:
            input_path = self.input_string( 'Enter your data directory',
                                            default = self._env_config.data_directory )
            expanded_path = os.path.expanduser( input_path )
            if os.path.isabs( expanded_path ):
                data_dir = expanded_path
            else:
                data_dir = os.path.abspath( expanded_path )  
                
            database_dir = os.path.join( data_dir, self.DATABASE_SUBDIR )
            media_dir = os.path.join( data_dir, self.MEDIA_SUBDIR )
            if not os.path.exists( data_dir ):
                self.print_warning( f'The directory "{data_dir}" does not exist.' )
                should_create = self.input_boolean( 'Do you want to create it?', default = False )
                if not should_create:
                    continue
                try:
                    os.makedirs( database_dir, exist_ok = True )
                    os.makedirs( media_dir, exist_ok = True )
                    return ( database_dir, media_dir )
                except (OSError, IOError) as e:
                    self.print_warning( f'Error creating directories: {e}' )
                    continue
            
            elif not os.path.isdir( data_dir ):
                self.print_warning( f'The path "{data_dir}" exists, but it is not a directory.' )
                continue
            
            else:
                try:
                    if not os.path.exists( database_dir ):
                        os.makedirs( database_dir, exist_ok = True )
                    if not os.path.exists( media_dir ):
                        os.makedirs( media_dir, exist_ok = True )
                    return ( database_dir, media_dir )
                except (OSError, IOError) as e:
                    self.print_warning( f'Error creating subdirectories: {e}' )
                    continue
            continue
        return
        
    def _get_email_settings( self ) -> EmailSettings:

        use_email = self.input_boolean( 'Configure email to allow alert notifications?', default = False )
        if use_email:
            self.print_notice( 'You may have to tweak your email provider\'s settings to allow this.' )
        else:
            return EmailSettings(
                email_address = self.DEFAULT_ADMIN_EMAIL,
                password = '',
                smtp_settings = SmtpSettings(
                    host = '',
                    port = '',
                    use_tls = False,
                    use_ssl = False,
                ),
            )

        while True:
            email_address = self.input_string( 'Enter your email address' )
            if EmailSettings.is_valid_email( email_address ):
                break
            self.print_warning( f'Invalid email address: {email_address}' )
            continue

        while True:
            password = self.input_string( 'Enter your email password' )
            if password:
                break
            self.print_warning( 'Password cannot be empty' )
            continue

        domain = email_address.split('@')[-1]

        smtp_settings = None
        if domain in self.COMMON_EMAIL_PROVIDER_SETTINGS:
            use_predefined = self.input_boolean( f'Use predefined settings for {domain}?' )
            if use_predefined:
                smtp_settings = self.COMMON_EMAIL_PROVIDER_SETTINGS[domain]
                
        if not smtp_settings:
            self.print_notice( 'Please provide SMTP settings.' )
            smtp_settings = self._get_smtp_settings()
            
        email_settings = EmailSettings(
            email_address = email_address,
            password = password,
            smtp_settings = smtp_settings,
        )
        
        # Optional SMTP validation
        test_smtp = self.input_boolean( 'Test SMTP connection now? (recommended)', default = True )
        if test_smtp and not self._test_smtp_connection(email_settings):
            self.print_warning( 'SMTP test failed. You may need to:\n'
                                '  - Enable "less secure apps" or use app-specific passwords\n'
                                '  - Check firewall settings\n'
                                '  - Verify SMTP server settings' )
            continue_anyway = self.input_boolean( 'Continue with these settings anyway?', default = False )
            if not continue_anyway:
                return self._get_email_settings()  # Retry email configuration
        
        return email_settings

    def _get_smtp_settings( self ) -> SmtpSettings:
        while True:
            host = self.input_string('Enter SMTP email host')
            if host:
                break
            self.print_warning( 'Host name cannot be empty' )
            continue

        use_tls = self.input_boolean( 'SMTP server uses TLS (STARTTLS)', default = True )
        if use_tls:
            use_ssl = False
            default_port = 587
        else:
            use_ssl = True
            default_port = 465

        while True:
            port = self.input_string('Enter SMTP port', default = str(default_port) )
            if SmtpSettings.is_valid_port( port ):
                break
            self.print_warning( f'Invalid port "{port}". Must be an integer in range [ 1024, 65535 ]' )
            continue
        
        return SmtpSettings(
            host = host,
            port = port,
            use_tls = use_tls,
            use_ssl = use_ssl,
        )
    
    def _test_smtp_connection(self, email_settings: EmailSettings) -> bool:
        """
        Test SMTP connection without sending email.
        Returns True if connection successful, False otherwise.
        """
        try:
            import smtplib
            
            self.print_notice( 'Testing SMTP connection...' )
            
            smtp_class = smtplib.SMTP_SSL if email_settings.smtp_settings.use_ssl else smtplib.SMTP
            
            with smtp_class(email_settings.smtp_settings.host, email_settings.smtp_settings.port, timeout=10) as server:
                if email_settings.smtp_settings.use_tls:
                    server.starttls()
                
                server.login(email_settings.email_address, email_settings.password)
                self.print_success( 'SMTP connection test successful!' )
                return True
                
        except ImportError:
            self.print_warning( 'Cannot test SMTP connection: smtplib not available' )
            return True  # Don't fail if we can't test
        except Exception as e:
            self.print_warning( f'SMTP connection test failed: {e}' )
            return False
        
    def _generate_memorable_password( self, num_words : int = 3, separator : str = "-" ):

        words = [
            'apple', 'banana', 'cherry', 'delta', 'eagle', 'falcon', 'grape', 
            'hunter', 'island', 'joker', 'kitten', 'lemon', 'melon', 'ninja', 'ocean',
            'piano', 'queen', 'robot', 'stone', 'tiger', 'unity', 'voice', 'water',
            'xenon', 'yacht', 'zebra', 'anchor', 'bridge', 'camera', 'dream', 'energy'
        ]

        chosen_words = [ secrets.choice(words) for _ in range(num_words) ]
        random_number = str( secrets.randbelow( 1000 ))  # A number between 0-999
        chosen_words.append( str(random_number) )
            
        password = separator.join(chosen_words)
        return password

    def _write_file( self ):

        is_sh_file = self._destination_filename.endswith( self.SH_FILE_SUFFIX )
        
        # Use atomic write with temporary file for safety
        temp_dir = os.path.dirname(self._destination_filename)
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=temp_dir, delete=False, 
                                             prefix='.env_temp_', suffix='.tmp') as temp_fh:
                temp_filename = temp_fh.name
                for name, value in self._settings_map.items():
                    value = str(value)  # ensure string
                    if is_sh_file:
                        escaped_value = shlex.quote(value)
                        temp_fh.write( f'export {name}={escaped_value}\n' )
                    else:
                        temp_fh.write( f'{name}={value}\n' )
                    continue
            
            # Set secure file permissions before moving
            os.chmod( temp_filename, stat.S_IRUSR | stat.S_IWUSR )
            
            # Atomically move temp file to final destination
            shutil.move( temp_filename, self._destination_filename )
            self.print_success( f'File created: {self._destination_filename}' )
            
        except (OSError, IOError) as e:
            self.print_warning( f'Error writing environment file: {e}' )
            # Clean up temp file if it exists
            if 'temp_filename' in locals() and os.path.exists(temp_filename):
                try:
                    os.unlink(temp_filename)
                except OSError:
                    pass
            raise

        if self._verbose:
            self.print_debug( 'Files contents:' )
            print( '----------')
            with open( self._destination_filename, 'r' ) as fh:
                content = fh.read()
                # Mask sensitive values in verbose output
                import re
                sensitive_patterns = [
                    (r'(DJANGO_SECRET_KEY=)([^\n]+)', r'\1[MASKED]'),
                    (r'(DJANGO_SUPERUSER_PASSWORD=)([^\n]+)', r'\1[MASKED]'),
                    (r'(TT_EMAIL_HOST_PASSWORD=)([^\n]+)', r'\1[MASKED]'),
                ]
                for pattern, replacement in sensitive_patterns:
                    content = re.sub(pattern, replacement, content)
                print( content, end = '' )
            print('----------')    
        return
    
    def _generate_secret_key( self, length : int = 50 ):
        chars = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(chars) for _ in range(length))

    @classmethod
    def input_boolean( cls, message : str, default : bool = None ) -> bool:

        if default is not None:
            if default:
                prompt = '[Y/n]'
            else:
                prompt = '[y/N]'
        else:
            prompt = '[y/n]'
            
        while True:
            value_str = input( f'{message} {prompt}: ').strip().lower()
            if not value_str and default is not None:
                return default
            if value_str in [ 'y', 'yes' ]:
                return True
            elif value_str in [ 'n', 'no' ]:
                return False
            cls.print_warning( 'Please answer "y" or "n".' )
            continue
        
    @classmethod
    def input_string( cls, message : str, default : str = None ) -> str:
        if default:
            prompt = f'[{default}]'
        else:
            prompt = ''
        value = input( f'{message} {prompt}: ' ).strip()
        if not value and default is not None:
            return default
        return value
    
    @staticmethod
    def print_debug( message : str ):
        print( f'[DEBUG] {message}' )

    @staticmethod
    def print_notice( message : str ):
        print( f'\n[NOTICE] {message}\n' )

    @staticmethod
    def print_warning( message : str ):
        print( f'\n\033[96m[WARNING]\033[0m {message}\n' )  # Yellow text

    @staticmethod
    def print_success( message : str ):
        print( f'\033[32m[SUCCESS]\033[0m {message}' )  # Green text

    @staticmethod
    def print_important(message: str):
        lines = message.split('\n')
        max_width = min( 80, max( len(line) for line in lines ) + 6 )

        def pad_line( line ):
            return line.center( max_width )

        padded_lines = [ pad_line(line) for line in lines ]
        border = " " * max_width

        # Inverted fg/bg text
        print( f'\n\033[7m{border}\033[0m' )
        for padded_line in padded_lines:
            print( f'\033[7m{padded_line}\033[0m' )
            continue
        print( f'\033[7m{border}\033[0m\n' )
        return

    @staticmethod
    def zzzprint_important( message : str ):
        border = '=' * ( min( len(message), 74 ) + 6)
        print( f'\n\033[7m{border}\033[0m' )  # Blue border
        print( f'\033[7m{message}\033[0m' )  # Blue text
        print( f'\033[7m{border}\033[0m\n' )  # Blue border
        
    COMMON_EMAIL_PROVIDER_SETTINGS = {
        'gmail.com': SmtpSettings(
            host = 'smtp.gmail.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'yahoo.com': SmtpSettings(
            host = 'smtp.mail.yahoo.com',
            port = 465,
            use_tls = False,
            use_ssl = True,
        ),
        'outlook.com': SmtpSettings(
            host = 'smtp.office365.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'hotmail.com': SmtpSettings(
            host = 'smtp.office365.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'icloud.com': SmtpSettings(
            host = 'smtp.mail.me.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'aol.com': SmtpSettings(
            host = 'smtp.aol.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'zoho.com': SmtpSettings(
            host = 'smtp.zoho.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'protonmail.com': SmtpSettings(
            host = '127.0.0.1',  # Requires the ProtonMail Bridge app
            port = 1025,  # Default for ProtonMail Bridge
            use_tls = True,
            use_ssl = False,
        ),
        'fastmail.com': SmtpSettings(
            host = 'smtp.fastmail.com',
            port = 465,
            use_tls = False,
            use_ssl = True,
        ),
        'mail.com': SmtpSettings(
            host = 'smtp.mail.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
    }


def parse_command_line_args():
    
    parser = argparse.ArgumentParser(
        description = 'Generate environment variables for Trip Tools.',
        add_help = True,
    )
    parser.add_argument(
        '--env-name',
        type = str,
        default = 'local',
        help = 'Name of the environment file to generate (default: "local").',
    )
    parser.add_argument(
        '--verbose',
        action = 'store_true',
        help = 'Enable verbose output for debugging purposes.',
    )

    args, unknown = parser.parse_known_args()

    if unknown:
        print( f'[ERROR] Unrecognized arguments: {" ".join(unknown)}\n' )
        parser.print_help()
        sys.exit(1)

    if not args.env_name.isidentifier():
        print( '[ERROR] Environment name must be a valid Python identifier.' )
        sys.exit(1)

    return args


if __name__ == '__main__':

    args = parse_command_line_args()
    generator = TtEnvironmentGenerator(
        env_name = args.env_name,
        verbose = args.verbose,
    )
    generator.generate_env_file()
    
