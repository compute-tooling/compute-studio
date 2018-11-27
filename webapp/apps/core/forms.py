from collections import namedtuple

from django import forms

from .param_displayer import ParamDisplayer


MetaParam = namedtuple("MetaParam", ["name", "default", "FieldCls"])

class Form(forms.Form):

    meta_parameters = []

    def __init__(self, *args, **kwargs):
        fields = args[0] if args else {}
        args = ({}, )
        clean_meta_parameters = {}
        for param in self.meta_parameters:
            try:
                cleaned = param.FieldCls(fields.get("start_year"))
            except forms.ValidationError:
                # fall back on default. deal with bad data in full validation.
                cleaned = param.FieldCls(fields.default)
            clean_meta_parameters[param.name] = cleaned
        pd = ParamDisplayer(**clean_meta_parameters)
        default_params = pd.get_defaults()
        update_fields = {}
        for param in list(default_params.values()):
            update_fields.update(param.fields)
        update_fields.updaet(clean_meta_parameters)
        super().__init__(data=fields, **kwargs)
        # funky things happen when dict is not copied
        self.fields.update(update_fields.copy())

    def save(self, ModelCls, commit=True):
        meta_parameters = [mp.name for mp in self.meta_parameters]
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


