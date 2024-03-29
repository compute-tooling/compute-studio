# Generated by Django 3.0.14 on 2021-06-20 19:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0027_project_use_iframe_resizer"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="tech",
            field=models.CharField(
                choices=[
                    ("python-paramtools", "Python-ParamTools"),
                    ("dash", "Dash"),
                    ("bokeh", "Bokeh"),
                    ("streamlit", "Streamlit"),
                ],
                max_length=64,
                null=True,
            ),
        ),
    ]
