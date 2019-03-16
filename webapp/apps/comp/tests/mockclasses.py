class MockModel:
    """Mock django Model class with save method"""

    def __init__(self, **kwargs):
        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

    @property
    def deserialized_inputs(self):
        return self.model_parameters

    def save(self, commit=True):
        return self
