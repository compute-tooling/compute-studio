from rest_framework import serializers

from webapp.apps.publish.serializers import PublishSerializer

from .models import Inputs, Simulation


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
    # has_write_access = serializers.BooleanField(source="has_write_access")

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        if self.context.get("request"):
            user = self.context["request"].user
        else:
            user = None
        rep["has_write_access"] = obj.has_write_access(user)
        return rep

    class Meta:
        model = Simulation
        fields = (
            "api_url",
            "authors",
            "creation_date",
            "gui_url",
            # "has_write_access",
            "is_public",
            "model_pk",
            "model_version",
            "notify_on_completion",
            "owner",
            "project",
            "readme",
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
            "status",
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

    # see to_representation
    # has_write_access = serializers.BooleanField(source="has_write_access")

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        if self.context.get("request"):
            user = self.context["request"].user
        else:
            user = None
        rep["has_write_access"] = obj.has_write_access(user)
        return rep

    class Meta:
        model = Inputs
        fields = (
            "adjustment",
            "api_url",
            "client",
            "custom_adjustment",
            "errors_warnings",
            "gui_url",
            # "has_write_access",
            "job_id",
            "meta_parameters",
            "notify_on_completion",
            "parent_model_pk",
            "sim",
            "status",
            "traceback",
        )


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
    # has_write_access = serializers.BooleanField(source="has_write_access")

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        if self.context.get("request"):
            user = self.context["request"].user
        else:
            user = None
        rep["parent_sims"] = MiniSimulationSerializer(
            obj.parent_sims(user=user), many=True
        ).data
        rep["has_write_access"] = obj.has_write_access(user)
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
            # "has_write_access",
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
            # "has_write_access",
            "model_pk",
            "model_version",
            "original_eta",
            "outputs",
            "owner",
            "outputs_version",
            # "parent_sims",
            "project",
            "run_time",
            "status",
            "traceback",
        )


class CollabSerializer(serializers.Serializer):
    authors = serializers.ListField(child=serializers.CharField(), max_length=10)
