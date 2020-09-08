from django.urls import path

from .views import HomeView, AboutView, PrivacyView, TermsView, DMCAView, RobotsText


urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("about/", AboutView.as_view(), name="about"),
    path("privacy/", PrivacyView.as_view(), name="privacy"),
    path("terms/", TermsView.as_view(), name="terms"),
    path("dmca/", DMCAView.as_view(), name="dmca"),
    path("robots.txt", RobotsText.as_view(), name="robots"),
]
