# Generated by Django 2.1.3 on 2018-12-04 21:17

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('upload', '0003_remove_fileinput_quick_calc'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileoutput',
            name='meta_data',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=None, null=True),
        ),
    ]
