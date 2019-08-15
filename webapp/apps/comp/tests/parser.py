import uuid

from webapp.apps.comp import parser


class LocalAPIParser(parser.APIParser):
    def post(self, errors_warnings, adjustment):
        return str(uuid.uuid4()), 1
