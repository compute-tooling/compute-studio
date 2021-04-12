import math


def set_resource_requirements(project_data):
    mem = float(project_data.pop("memory"))
    cpu = float(project_data.pop("cpu"))
    if cpu and mem:
        project_data["resources"] = {
            "requests": {"memory": f"{mem}G", "cpu": cpu},
            "limits": {"memory": f"{math.ceil(mem * 1.2)}G", "cpu": cpu,},
        }
