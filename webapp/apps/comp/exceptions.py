import json


class COMPError(Exception):
    pass


class AppError(COMPError):
    def __init__(self, parameters, traceback):
        self.parameters = json.dumps(parameters, indent=4)
        self.traceback = traceback
        super().__init__(traceback)


class ValidationError(COMPError):
    pass
