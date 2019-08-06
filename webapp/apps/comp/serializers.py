from rest_framework import serializers

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
    api_url = serializers.CharField(source="get_absolute_api_url", required=False)

    job_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=(("SUCCESS", "Success"), ("FAIL", "Fail")), required=False
    )
    sim = MiniSimulationSerializer(source="outputs", required=False)
    api_url = serializers.CharField(source="get_absolute_api_url", required=False)

    class Meta:
        model = Inputs
        fields = (
            "pk",
            "meta_parameters",
            "adjustment",
            "inputs_file",
            "errors_warnings",
            "job_id",
            "status",
            "traceback",
            "sim",
            "api_url",
            "client",
        )


class SimulationSerializer(serializers.ModelSerializer):
    inputs = InputsSerializer(required=False)
    api_url = serializers.CharField(source="get_absolute_api_url")
    gui_url = serializers.CharField(source="get_absolute_url")
    eta = serializers.FloatField(source="compute_eta")

    class Meta:
        model = Simulation
        fields = (
            "inputs",
            "outputs",
            "traceback",
            "creation_date",
            "api_url",
            "gui_url",
            "eta",
            "model_pk",
        )
