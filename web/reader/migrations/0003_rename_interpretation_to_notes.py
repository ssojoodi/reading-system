from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("reader", "0002_bookchunk_interpretation"),
    ]

    operations = [
        migrations.RenameField(
            model_name="bookchunk",
            old_name="interpretation",
            new_name="notes",
        ),
    ]
