from django.urls import path

from . import views

urlpatterns = [
    path(
        "signup/",
        views.CustomSignupView.as_view(),
        name="signup",
    ),
]