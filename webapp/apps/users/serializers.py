from rest_framework import serializers

from webapp.apps.users.models import Project, EmbedApproval


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    cluster_type = serializers.CharField(required=False)
    sim_count = serializers.IntegerField(required=False)
    user_count = serializers.IntegerField(required=False)
    latest_tag = serializers.CharField(allow_null=True, required=False)
    # see to_representation
    # has_write_access = serializers.BooleanField(source="has_write_access")

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        if self.context.get("request"):
            user = self.context["request"].user
        else:
            user = None
        rep["has_write_access"] = obj.has_write_access(user)
        if not obj.has_write_access(user):
            rep.pop("sim_count")
            rep.pop("user_count")
        return rep

    class Meta:
        model = Project
        fields = (
            "title",
            "oneliner",
            "description",
            "repo_url",
            "repo_tag",
            "latest_tag",
            "exp_task_time",
            "server_cost",
            "cpu",
            "memory",
            "listed",
            "owner",
            "cluster_type",
            "sim_count",
            "status",
            "user_count",
            "callable_name",
            "tech",
        )
        read_only = (
            "sim_count",
            "user_count",
            "status",
        )


class ProjectWithVersionSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    cluster_type = serializers.CharField(required=False)
    sim_count = serializers.IntegerField(required=False)
    version = serializers.CharField(required=False)
    user_count = serializers.IntegerField(required=False)
    latest_tag = serializers.CharField(allow_null=True, required=False)
    # see to_representation
    # has_write_access = serializers.BooleanField(source="has_write_access")

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        if self.context.get("request"):
            user = self.context["request"].user
        else:
            user = None
        rep["has_write_access"] = obj.has_write_access(user)
        if not obj.has_write_access(user):
            rep.pop("sim_count")
            rep.pop("user_count")
        return rep

    class Meta:
        model = Project
        fields = (
            "title",
            "oneliner",
            "description",
            "repo_url",
            "repo_tag",
            "latest_tag",
            "exp_task_time",
            "server_cost",
            "cpu",
            "memory",
            "listed",
            "owner",
            "cluster_type",
            "sim_count",
            "status",
            "user_count",
            "version",
            "callable_name",
            "tech",
        )
        read_only = ("sim_count", "status", "user_count", "version")


class DeploymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            "latest_tag",
            "staging_tag",
        )


class EmbedApprovalSerializer(serializers.ModelSerializer):
    project = serializers.StringRelatedField()
    owner = serializers.StringRelatedField()

    class Meta:
        model = EmbedApproval
        fields = (
            "name",
            "project",
            "owner",
            "url",
        )
        read_only = ("owner", "project")
