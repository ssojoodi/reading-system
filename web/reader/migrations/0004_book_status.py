from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reader", "0003_rename_interpretation_to_notes"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "New"),
                    ("chunked", "Chunked"),
                    ("interpreted", "Interpreted"),
                    ("finalized", "Finalized"),
                ],
                default="new",
                max_length=20,
            ),
        ),
    ]
