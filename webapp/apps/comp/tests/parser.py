from webapp.apps.comp import parser


class LocalParser(parser.Parser):
    def post(self, errors_warnings, model_parameters):
        return errors_warnings, model_parameters, None


class LocalAPIParser(parser.APIParser):
    def post(self, errors_warnings, model_parameters):
        return errors_warnings, model_parameters, None
