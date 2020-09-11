from rest_framework import serializers

from webapp.apps.users.models import Project, EmbedApproval, Deployment, Tag


class DeploymentSerializer(serializers.ModelSerializer):
    project = serializers.StringRelatedField()

    class Meta:
        model = Deployment
        fields = (
            "project",
            "created_at",
            "deleted_at",
            "last_load_at",
            "last_ping_at",
            "name",
            "tag",
            "status",
        )
        read_only = (
            "project",
            "created_at",
            "last_loaded_at",
            "name",
            "tag",
        )


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    cluster_type = serializers.CharField(required=False)
    sim_count = serializers.IntegerField(required=False)
    user_count = serializers.IntegerField(required=False)
    latest_tag = serializers.StringRelatedField(required=False)
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
    latest_tag = serializers.StringRelatedField(required=False)
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
        read_only = ("sim_count", "status", "user_count", "version", "latest_tag")


class TagUpdateSerializer(serializers.Serializer):
    latest_tag = serializers.CharField(allow_null=True, required=False)
    staging_tag = serializers.CharField(allow_null=True, required=False)

    def validate(self, attrs):
        if attrs.get("latest_tag") is None and attrs.get("staging_tag") is None:
            raise serializers.ValidationError(
                "Either latest_tag or staging_tag must be specificied"
            )
        return attrs


class TagSerializer(serializers.ModelSerializer):
    project = serializers.StringRelatedField()

    class Meta:
        model = Tag
        fields = (
            "project",
            "image_tag",
            "memory",
            "cpu",
            "created_at",
        )

        read_only = (
            "project",
            "memory",
            "cpu",
            "created_at",
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
