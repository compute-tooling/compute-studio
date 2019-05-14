import difflib
from typing import Tuple


def is_wildcard(x):
    if isinstance(x, str):
        return x in ("*", "*") or x.strip() in ("*", "*")
    else:
        return False


def is_reverse(x):
    if isinstance(x, str):
        return x in ("<", "<") or x.strip() in ("<", "<")
    else:
        return False


def json_int_key_encode(rename_dict):
    """
    Recursively rename integer value keys if they are casted to strings
    via JSON encoding

    returns: dict with new keys
    """
    if isinstance(rename_dict, dict):
        for k in list(rename_dict.keys()):
            if hasattr(k, "isdigit") and k.isdigit():
                new_label = int(k)
            else:
                new_label = k
            rename_dict[new_label] = json_int_key_encode(rename_dict.pop(k))
    return rename_dict


def dims_to_dict(param_name, meta_parameters):
    """
    Convert value object from string to dict:
    "param_name____dim0__dimval___dim1__dimval1..."
    -->
    {"value": val, dim0": dimval, ...}

    Return: base parameter name, value object dict

    Note: Dimensions that are also meta parameters are saved with the value "mp"
    because their value is saved and controlled by the corresponding meta
    parameter. Thus, this function replaces "mp" with the value in
    meta_parameters.
    """

    value_object = {}
    spl = param_name.split("____")
    basename = spl[0]
    # len(spl) > 1 implies dimension info is in the second component
    if len(spl) > 1:
        assert len(spl) == 2
        dims = spl[1]
        # Split dimension component by each dimension
        dimstrings = dims.split("___")
        # Further parse those down into the name of the dimension
        # and its value.
        for dim in dimstrings:
            dim_name, dim_value = dim.split("__")
            if dim_name in meta_parameters:
                dim_value = meta_parameters[dim_name]
            value_object[dim_name] = dim_value
    return basename, value_object


def dims_to_string(param_name, value_object, meta_parameters):
    """
    Convert value object from dict to string:
    {"value": val, dim0": dimval, ...}
    -->
    "param_name____dim0__dimval___dim1__dimval1..."

    Return: New name, suffix

    Note: Dimensions that are also meta parameters are saved with the value "mp"
    because their value is saved and controlled by the corresponding meta
    parameter. Thus, dims_to_dict replaces "mp" with the specified meta
    parameter value.

    The dimension names are added to the string in alphabetic order to
    better ensure replicable field name creation.
    """
    dims = {}
    for dim_name, dim_value in value_object.items():
        if dim_name == "value":
            continue
        if dim_name in meta_parameters:
            dim_value = "mp"
        dims[dim_name] = dim_value

    if dims:
        suffix = "___".join(
            [f"{dim_name}__{dim_value}" for dim_name, dim_value in sorted(dims.items())]
        )
    else:
        suffix = ""
    if suffix:
        return param_name + "____" + suffix, suffix
    else:
        return param_name, suffix
