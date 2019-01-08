from webapp.apps.core.templatetags.utility import is_truthy


def test_is_truthy():
    """
    Tests is_truthy template tag. An attempt was made to use the django
    BoundField class which is what is passed to is_truthy, but this proved
    to be more trouble than it was worth.
    """
    class Mock:
        def __init__(self, value=None, placeholder=None):
            self._value = value
            self.attrs = {"placeholder": placeholder}

        def value(self):
            return self._value

    def mock_checkbox(value, placeholder):
        checkbox = Mock(value=value)
        checkbox.field = Mock()
        checkbox.field.widget = Mock(placeholder=placeholder)
        return checkbox

    # get fresh page or get edit page and parameter has not
    # been edited
    assert is_truthy(mock_checkbox(None, "True"))
    assert not is_truthy(mock_checkbox(None, "False"))

    # get page after reset
    assert is_truthy(mock_checkbox("", "True"))
    assert not is_truthy(mock_checkbox("", "False"))

    # get page after edit where parameter has been edited
    assert is_truthy(mock_checkbox("True", "True"))
    assert is_truthy(mock_checkbox("True", "False"))
    assert not is_truthy(mock_checkbox("False", "True"))
    assert not is_truthy(mock_checkbox("False", "False"))