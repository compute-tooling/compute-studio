from webapp.apps.core.meta_parameters import (meta_parameters, MetaParameters,
                                              MetaParameter)


def meta_parameter_factory(mp):
    # optionally edit parameters attribute on mp
    return mp


{project}_meta_parameters = meta_parameter_factory(meta_parameters)