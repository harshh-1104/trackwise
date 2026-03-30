from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='trackwise_signup'),
    path('verify-otp/', views.verify_otp_view, name='trackwise_verify_otp'),
    path('login/', views.login_view, name='trackwise_login'),
    path('logout/', views.logout_view, name='trackwise_logout'),

    path('', views.dashboard_view, name='trackwise_dashboard'),
    path('transactions/', views.transaction_list_view, name='trackwise_transactions'),
    path('categories/', views.category_list_view, name='trackwise_categories'),
    path('budgets/', views.budget_list_view, name='trackwise_budgets'),
    path('reports/', views.reports_view, name='trackwise_reports'),
    path('profile/', views.profile_view, name='trackwise_profile'),
    path('transactions/delete/<int:pk>/', views.delete_transaction_view, name='trackwise_delete_transaction'),
    path('categories/delete/<int:pk>/', views.delete_category_view, name='trackwise_delete_category'),
    path('budgets/delete/<int:pk>/', views.delete_budget_view, name='trackwise_delete_budget'),
    path('emi/', views.emi_list_view, name='trackwise_emi'),
    path('emi/delete/<int:pk>/', views.delete_emi_view, name='trackwise_delete_emi'),
]
