from rest_framework import serializers

from .models import Inputs, Simulation


class ResultSerializer(serializers.Serializer):
    outputs = serializers.JSONField()
    # only used with v0!
    aggr_outputs = serializers.JSONField(required=False)
    version = serializers.CharField()


class OutputsSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=(("SUCCESS", "Success"), ("FAIL", "Fail")))
    traceback = serializers.CharField(required=False)
    result = ResultSerializer(required=False)
    model_version = serializers.CharField(required=False)
    meta = serializers.JSONField()


class MiniSimulationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Simulation
        fields = ("model_pk",)


class InputsSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=(("SUCCESS", "Success"), ("FAIL", "Fail")), required=False
    )
    simulation = MiniSimulationSerializer(required=False)

    class Meta:
        model = Inputs
        fields = (
            "meta_parameters",
            "adjustment",
            "inputs_file",
            "errors_warnings",
            "job_id",
            "status",
            "traceback",
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
