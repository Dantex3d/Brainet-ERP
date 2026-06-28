from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

UserModel = get_user_model()


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "placeholder": "name@school.com",
                "class": "form-control",
            }
        ),
    )

    error_messages = {
        "invalid_login": _("Wrong credentials. Please check your email and password."),
        "inactive": _("This account is inactive."),
        "user_not_found": _("User does not exist."),
    }

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if email and password:
            try:
                user = UserModel._default_manager.get(email__iexact=email)
            except UserModel.DoesNotExist:
                raise forms.ValidationError(
                    self.error_messages["user_not_found"],
                    code="user_not_found",
                )

            if not user.check_password(password):
                raise forms.ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                )

            if not user.is_active:
                raise forms.ValidationError(
                    self.error_messages["inactive"],
                    code="inactive",
                )

            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                )

        return self.cleaned_data
