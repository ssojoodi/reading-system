from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reader", "0004_book_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="thumbnail_content_type",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="book",
            name="thumbnail_data",
            field=models.TextField(blank=True),
        ),
    ]
