from django.views.generic.base import View
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied


class AbstractRouterView(View):
    projects = None
    payment_view = None
    login_view = None

    def handle(self, request, is_get, *args, **kwargs):
        print("router handle", args, kwargs)
        project = get_object_or_404(
            self.projects,
            owner__user__username=kwargs["username"],
            title=kwargs["title"],
        )
        if project.status in ["updating", "live"]:
            if project.sponsor is None:
                return self.payment_view.as_view()(request, *args, **kwargs)
            else:
                return self.login_view.as_view()(request, *args, **kwargs)
        else:
            if is_get:
                return self.unauthorized_get(request, project)
            else:
                raise PermissionDenied()

    def unauthorized_get(self, request, project):
        return PermissionDenied()

    def get(self, request, *args, **kwargs):
        return self.handle(request, True, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.handle(request, False, *args, **kwargs)


# class RouterView(InputsMixin, AbstractRouterView):
#     projects = Project.objects.all()
#     placeholder_template = "comp/model_placeholder.html"
#     payment_view = RequiresPmtInputsView
#     login_view = RequiresLoginInputsView

#     def unauthorized_get(self, request, project):
#         context = self.project_context(request, project)
#         return render(request, self.placeholder_template, context)

#     def get(self, request, *args, **kwargs):
#         return self.handle(request, True, *args, **kwargs)

#     def post(self, request, *args, **kwargs):
#         return self.handle(request, False, *args, **kwargs)
