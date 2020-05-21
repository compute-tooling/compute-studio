from rest_framework import serializers
from guardian.shortcuts import get_users_with_perms

from webapp.apps.publish.serializers import PublishSerializer

from .exceptions import ResourceLimitException
from .models import Inputs, Simulation, PendingPermission, ModelConfig


class OutputsSerializer(serializers.Serializer):
    """
    Serialze data from the simulation complete callback.
    """

    job_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=(("SUCCESS", "Success"), ("FAIL", "Fail")))
    traceback = serializers.CharField(required=False)
    model_version = serializers.CharField(required=False)
    meta = serializers.JSONField()
    outputs = serializers.JSONField(required=False)
    # only used with v0!
    aggr_outputs = serializers.JSONField(required=False)
    version = serializers.CharField(required=False)

    def to_internal_value(self, data):
        if "task_id" in data:
            data["job_id"] = data.pop("task_id")
        return super().to_internal_value(data)


class PendingPermissionSerializer(serializers.ModelSerializer):
    profile = serializers.StringRelatedField()
    grant_url = serializers.CharField(required=False, source="get_absolute_grant_url")

    class Meta:
        model = PendingPermission
        fields = ("grant_url", "profile", "permission_name", "is_expired")
        read_only = ("is_expired", "grant_url")


class MiniSimulationSerializer(serializers.ModelSerializer):
    """
    Serializer for data about simulations. This does not include
    the simulation results. This data is helpful for getting/
    setting the title and viewing the simulation's status.
    """

    owner = serializers.StringRelatedField(source="get_owner", required=False)
    authors = serializers.StringRelatedField(
        source="get_authors", many=True, required=False
    )
    title = serializers.CharField(required=False)
    model_pk = serializers.IntegerField(required=False)
    project = serializers.StringRelatedField(required=False)
    readme = serializers.JSONField(required=False)
    status = serializers.CharField(required=False)
    api_url = serializers.CharField(required=False, source="get_absolute_api_url")
    gui_url = serializers.CharField(required=False, source="get_absolute_url")

    # see to_representation
    # role = serializers.BooleanField(source="role")

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        if self.context.get("request"):
            user = self.context["request"].user
        else:
            user = None
        rep["role"] = obj.role(user)
        rep["authors"] = sorted(rep["authors"])
        return rep

    def validate_is_public(self, value):
        if getattr(self, "instance", None) is not None and value is False:
            self.instance.make_private_test()
        return value

    class Meta:
        model = Simulation
        fields = (
            "api_url",
            "authors",
            "creation_date",
            "gui_url",
            "is_public",
            "model_pk",
            "model_version",
            "notify_on_completion",
            "owner",
            "project",
            "readme",
            # "role",
            "status",
            "title",
        )
        read_only = (
            "api_url",
            "authors",
            "creation_date",
            "gui_url",
            "model_pk",
            "model_version",
            "owner",
            "project",
            # "role",
            "status",
        )


class ModelConfigSerializer(serializers.ModelSerializer):
    project = serializers.StringRelatedField()

    class Meta:
        model = ModelConfig
        fields = (
            "project",
            "model_version",
            "meta_parameters_values",
            "meta_parameters",
            "model_parameters",
            "creation_date",
        )

        read_only = (
            "project",
            "model_version",
            "meta_parameters_values",
            "meta_parameters",
            "model_parameters",
            "creation_date",
        )


class InputsSerializer(serializers.ModelSerializer):
    """
    Serializer for the Inputs object.
    """

    job_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=(("SUCCESS", "Success"), ("FAIL", "Fail")), required=False
    )
    client = serializers.ChoiceField(
        choices=(
            ("web-alpha", "Web-Alpha"),
            ("web-beta", "Web-Beta"),
            ("rest-api", "REST API"),
        ),
        required=False,
    )
    parent_model_pk = serializers.IntegerField(required=False)
    job_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=(("SUCCESS", "Success"), ("FAIL", "Fail")), required=False
    )
    api_url = serializers.CharField(source="get_absolute_api_url", required=False)
    gui_url = serializers.CharField(source="get_absolute_url", required=False)

    sim = MiniSimulationSerializer(required=False)

    # Not part of Inputs model but is needed for setting sim completion
    # notification status on sims created from /[owner]/[title]/api/v1/
    notify_on_completion = serializers.BooleanField(required=False)

    model_config = ModelConfigSerializer(allow_null=True, required=False)

    # see to_representation
    # role = serializers.BooleanField(source="role")

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        if self.context.get("request"):
            user = self.context["request"].user
        else:
            user = None
        rep["role"] = obj.role(user)
        rep["sim"]["authors"] = sorted(rep["sim"]["authors"])
        return rep

    def to_internal_value(self, data):
        if "outputs" in data:
            data.update(**data.pop("outputs"))
        if "task_id" in data:
            data["job_id"] = data.pop("task_id")
        return super().to_internal_value(data)

    class Meta:
        model = Inputs
        fields = (
            "adjustment",
            "api_url",
            "client",
            "custom_adjustment",
            "errors_warnings",
            "gui_url",
            "job_id",
            "meta_parameters",
            "model_config",
            "notify_on_completion",
            "parent_model_pk",
            "role",
            "sim",
            "status",
            "traceback",
        )


