from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class AdminCreateUserForm(forms.Form):
    username = forms.CharField(label='Логин', max_length=150)
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Повтор пароля', widget=forms.PasswordInput)
    role = forms.ChoiceField(
        label='Роль',
        choices=[
            ('user', 'Пользователь'),
            ('tech_admin', 'Тех. администратор'),
        ],
    )
    email = forms.EmailField(label='Email', required=False)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Пользователь с таким логином уже есть.')
        return username

    def clean_password1(self):
        p1 = self.cleaned_data.get('password1')
        if p1:
            validate_password(p1)
        return p1

    def clean(self):
        data = super().clean()
        p1 = data.get('password1')
        p2 = data.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError('Пароли не совпадают.')
        return data

    def save(self):
        data = self.cleaned_data
        return User.objects.create_user(
            username=data['username'],
            password=data['password1'],
            email=data.get('email') or '',
            role=data['role'],
        )
