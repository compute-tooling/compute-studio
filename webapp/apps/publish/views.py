from django.shortcuts import render
from django.views import View


class PublishView(View):
    template_name = "publish/publish.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        print(request.POST.dict())
        return render(request, self.template_name)
