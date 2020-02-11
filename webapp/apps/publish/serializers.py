from rest_framework import serializers

from webapp.apps.users.models import Project


class PublishSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    cluster_type = serializers.CharField(required=False)
    sim_count = serializers.IntegerField()

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
            "listed",
            "owner",
            "cluster_type",
            "sim_count",
            "status",
        )
        read_only = ("sim_count", "status")
