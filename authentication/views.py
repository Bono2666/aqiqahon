from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from .forms import LoginForm


def login_view(request):
    form = LoginForm(request.POST or None)

    msg = None

    if request.method == "POST":

        if form.is_valid():
            user_id = form.cleaned_data.get("user_id")
            password = form.cleaned_data.get("password")
            user = authenticate(user_id=user_id, password=password)
            if user is not None:
                login(request, user)
                return redirect("/")
            else:
                msg = 'Invalid User ID/Password'
        else:
            msg = 'Error validating the form.'

    return render(request, "accounts/login.html", {"form": form, "msg": msg})


def forbidden_view(request):
    return render(request, "home/forbidden.html")
