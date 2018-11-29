from django import forms

from .param_displayer import ParamDisplayer


class InputsForm(forms.Form):

    ParamDisplayerCls = ParamDisplayer
    meta_parameters = None

    def __init__(self, *args, **kwargs):
        fields = args[0] if args else {}
        args = ({}, )
        clean_meta_parameters = self.meta_parameters.validate(fields)
        # guarantee that we have meta_parameters
        # this is important for empty or partially empty GET requests
        fields.update(clean_meta_parameters)
        pd = self.ParamDisplayerCls(**clean_meta_parameters)
        default_params = pd.get_defaults()
        update_fields = {}
        for param in list(default_params.values()):
            update_fields.update(param.fields)
        update_fields.update({
            mp.name: mp.field for mp in self.meta_parameters.parameters
        })
        super().__init__(data=fields, **kwargs)
        # funky things happen when dict is not copied
        self.fields.update(update_fields.copy())

    def save(self, ModelCls, commit=True):
        meta_parameters = [mp.name for mp in self.meta_parameters.parameters]
        clean_meta_parameters = {name: self.cleaned_data[name]
                                 for name in meta_parameters}
        # use cleaned_data keys to filter out un-needed params like request
        # tokens
        raw_gui_inputs = {}
        gui_inputs = {}
        for k in self.cleaned_data:
            if k not in meta_parameters:
                raw_gui_inputs[k] = self.data.get(k, None)
                gui_inputs[k] = self.cleaned_data[k]
        model = ModelCls(
            raw_gui_inputs=raw_gui_inputs,
            gui_inputs=gui_inputs)
        # try to set metaparameters as model attributes. ignore errors.
        for param in meta_parameters:
            try:
                setattr(model, param, self.cleaned_data[param])
            except AttributeError:
                print("failed to set attr: ", param, value)
        if commit:
            model.save()
        return model


