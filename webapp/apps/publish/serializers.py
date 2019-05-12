from rest_framework import serializers

from webapp.apps.users.models import Project


class PublishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            "title",
            "oneliner",
            "description",
            "repo_url",
            "server_size",
            "exp_task_time",
            "server_cost",
        )
