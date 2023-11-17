from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from es_mvp.views import initial_store_settings

### Registration view functions

def register(request):
    """Register a new user."""
    if request.method != 'POST':
        # Display blank registration form.
        form = UserCreationForm()
    else:
        # Process completed form.
        form = UserCreationForm(data=request.POST)
        if form.is_valid():
            new_user = form.save()
            # Keeps the new user inactive until the admin handling
            new_user.is_active = False
            new_user.save()
            # Generates a initial store settings for the new user.
            initial_store_settings(new_user.id)
            ## Log the user in and then redirect to home page.
            ## login(request, new_user)
            return redirect('es_mvp:home')
    # Display a blank or invalid form.
    context = {'form': form}
    return render(request, 'registration/register.html', context)


