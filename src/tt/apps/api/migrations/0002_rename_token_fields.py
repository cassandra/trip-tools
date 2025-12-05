from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="apitoken",
            old_name="key_prefix",
            new_name="lookup_key",
        ),
        migrations.RenameField(
            model_name="apitoken",
            old_name="key_hash",
            new_name="api_token_hash",
        ),
    ]
