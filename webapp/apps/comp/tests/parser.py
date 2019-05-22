from webapp.apps.comp import parser


class LocalParser(parser.Parser):
    def post(self, errors_warnings, adjustment):
        return errors_warnings, adjustment, None


class LocalAPIParser(parser.APIParser):
    def post(self, errors_warnings, adjustment):
        return errors_warnings, adjustment, None
