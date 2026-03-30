from django import forms
from .models import Category, Budget, Transaction

INPUT_CLASS = 'w-full bg-slate-50 border border-slate-200 shadow-sm rounded-xl py-3 px-4 text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all outline-none duration-200'

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'type']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g., Groceries'}),
            'type': forms.Select(attrs={'class': INPUT_CLASS}),
        }

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount_limit']
        widgets = {
            'category': forms.Select(attrs={'class': INPUT_CLASS}),
            'amount_limit': forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'placeholder': 'Limit Amount (e.g., 500.00)'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user, type='Expense')
        else:
            self.fields['category'].queryset = Category.objects.filter(type='Expense')

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['category', 'description', 'amount', 'type', 'date']
        widgets = {
            'category': forms.Select(attrs={'class': INPUT_CLASS}),
            'description': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'What was this for?'}),
            'amount': forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'placeholder': 'Amount (e.g., 50.00)'}),
            'type': forms.Select(attrs={'class': INPUT_CLASS}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user)

class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'John'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'john@example.com'}))
    age = forms.IntegerField(widget=forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': '25'}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'New York'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': INPUT_CLASS, 'placeholder': '••••••••'}))

class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6, widget=forms.TextInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 shadow-sm rounded-xl py-4 px-4 text-center tracking-[0.5em] text-2xl font-bold text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all outline-none duration-200', 'placeholder': '------'}))

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'name@example.com'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': INPUT_CLASS, 'placeholder': '••••••••'}))

class UserProfileUpdateForm(forms.Form):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Your name'}))
    age = forms.IntegerField(widget=forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Your age'}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Your city'}))
    occupation = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g., Software Engineer'}))
