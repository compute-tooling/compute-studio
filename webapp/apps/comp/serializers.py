from rest_framework import serializers

from webapp.apps.publish.serializers import PublishSerializer

from .models import Inputs, Simulation


class OutputsSerializer(serializers.Serializer):
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
    api_url = serializers.CharField(source="get_absolute_api_url")
    gui_url = serializers.CharField(source="get_absolute_url")
    creation_date = serializers.DateTimeField(format="%Y-%m-%d")

    class Meta:
        model = Simulation
        fields = ("model_pk", "api_url", "gui_url", "creation_date", "model_version")


class InputsSerializer(serializers.ModelSerializer):
    hashid = serializers.CharField(source="get_hashid", required=False)
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
    sim = MiniSimulationSerializer(source="outputs", required=False)
    parent_model_pk = serializers.IntegerField(required=False)
    parent_inputs_hashid = serializers.CharField(required=False)
    job_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=(("SUCCESS", "Success"), ("FAIL", "Fail")), required=False
    )
    api_url = serializers.CharField(source="get_absolute_api_url", required=False)
    edit_inputs_url = serializers.CharField(source="get_edit_url", required=False)

    class Meta:
        model = Inputs
        fields = (
            "hashid",
            "meta_parameters",
            "adjustment",
            "custom_adjustment",
            "errors_warnings",
            "job_id",
            "status",
            "traceback",
            "sim",
            "parent_model_pk",
            "parent_inputs_hashid",
            "api_url",
            "edit_inputs_url",
            "client",
        )


class SimDescriptionSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(required=False)
    title = serializers.CharField(required=False)
    readme = serializers.CharField(required=False)
    api_url = serializers.CharField(required=False, source="get_absolute_api_url")
    gui_url = serializers.CharField(required=False, source="get_absolute_url")

    class Meta:
        model = Simulation
        fields = ("title", "readme", "owner", "last_modified", "api_url", "gui_url")


class SimulationSerializer(serializers.ModelSerializer):
    api_url = serializers.CharField(source="get_absolute_api_url")
    gui_url = serializers.CharField(source="get_absolute_url")
    eta = serializers.FloatField(source="compute_eta")
    original_eta = serializers.FloatField(source="compute_original_eta")
    title = serializers.CharField(required=False)
    readme = serializers.CharField(required=False)
    owner = serializers.StringRelatedField(required=False)
    project = PublishSerializer()
    parent_sims = SimDescriptionSerializer(many=True)

    class Meta:
        model = Simulation
        fields = (
            "title",
            "readme",
            "last_modified",
            "parent_sims",
            "outputs",
            "traceback",
            "creation_date",
            "api_url",
            "gui_url",
            "eta",
            "original_eta",
            "model_pk",
            "status",
            "model_version",
            "run_time",
            "exp_comp_datetime",
            "traceback",
            "owner",
            "project",
        )
