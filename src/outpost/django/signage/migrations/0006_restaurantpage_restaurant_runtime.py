# Generated by Django 2.2.28 on 2023-03-01 19:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("signage", "0005_auto_20230301_1739"),
    ]

    operations = [
        migrations.AddField(
            model_name="restaurantpage",
            name="restaurant_runtime",
            field=models.DurationField(blank=True, null=True),
        ),
    ]