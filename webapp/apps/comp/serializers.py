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
    model_version = serializers.CharField()
    meta = serializers.JSONField()


class InputsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inputs
        fields = (
            "meta_parameters",
            "model_parameters",
            "inputs_file",
            "errors_warnings",
        )


class SimulationSerializer(serializers.ModelSerializer):
    inputs = InputsSerializer(required=False)
    # outputs = serializers.ModelField(required=False)
    # traceback = serializers.ModelField(required=False)
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
