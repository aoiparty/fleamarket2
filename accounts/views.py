from django.shortcuts import render
from django.contrib import messages
from django.views.generic import DeleteView, FormView, TemplateView
from .forms import CustomSignupForm, EmailChangeForm
from allauth.account.views import PasswordChangeView, SignupView #PasswordChangeViewを追加
from django.urls import reverse_lazy

# ...

# Create your views here.
from . import forms
from allauth.account.views import SignupView
from .forms import CustomSignupForm
from django.views.generic import ListView,DetailView,FormView,TemplateView,DeleteView


class CustomSignupView(SignupView):
    template_name = "account/signup.html"
    form_class = CustomSignupForm


class EmailChangeView(FormView):
    form_class = EmailChangeForm
    success_url = reverse_lazy("account_email_change_done")
    template_name = "account/email_change.html"

    #現在のメアドを取得
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_email"] = self.request.user.email
        return context

    def form_valid(self, form):
        user = self.request.user
        new_email = form.cleaned_data["email"]
        user.email = new_email
        user.save()
        return super().form_valid(form)

class EmailChangeDoneView(TemplateView):
    template_name = "account/email_change_done.html"

class CustomPasswordChangeView(PasswordChangeView):
    success_url = reverse_lazy("main:account")
