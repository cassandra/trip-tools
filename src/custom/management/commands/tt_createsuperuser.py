from django.conf import settings
from django.core.management.base import BaseCommand

from custom.models import CustomUser


class Command( BaseCommand ):
    """
    Command provided so that we can automate creating the super user in
    deployments.  Normal django "createsuperuser" does not allow passing
    password.

    If the superuser already exists, updates the password to match the
    environment variable.
    """
    def handle( self, *args, **options ):
        admin_email = settings.DJANGO_SUPERUSER_EMAIL
        admin_password = settings.DJANGO_SUPERUSER_PASSWORD
        if not admin_email or not admin_password:
            raise ValueError( 'Need to set "DJANGO_SUPERUSER_EMAIL" and "DJANGO_SUPERUSER_PASSWORD"' )

        existing_user = CustomUser.objects.filter( email = admin_email ).first()
        if existing_user:
            existing_user.set_password( admin_password )
            existing_user.is_superuser = True
            existing_user.is_staff = True
            existing_user.save()
        else:
            CustomUser.objects.create_superuser(
                email = admin_email,
                password = admin_password,
            )
        return
