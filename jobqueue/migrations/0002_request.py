from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobqueue", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Request",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=30)),
                ("queue", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
