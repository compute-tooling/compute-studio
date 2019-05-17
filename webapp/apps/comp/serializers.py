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
    outputs = serializers.JSONField(required=False, read_only=True)

    class Meta:
        model = Simulation
        fields = ("inputs", "outputs")
