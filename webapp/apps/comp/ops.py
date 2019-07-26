def parse_ops(self, parsed_input, errors_warnings, extend, extend_val):
    """
    Parses and applies the * and < operators on *specific projects*.
    This will be superseded by a better GUI.
    """
    number_reverse_operators = 1

    revision = defaultdict(list)
    for param in parsed_input:
        if param.endswith("checkbox"):
            revision[param] = parsed_input[param]
            continue
        for val_obj in parsed_input[param]:
            i = 0
            if not isinstance(val_obj["value"], list):
                revision[param].append(val_obj)
                continue
            while i < len(val_obj["value"]):
                if is_wildcard(val_obj["value"][i]):
                    # may need to do something here
                    pass
                elif is_reverse(val_obj["value"][i]):
                    # only the first character can be a reverse char
                    # and there must be a following character
                    # TODO: Handle error
                    if i != 0:
                        errors_warnings["GUI"]["errors"][param] = [
                            "Reverse operator can only be used in the first position."
                        ]
                        return {}
                    if len(val_obj["value"]) == 1:
                        errors_warnings["GUI"]["errors"][param] = [
                            "Reverse operator must have an additional value, e.g. '<,2'"
                        ]
                        return {}
                    # set value for parameter in start_year - 1

                    opped = {extend: extend_val - 1, "value": val_obj["value"][i + 1]}

                    revision[param].append(dict(val_obj, **opped))

                    # realign year and parameter indices
                    for _ in (0, number_reverse_operators + 1):
                        val_obj["value"].pop(0)
                    continue
                else:
                    opped = {extend: extend_val + i, "value": val_obj["value"][i]}
                    revision[param].append(dict(val_obj, **opped))

                i += 1
    return revision
