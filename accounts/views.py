from django.shortcuts import render

# Create your views here.
from . import forms
from allauth.account.views import SignupView
from .forms import CustomSignupForm

class CustomSignupView(SignupView):
    templates_name = "account/signup.html"
    form_class = CustomSignupForm
