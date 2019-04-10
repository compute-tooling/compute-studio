from rest_framework import serializers


class OutputsSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=(("SUCCESS", "Success"), ("FAIL", "Fail")))
    result = serializers.JSONField(required=False)
    traceback = serializers.CharField(required=False)
    meta = serializers.JSONField()
