import random
import calendar
from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import Category, Budget, Transaction, UserProfile, EMI
from .forms import CategoryForm, BudgetForm, TransactionForm, SignupForm, OTPForm, LoginForm, UserProfileUpdateForm

@login_required(login_url='trackwise_login')
def profile_view(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST)
        if form.is_valid():
            request.user.first_name = form.cleaned_data['first_name']
            request.user.save()
            user_profile.age = form.cleaned_data['age']
            user_profile.city = form.cleaned_data['city']
            user_profile.occupation = form.cleaned_data.get('occupation', '')
            user_profile.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('trackwise_profile')
    else:
        initial_data = {
            'first_name': request.user.first_name,
            'age': user_profile.age,
            'city': user_profile.city,
            'occupation': user_profile.occupation,
        }
        form = UserProfileUpdateForm(initial=initial_data)
    return render(request, 'profile.html', {
        'form': form,
        'user_profile': user_profile,
        'email': request.user.email,
        'member_since': request.user.date_joined,
    })

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            # Generate 6-digit OTP
            otp = str(random.randint(100000, 999999))
            
            # Store signup data in session
            request.session['signup_data'] = form.cleaned_data
            request.session['otp'] = otp
            
            # Send Email
            try:
                html_message = render_to_string('emails/otp_email.html', {
                    'otp': otp,
                    'first_name': form.cleaned_data['first_name']
                })
                plain_message = strip_tags(html_message)
                
                send_mail(
                    'Your TrackWise OTP Verification Code',
                    plain_message,
                    settings.EMAIL_HOST_USER,
                    [form.cleaned_data['email']],
                    html_message=html_message,
                    fail_silently=False,
                )
                return redirect('trackwise_verify_otp')
            except Exception as e:
                messages.error(request, f"Failed to send email. Please check your SMTP settings. Error: {str(e)}")
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def verify_otp_view(request):
    if 'signup_data' not in request.session or 'otp' not in request.session:
        return redirect('trackwise_signup')

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['otp'] == request.session['otp']:
                data = request.session['signup_data']
                
                # Check if user already exists
                if User.objects.filter(username=data['email']).exists() or User.objects.filter(email=data['email']).exists():
                    messages.error(request, "A user with this email already exists.")
                    return redirect('trackwise_signup')
                
                # Create user
                user = User.objects.create_user(
                    username=data['email'],
                    email=data['email'],
                    password=data['password'],
                    first_name=data['first_name']
                )
                
                # Create UserProfile
                UserProfile.objects.create(
                    user=user,
                    age=data['age'],
                    city=data['city']
                )
                
                # Clear session data
                del request.session['signup_data']
                del request.session['otp']
                
                # Auto-login the user after successful registration
                login(request, user)
                return redirect('trackwise_dashboard')
            else:
                messages.error(request, "Invalid OTP. Please try again.")
    else:
        form = OTPForm()
    return render(request, 'verify_otp.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            # Authenticate typically uses username, which we set as the email
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('trackwise_dashboard')
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('trackwise_login')

def get_emi_deductions(user, year, month):
    """Calculate total EMI burden for a specific month/year"""
    emis = EMI.objects.filter(user=user, active=True, start_date__lte=date(year, month, calendar.monthrange(year, month)[1]))
    total_deduction = 0
    
    for emi in emis:
        # Skip if end_date exists and is in the past
        if emi.end_date and emi.end_date < date(year, month, 1):
            continue
            
        if emi.frequency == 'Monthly':
            total_deduction += emi.amount
        elif emi.frequency == 'Weekly':
            # Count occurrences of start_date's weekday in the target month
            weekday = emi.start_date.weekday() # 0=Mon, 6=Sun
            first_day, last_day = calendar.monthrange(year, month)
            count = 0
            for d in range(1, last_day + 1):
                curr_date = date(year, month, d)
                if curr_date.weekday() == weekday and curr_date >= emi.start_date:
                    if not emi.end_date or curr_date <= emi.end_date:
                        count += 1
            total_deduction += (count * emi.amount)
            
    return total_deduction

def get_all_time_emi_burden(user, target_date=None):
    """Calculate total accumulated EMI burden up to a specific date (defaults to today)"""
    if target_date is None:
        target_date = date.today()
    
    emis = EMI.objects.filter(user=user, start_date__lte=target_date)
    total_accumulated = 0
    
    for emi in emis:
        # The EMI stops accumulating at either its end_date or the target_date
        effective_end = min(emi.end_date, target_date) if emi.end_date else target_date
        
        if emi.frequency == 'Monthly':
            # Count months: (Year difference * 12) + Month difference
            months_diff = (effective_end.year - emi.start_date.year) * 12 + (effective_end.month - emi.start_date.month)
            count = months_diff
            # If the end day is >= start day, it means the current month's payment has occurred
            if effective_end.day >= emi.start_date.day:
                count += 1
            total_accumulated += (max(0, count) * emi.amount)
            
        elif emi.frequency == 'Weekly':
            days_diff = (effective_end - emi.start_date).days
            count = (days_diff // 7) + 1
            total_accumulated += (max(0, count) * emi.amount)
            
    return total_accumulated

@login_required(login_url='trackwise_login')
def dashboard_view(request):
    # Get period from request or default to current month
    now = timezone.now()
    month_raw = request.GET.get('month')
    year_raw = request.GET.get('year')
    
    month = int(month_raw) if month_raw and month_raw.isdigit() else now.month
    year = int(year_raw) if year_raw and year_raw.isdigit() else now.year
    
    # Calculate previous and next month for navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    # Selected Month Statistics
    transactions = Transaction.objects.filter(user=request.user, date__month=month, date__year=year).order_by('-date')
    recent_transactions = transactions[:5]
    
    # EMI Deductions
    emi_total = get_emi_deductions(request.user, year, month)
    
    # EMI Toggle State
    show_emi = request.GET.get('show_emi', 'true') == 'true'
    
    # Adjust Income (Net Income)
    selected_income = (Transaction.objects.filter(user=request.user, type='Income', date__month=month, date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0)
    if show_emi:
        selected_income -= emi_total
    
    selected_expenses = Transaction.objects.filter(user=request.user, type='Expense', date__month=month, date__year=year).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # All-time Net Worth (Cumulative)
    all_income = Transaction.objects.filter(user=request.user, type='Income').aggregate(Sum('amount'))['amount__sum'] or 0
    all_expenses = Transaction.objects.filter(user=request.user, type='Expense').aggregate(Sum('amount'))['amount__sum'] or 0
    total_balance = all_income - all_expenses
    
    emi_all_time = 0
    if show_emi:
        # Deduct all-time EMI burden from net worth
        emi_all_time = get_all_time_emi_burden(request.user)
        total_balance -= emi_all_time
    
    # Category summary for the selected month
    categories = Category.objects.filter(user=request.user).annotate(
        total_spent=Sum('transaction__amount', filter=Q(
            transaction__type='Expense', 
            transaction__date__month=month, 
            transaction__date__year=year
        ))
    ).filter(total_spent__gt=0)
    
    context = {
        'recent_transactions': recent_transactions,
        'selected_income': selected_income,
        'selected_expenses': selected_expenses,
        'emi_burden': emi_total,
        'total_balance': total_balance,
        'emi_all_time': emi_all_time,
        'categories_summary': categories,
        'current_month_name': calendar.month_name[month],
        'current_month': month,
        'current_year': year,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'is_current_period': (month == now.month and year == now.year),
        'show_emi': show_emi
    }
    return render(request, 'dashboard.html', context)

@login_required(login_url='trackwise_login')
def transaction_list_view(request):
    now = timezone.now()
    month = request.GET.get('month')
    year = request.GET.get('year')
    
    # Filter by search query if provided
    query = request.GET.get('q')
    if query:
        transactions = Transaction.objects.filter(
            user=request.user
        ).filter(
            Q(description__icontains=query) | 
            Q(category__name__icontains=query)
        ).order_by('-date')
        period_name = f"Search results for '{query}'"
    # Filter by month/year if provided
    elif month and year:
        transactions = Transaction.objects.filter(user=request.user, date__month=month, date__year=year).order_by('-date')
        period_name = f"{calendar.month_name[int(month)]} {year}"
    else:
        transactions = Transaction.objects.filter(user=request.user).order_by('-date')
        period_name = "All Time"

    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            return redirect('trackwise_transactions')
    else:
        # Pre-fill type if provided in GET
        initial_type = request.GET.get('type', 'Expense')
        form = TransactionForm(initial={'type': initial_type}, user=request.user)
    return render(request, 'transactions.html', {
        'transactions': transactions, 
        'form': form,
        'period_name': period_name
    })

@login_required(login_url='trackwise_login')
def category_list_view(request):
    categories = Category.objects.filter(user=request.user)
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            return redirect('trackwise_categories')
    else:
        form = CategoryForm()
    
    context = {
        'categories': categories,
        'form': form
    }
    return render(request, 'categories.html', context)

@login_required(login_url='trackwise_login')
def budget_list_view(request):
    budgets = Budget.objects.filter(category__user=request.user, category__type='Expense')
    budget_data = []
    current_month = timezone.now().month
    current_year = timezone.now().year
    
    total_budget_expense = 0
    total_spent_expense = 0
    
    for budget in budgets:
        spent = Transaction.objects.filter(
            user=request.user,
            category=budget.category, 
            type=budget.category.type,
            date__month=current_month,
            date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Only include expenses in the header summary totals
        if budget.category.type == 'Expense':
            total_budget_expense += budget.amount_limit
            total_spent_expense += spent
            
        percentage = min(int((spent / budget.amount_limit) * 100) if budget.amount_limit > 0 else 100, 100)
        budget_data.append({
            'budget': budget,
            'spent': spent,
            'percentage': percentage,
            'is_exceeded': percentage >= 100,
            'is_warning': percentage >= 85 and percentage < 100
        })
        
    if request.method == 'POST':
        category_id = request.POST.get('category')
        instance = Budget.objects.filter(category_id=category_id, category__user=request.user).first()
        form = BudgetForm(request.POST, instance=instance, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.save()
            messages.success(request, f"Budget limit updated successfully.")
            return redirect('trackwise_budgets')
    else:
        form = BudgetForm(user=request.user)
        
    context = {
        'budget_data': budget_data,
        'form': form,
        'total_budget': total_budget_expense,
        'total_spent': total_spent_expense,
    }
    return render(request, 'budgets.html', context)

@login_required(login_url='trackwise_login')
def reports_view(request):
    now = timezone.now()
    month_raw = request.GET.get('month')
    year_raw = request.GET.get('year')
    current_month = int(month_raw) if month_raw and month_raw.isdigit() else now.month
    current_year = int(year_raw) if year_raw and year_raw.isdigit() else now.year

    # 1. Monthly Summary (For Selected Period)
    total_income = Transaction.objects.filter(
        user=request.user,
        type='Income', 
        date__month=current_month, 
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # EMI Deductions for the report period
    emi_total = get_emi_deductions(request.user, current_year, current_month)
    total_income -= emi_total
    
    total_expenses = Transaction.objects.filter(
        user=request.user,
        type='Expense', 
        date__month=current_month, 
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    savings = total_income - total_expenses
    savings_rate = (savings / total_income * 100) if total_income > 0 else 0

    # 2. Category Breakdown (Expenses)
    category_expenses = Category.objects.filter(user=request.user, type='Expense').annotate(
        amount=Sum('transaction__amount', filter=Q(
            transaction__type='Expense',
            transaction__date__month=current_month,
            transaction__date__year=current_year
        ))
    ).filter(amount__gt=0).order_by('-amount')

    categories_list = []
    for cat in category_expenses:
        percentage = (cat.amount / total_expenses * 100) if total_expenses > 0 else 0
        categories_list.append({
            'name': cat.name,
            'amount': cat.amount,
            'percentage': round(percentage, 1),
            'icon': cat.icon,
            'color': cat.color_class
        })

    # 3. Monthly Trends (Last 6 Months)
    trends_raw = []
    max_val = 0
    for i in range(5, -1, -1):
        target_month = current_month - i
        target_year = current_year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        m_inc = Transaction.objects.filter(user=request.user, type='Income', date__month=target_month, date__year=target_year).aggregate(Sum('amount'))['amount__sum'] or 0
        m_emi = get_emi_deductions(request.user, target_year, target_month)
        m_inc = max(0, m_inc - m_emi) # Net Income
        
        m_exp = Transaction.objects.filter(user=request.user, type='Expense', date__month=target_month, date__year=target_year).aggregate(Sum('amount'))['amount__sum'] or 0
        
        max_val = max(max_val, m_inc, m_exp)
        trends_raw.append({
            'month': calendar.month_name[target_month][:3],
            'income': m_inc,
            'expense': m_exp
        })

    # Scale the heights based on max_val
    trends = []
    scale = max_val / 100 if max_val > 0 else 1
    for t in trends_raw:
        trends.append({
            'month': t['month'],
            'income': t['income'],
            'expense': t['expense'],
            'income_h': max(2, int(t['income'] / scale)) if t['income'] > 0 else 2,
            'expense_h': max(2, int(t['expense'] / scale)) if t['expense'] > 0 else 2
        })

    # Calculate previous and next month for navigation
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    next_month = current_month + 1 if current_month < 12 else 1
    next_year = current_year if current_month < 12 else current_year + 1

    context = {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'savings': savings,
        'savings_rate': round(savings_rate, 1),
        'category_expenses': categories_list,
        'trends': trends,
        'top_category': categories_list[0] if categories_list else None,
        'current_month_name': calendar.month_name[current_month],
        'current_month': current_month,
        'current_year': current_year,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'is_current_period': (current_month == now.month and current_year == now.year),
        'emi_burden': emi_total
    }
    return render(request, 'reports.html', context)

@login_required(login_url='trackwise_login')
def delete_transaction_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, "Transaction deleted successfully.")
    return redirect('trackwise_transactions')

@login_required(login_url='trackwise_login')
def delete_category_view(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        category.delete()
        messages.success(request, "Category deleted successfully.")
    return redirect('trackwise_categories')

@login_required(login_url='trackwise_login')
def delete_budget_view(request, pk):
    budget = get_object_or_404(Budget, pk=pk, category__user=request.user)
    if request.method == 'POST':
        category_name = budget.category.name
        budget.delete()
        messages.success(request, f"Budget for {category_name} removed successfully.")
    return redirect('trackwise_budgets')

@login_required(login_url='trackwise_login')
def emi_list_view(request):
    if request.method == 'POST':
        description = request.POST.get('description')
        amount = request.POST.get('amount')
        frequency = request.POST.get('frequency')
        start_date = request.POST.get('start_date')
        
        EMI.objects.create(
            user=request.user,
            description=description,
            amount=amount,
            frequency=frequency,
            start_date=start_date
        )
        messages.success(request, f"EMI for '{description}' added successfully.")
        return redirect('trackwise_emi')

    emis = EMI.objects.filter(user=request.user)
    today = date.today()
    monthly_burden = get_emi_deductions(request.user, today.year, today.month)
    
    return render(request, 'emi.html', {
        'emis': emis,
        'monthly_burden': monthly_burden
    })

@login_required(login_url='trackwise_login')
def delete_emi_view(request, pk):
    emi = get_object_or_404(EMI, pk=pk, user=request.user)
    if request.method == 'POST':
        description = emi.description
        emi.delete()
        messages.success(request, f"EMI for '{description}' removed.")
    return redirect('trackwise_emi')
