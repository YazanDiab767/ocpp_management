from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import admin_required
from accounts.forms import PhoneLoginForm, UserCreateForm, UserUpdateForm, UserPermissionsForm

User = get_user_model()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard-home')
    if request.method == 'POST':
        form = PhoneLoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
    else:
        form = PhoneLoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@admin_required
def user_list(request):
    users = User.objects.all().order_by('-date_joined')
    from accounts.models import PAGE_REGISTRY
    return render(request, 'accounts/user_list.html', {
        'users': users,
        'total_pages': len(PAGE_REGISTRY),
    })


@admin_required
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'User created successfully.')
            return redirect('user-list')
    else:
        form = UserCreateForm()
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Create User',
    })


@admin_required
def user_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    allowed_pages = user.get_allowed_pages()
    from accounts.models import PAGE_REGISTRY
    permissions_display = []
    for key, (name, section) in PAGE_REGISTRY.items():
        permissions_display.append({
            'name': name,
            'section': section,
            'allowed': key in allowed_pages,
        })
    return render(request, 'accounts/user_detail.html', {
        'user_obj': user,
        'permissions_display': permissions_display,
    })


@admin_required
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('user-detail', pk=user.pk)
    else:
        form = UserUpdateForm(instance=user)
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Edit User',
        'user_obj': user,
    })


@admin_required
def user_permissions(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserPermissionsForm(request.POST, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Permissions updated for {user.full_name}.')
            return redirect('user-detail', pk=user.pk)
    else:
        form = UserPermissionsForm(user=user)
    return render(request, 'accounts/user_permissions.html', {
        'form': form,
        'user_obj': user,
        'sections': form.get_sections(),
    })


@admin_required
def user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        status = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'User {status} successfully.')
    return redirect('user-detail', pk=user.pk)
