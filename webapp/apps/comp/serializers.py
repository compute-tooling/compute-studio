from rest_framework import serializers


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
    meta = serializers.JSONField()
