# Generated by Django 3.0.13 on 2021-05-07 22:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0024_project_social_image_link"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="embed_background_color",
            field=models.CharField(default="white", max_length=128),
        ),
    ]
