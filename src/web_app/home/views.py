from django.shortcuts import render
from me_project.web_utils import init_session

from .forms import LoginForm


# Create your views here.

def home(request):
    # Load configs
    init_session(request.session)
    #
    context = {
        'login_form': LoginForm()
    }

    return render(request, 'home.html', context)
