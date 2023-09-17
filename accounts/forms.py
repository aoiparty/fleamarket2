from xml.etree.ElementTree import fromstring
from allauth.account.forms import SetPasswordForm,SignupForm
from django import forms
from django.contrib.auth import get_user_model
      
class CustomSignupForm(SignupForm):
    """会員登録用フォーム"""
    #メアド、パスワードなどはインポートしてあるので、利用規約のみかく
    checkbox = forms.BooleanField(
        label="利用規約に同意する",
        error_messages={"required": "利用規約に同意する必要があります"},
        required=True,
    )

    fields = ["username", "email", "password1", "password2", "checkbox"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["class"] = "form"
        self.fields["email"].widget.attrs["class"] = "form"
        self.fields["password1"].widget.attrs["class"] = "form"
        self.fields["password2"].widget.attrs["class"] = "form"

    def clean_checkbox(self):
        checkbox = self.cleaned_data.get("checkbox")
        if not checkbox:
            raise forms.ValidationError(
                self.fields["checkbox"].error_messages["required"]
            )
        return checkbox
       #clean_フィールド名...新しいバリデーション。バリデーションで通らない時raise ValidaitonError()
     #self.fields["checkbox"].error_messages["required"]...fieldのCheckboxの中にあるerrormassagesのrequired
     #→"利用規約に同意する必要があります"が表示される
