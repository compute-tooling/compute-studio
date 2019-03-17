from webapp.apps.publish.utils import title_fixup


def test_title_fixup():
    assert title_fixup("hello&&*******wor  ld") == "hello-wor-ld"
