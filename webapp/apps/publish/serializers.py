from rest_framework import serializers

from webapp.apps.users.models import Project


class PublishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            "title",
            "oneliner",
            "description",
            "inputs_style",
            "meta_parameters",
            "package_defaults",
            "parse_user_adjustments",
            "run_simulation",
            "server_size",
            "exp_task_time",
            "installation",
            "server_cost",
        )