class SimAccessSerializer(serializers.Serializer):
    """Serialize user's permissions for a given simulation"""

    is_owner = serializers.BooleanField(required=False)
    role = serializers.ChoiceField(
        required=True, choices=("read", "write", "admin"), allow_null=True
    )
    username = serializers.CharField(required=True)
    msg = serializers.CharField(required=False, allow_blank=True)

    @staticmethod
    def ser(sim: Simulation, user=None):
        """
        Hacked on method for serializing data that doesn't quite fit the
        drf ModelSerialization approach.
        """
        return {
            "is_owner": sim.is_owner(user),
            "role": sim.role(user),
            "username": user.username,
        }

    class Meta:
        fields = ("is_owner", "role", "username", "msg")
        read_only = ("is_owner",)
        write_only = ("msg",)


class SimulationSerializer(serializers.ModelSerializer):
    """
    Serializer for entire Simulation object. This contains meta
    data about simulations as well as the outputs. The outputs
    can be either the full outputs or references to their
    location in the storage bucket.
    """

    api_url = serializers.CharField(source="get_absolute_api_url")
    gui_url = serializers.CharField(source="get_absolute_url")
    eta = serializers.FloatField(source="compute_eta")
    original_eta = serializers.FloatField(source="compute_original_eta")
    title = serializers.CharField(required=False)
    owner = serializers.StringRelatedField(source="get_owner", required=False)
    authors = serializers.StringRelatedField(source="get_authors", many=True)
    project = PublishSerializer()
    outputs_version = serializers.CharField()
    # see to_representation for definition of parent_sims:
    # parent_sims = MiniSimulationSerializer(many=True)
    # role = serializers.BooleanField(source="role")

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        if self.context.get("request"):
            user = self.context["request"].user
        else:
            user = None
        rep["parent_sims"] = MiniSimulationSerializer(
            obj.parent_sims(user=user), many=True
        ).data
        rep["role"] = obj.role(user)
        rep["authors"] = sorted(rep["authors"])
        if obj.has_admin_access(user):
            rep["pending_permissions"] = PendingPermissionSerializer(
                instance=obj.pending_permissions.all(), many=True
            ).data
            permission_objects = get_users_with_perms(obj)
            rep["access"] = []
            for user in permission_objects:
                rep["access"].append(SimAccessSerializer.ser(obj, user))
        elif (
            user is not None
            and user.is_authenticated
            and obj.pending_permissions.filter(profile__user=user).count() > 0
        ):
            rep["pending_permissions"] = PendingPermissionSerializer(
                instance=obj.pending_permissions.filter(profile__user=user), many=True
            ).data
        return rep

    class Meta:
        model = Simulation
        fields = (
            "api_url",
            "authors",
            "creation_date",
            "eta",
            "exp_comp_datetime",
            "gui_url",
            "is_public",
            "model_pk",
            "model_version",
            "notify_on_completion",
            "original_eta",
            "outputs",
            "owner",
            "outputs_version",
            # "parent_sims",
            "project",
            "readme",
            # "role",
            "run_time",
            "status",
            "title",
            "traceback",
        )
        read_only = (
            "api_url",
            "authors",
            "creation_date",
            "eta",
            "exp_comp_datetime",
            "gui_url",
            "model_pk",
            "model_version",
            "original_eta",
            "outputs",
            "owner",
            "outputs_version",
            # "parent_sims",
            "project",
            # "role",
            "run_time",
            "status",
            "traceback",
        )


class AuthorSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    msg = serializers.CharField(required=False, allow_blank=True)


class AddAuthorsSerializer(serializers.Serializer):
    authors = serializers.ListField(child=AuthorSerializer(), max_length=10)
