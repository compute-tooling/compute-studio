from django.views.generic.base import TemplateView


class PublishView(TemplateView):
    template_name = "docs/publish.html"


class FunctionsView(TemplateView):
    template_name = "docs/functions.html"


class EnvironmentView(TemplateView):
    template_name = "docs/environment.html"


class IOSchemaView(TemplateView):
    template_name = "docs/ioschema.html"
