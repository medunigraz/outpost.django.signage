# Generated by Django 2.2.28 on 2024-03-26 15:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("signage", "0010_auto_20230919_1433"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="display",
            name="screen",
        ),
    ]
