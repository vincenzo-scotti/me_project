from django.shortcuts import render, redirect, HttpResponse
from me_project.web_utils import init_session
from django.contrib.auth import authenticate, login, logout

from .forms import LoginForm
from me_project.web_utils.utils import *


# Create your views here.

# References https://docs.djangoproject.com/en/5.0/topics/auth/default/


def login_view(request):
    # Manage authentication
    login_form = LoginForm(request.POST)
    if login_form.is_valid():
        user_name = login_form.cleaned_data[UNAME]
        password = login_form.cleaned_data[PWD]
    else:
        user_name = password = None
    user = authenticate(request, username=user_name, password=password)
    #
    if user is not None:
        login(request, user)
        # Redirect to a success page.
        return redirect(request.GET.get('next', '/'))
    else:
        # Return an 'invalid login' error message.
        return HttpResponse('AuthenticationError', status=401)


def logout_view(request):
    # Log user out
    logout(request)
    # Reset session data
    init_session(request.session)
    # Redirect to source page
    return redirect('/')
