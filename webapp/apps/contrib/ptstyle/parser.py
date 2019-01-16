from collections import defaultdict

from webapp.apps.core.parser import Parser


class ParmToolsParser(Parser):

    def unflatten(self, parsed_input):
        params = defaultdict(list)
        for param, value in parsed_input.items():
            # Split into name and dimension components.
            spl = param.split("___")
            # len(spl) > 1 implies dimension info is in the second component
            if len(spl) > 1:
                assert len(spl) == 2
                # Split dimension component by each dimension
                dimstrings = spl[1].split("__")
                value_item = {}
                # Further parse those down into the name of the dimension
                # and its value.
                for dim in dimstrings:
                    name, value = dim.split("_")
                    value_item[name] = item
                value_item["value"] = value
                params[spl].append(dict(value_item, **self.valid_meta_params))
            else:
                # No dimension information is encoded.
                assert len(spl) == 1
                params[param].append(dict(value=value, **self.valid_meta_params))
        return params