from django.urls import path

from . import views

app_name = "main"
urlpatterns = [
    path("home/",views.HomeView.as_view(),name = "home")
]

