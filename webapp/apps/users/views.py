from django.urls import reverse_lazy
from django.views import generic

from .forms import UserCreationForm


class SignUp(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)