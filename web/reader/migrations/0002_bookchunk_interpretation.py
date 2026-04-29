from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reader", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="bookchunk",
            name="interpretation",
            field=models.TextField(blank=True),
        ),
    ]
