# Generated by Django 3.0.11 on 2020-12-11 08:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0006_delete_usagerecord"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="cancel_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscription",
            name="trial_end",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
