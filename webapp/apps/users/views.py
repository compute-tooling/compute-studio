from django.urls import reverse_lazy
from django.views import generic, View
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from .forms import UserCreationForm


class SignUp(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UserProfile(View):
    template_name = 'registration/profile_base.html',

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name,
                      context={'username': request.user.username})