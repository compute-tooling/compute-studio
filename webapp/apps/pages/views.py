from django.shortcuts import render
from django.views import View
# Create your views here.

class BaseView(View):
    template_name = 'pages/home.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)


class Publish(View):
    template_name = 'pages/publish.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)
