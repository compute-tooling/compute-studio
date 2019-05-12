from django import forms

from .models import Inputs


class InputsForm(forms.Form):
    def __init__(self, project, displayer, *args, **kwargs):
        self.project = project
        self.meta_parameters = displayer.parsed_meta_parameters()

        fields = args[0] if args else {}
        if fields:
            # POST inputs form
            clean_meta_parameters = self.meta_parameters.validate(fields)
        elif kwargs.get("initial", None) is not None:
            # GET edit inputs form
            clean_meta_parameters = self.meta_parameters.validate(kwargs.get("initial"))
        else:
            # GET fresh inputs form
            clean_meta_parameters = self.meta_parameters.validate({})
        fields.update(clean_meta_parameters)
        displayer.meta_parameters = clean_meta_parameters
        default_params = displayer.defaults(flat=True)
        update_fields = {}
        for param in list(default_params.values()):
            update_fields.update(param.fields)
        update_fields.update(
            {
                mp_name: mp.field
                for mp_name, mp in self.meta_parameters.parameters.items()
            }
        )
        super().__init__(data=fields, **kwargs)
        # funky things happen when dict is not copied
        self.fields.update(update_fields.copy())

    def save(self, commit=True):
        meta_parameters = list(self.meta_parameters.parameters.keys())
        clean_meta_parameters = {
            name: self.cleaned_data[name] for name in meta_parameters
        }
        # use cleaned_data keys to filter out un-needed params like request
        # tokens
        raw_gui_inputs = {}
        gui_inputs = {}
        clean_meta_parameters = {}
        for k in self.cleaned_data:
            if k not in meta_parameters:
                raw_gui_inputs[k] = self.data.get(k, None)
                gui_inputs[k] = self.cleaned_data[k]
            else:
                clean_meta_parameters[k] = self.cleaned_data[k]

        model = Inputs(
            meta_parameters=clean_meta_parameters,
            raw_gui_inputs=raw_gui_inputs,
            gui_inputs=gui_inputs,
            project=self.project,
        )
        if commit:
            model.save()
        return model
