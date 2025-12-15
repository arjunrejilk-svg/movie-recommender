from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
import re


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email']  # We also add Email just in case

    def clean_password1(self):
        password = self.cleaned_data.get('password1')

        # Rule 1: Must contain at least 1 Uppercase Letter (A-Z)
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError(
                "Password must contain at least 1 Uppercase letter (A-Z).")

        # Rule 2: Must contain at least 1 Number (0-9)
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError(
                "Password must contain at least 1 Number (0-9).")

        # Rule 3: Must contain at least 1 Special Character (@, $, !, etc.)
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise forms.ValidationError(
                "Password must contain at least 1 Special Character (!@#$%).")

        return password
