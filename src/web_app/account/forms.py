from django import forms


class LoginForm(forms.Form):
    user_name = forms.CharField(
        min_length=1,
        max_length=256,
        label='User name',
        widget=forms.TextInput(
            attrs={'class': 'form-control me-2', 'type': 'user_name', 'placeholder': 'User', 'aria-label': 'Login'}
        )
    )
    password = forms.CharField(
        min_length=1,
        max_length=256,
        label='Password',
        widget=forms.TextInput(
            attrs={'class': 'form-control me-2', 'type': 'password', 'placeholder': 'Password', 'aria-label': 'Login'}
        )
    )
