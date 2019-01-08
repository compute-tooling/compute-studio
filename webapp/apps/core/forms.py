from django import forms

from .displayer import Displayer


class InputsForm(forms.Form):

    model = None
    displayer_class = Displayer
    meta_parameters = None

    def __init__(self, *args, **kwargs):
        fields = args[0] if args else {}
        if fields:
            # POST inputs form
            clean_meta_parameters = self.meta_parameters.validate(fields)
        elif kwargs.get("initial", None) is not None:
            # GET edit inputs form
            clean_meta_parameters = self.meta_parameters.validate(
                kwargs.get("initial"))
        else:
            # GET fresh inputs form
            clean_meta_parameters = self.meta_parameters.validate({})
        fields.update(clean_meta_parameters)
        pd = self.displayer_class(**clean_meta_parameters)
        default_params = pd.defaults(flat=True)
        update_fields = {}
        for param in list(default_params.values()):
            update_fields.update(param.fields)
        update_fields.update({
            mp.name: mp.field for mp in self.meta_parameters.parameters
        })
        super().__init__(data=fields, **kwargs)
        # funky things happen when dict is not copied
        self.fields.update(update_fields.copy())

    def save(self, commit=True):
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
        model = self.model(
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
