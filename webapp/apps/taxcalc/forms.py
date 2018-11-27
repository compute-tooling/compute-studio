from django import forms

from .constants import START_YEAR, DEFAULT_SOURCE

from .param_displayer import ParamDisplayer


class TaxcalcForm(forms.Form):

    meta_parameters = ["start_year", "data_source"]

    def __init__(self, *args, **kwargs):
        fields = args[0] if args else {}
        args = ({}, )
        self._start_year = int(fields.get("start_year", START_YEAR))
        self._data_source = fields.get("data_source", DEFAULT_SOURCE)
        pd = ParamDisplayer(start_year=int(START_YEAR),
                            data_source=DEFAULT_SOURCE)
        default_params = pd.get_defaults()

        update_fields = {}
        for param in list(default_params.values()):
            update_fields.update(param.fields)
        update_fields["start_year"] = forms.IntegerField(min_value=2013, max_value=2018)
        update_fields["data_source"] = forms.CharField()
        super().__init__(data=fields, **kwargs)
        self.fields.update(update_fields.copy())

    def save(self, ModelCls, commit=True):
        meta_parameters = ["start_year", "data_source"]
        clean_meta_parameters = {mp: self.cleaned_data[mp]
                                 for mp in meta_parameters}
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
        for param in self.meta_parameters:
            try:
                setattr(model, param, self.cleaned_data[param])
            except AttributeError:
                print("failed to set attr: ", param, value)
        if commit:
            model.save()
        return model
