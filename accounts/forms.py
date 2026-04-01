from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from accounts.models import PagePermission, PAGE_REGISTRY

User = get_user_model()


class PhoneLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter phone number',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
        }),
    )


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = ['phone_number', 'full_name', 'role']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        pw2 = cleaned_data.get('password_confirm')
        if pw and pw2 and pw != pw2:
            self.add_error('password_confirm', 'Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if user.role == User.Role.ADMIN:
            user.is_staff = True
        if commit:
            user.save()
            # Admins get all permissions automatically
            if user.role == User.Role.ADMIN:
                user.page_permissions.set(PagePermission.objects.all())
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['phone_number', 'full_name', 'role', 'is_active']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.role == User.Role.ADMIN:
            user.is_staff = True
        else:
            user.is_staff = False
        if commit:
            user.save()
            # When promoted to admin, grant all permissions
            if user.role == User.Role.ADMIN:
                user.page_permissions.set(PagePermission.objects.all())
        return user


class UserPermissionsForm(forms.Form):
    """Checkbox form for assigning page permissions to a user.
    Permissions are grouped by section for a clean layout."""

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Build one checkbox per page, grouped by section
        all_perms = PagePermission.objects.all()
        user_perm_keys = set()
        if user:
            user_perm_keys = set(user.page_permissions.values_list('page_key', flat=True))

        for perm in all_perms:
            self.fields[perm.page_key] = forms.BooleanField(
                label=perm.display_name,
                required=False,
                initial=perm.page_key in user_perm_keys,
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            )

    def get_sections(self):
        """Return fields grouped by section for template rendering."""
        all_perms = PagePermission.objects.all()
        sections = {}
        for perm in all_perms:
            if perm.section not in sections:
                sections[perm.section] = []
            field = self[perm.page_key]
            sections[perm.section].append(field)
        return sections

    def save(self):
        if not self.user:
            return
        selected_keys = [key for key, val in self.cleaned_data.items() if val]
        perms = PagePermission.objects.filter(page_key__in=selected_keys)
        self.user.page_permissions.set(perms)
