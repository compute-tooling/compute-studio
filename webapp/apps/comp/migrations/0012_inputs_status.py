# Generated by Django 2.2.1 on 2019-07-17 18:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("comp", "0011_auto_20190716_1750")]

    operations = [
        migrations.AddField(
            model_name="inputs",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("SUCCESS", "Success"),
                    ("FAIL", "Fail"),
                    ("WORKER_FAILURE", "Worker Failure"),
                ],
                default="SUCCESS",
                max_length=20,
            ),
            preserve_default=False,
        )
    ]