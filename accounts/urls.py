from django.urls import path

from . import views

from django.contrib.staticfiles.urls import static

from django.conf import settings

from django.urls import path, include

urlpatterns = [
    path(
        "signup/",
        views.CustomSignupView.as_view(),
        name="signup",
        
    ),
    path("email/change/", views.EmailChangeView.as_view(), name="account_email_change"),
    path(
        "email/change/done/",
        views.EmailChangeDoneView.as_view(),
        name="account_email_change_done",
    ),
    path(
        "password/change/",
        views.CustomPasswordChangeView.as_view(),
        name="change_password",
    ),
]

if settings.DEBUG:
    # 追加
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]