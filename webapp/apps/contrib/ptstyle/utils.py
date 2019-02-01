def to_dict(param_name):
    """
    Convert value object from string to dict:
       "param_name___dim0_dimval__dim1_dimval1..."
       -->
       {"value": val, dim0": dimval, ...}

    Return: base parameter name, value object dict
    """

    value_object = {}
    spl = param_name.split("____")
    basename = spl[0]
    # len(spl) > 1 implies dimension info is in the second component
    if len(spl) > 1:
        assert len(spl) == 2
        base_name, dims = spl
        # Split dimension component by each dimension
        dimstrings = dims.split("___")
        # Further parse those down into the name of the dimension
        # and its value.
        for dim in dimstrings:
            dim_name, dim_value = dim.split("__")
            value_object[dim_name] = dim_value
    return basename, value_object


def to_string(param_name, value_object):
    """
    Convert value object from dict to string:
       {"value": val, dim0": dimval, ...}
       -->
       "param_name____dim0__dimval___dim1__dimval1..."

    Return: New name, suffix
    """
    dims = {k: v for k, v in value_object.items() if k != "value"}
    if dims:
        suffix = "___".join([
            f"{dim_name}__{dim_value}" for dim_name, dim_value in dims.items()
        ])
    else:
        suffix = ""
    if suffix:
        return param_name + "____" + suffix, suffix
    else:
        return param_name, suffix
