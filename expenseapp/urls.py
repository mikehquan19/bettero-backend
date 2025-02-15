from django.urls import path 
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView, TokenVerifyView, TokenBlacklistView,
)

urlpatterns = [
    # authentication
    path("login", TokenObtainPairView.as_view(), name="login"),
    path("login/refresh", TokenRefreshView.as_view(), name="login_refresh"),
    path("login/verify", TokenVerifyView.as_view(), name="login_verify"),
    path("register", views.Register.as_view(), name="register"),
    path("logout", TokenBlacklistView.as_view(), name="logout"),
    
    # user's financial summary
    path("summary", views.user_summary_detail, name="user_summary"),
    path("full_summary", views.user_full_summary_detail, name="user_full_summary"),

    # account list, detail, and financial summary
    path("accounts", views.AccountList.as_view(), name="account_list"),
    path("accounts/<int:pk>", views.AccountDetail.as_view(), name="account_detail"),
    path("accounts/<int:pk>/summary", views.AccountSummary.as_view(), name="account_summary"),

    # transaction list
    path("transactions", views.UserTransactionList.as_view(), name="user_transactions"),

    path("transactions/interval", views.IntervalTransactionList.as_view(), name="interval_transactions"),
    path("transactions/category/<str:arg_cat>", views.CategoryTransactionList.as_view(), name="category_transactionss"),
    path("transactions/both", views.BothTransactionList.as_view(), name="both_transactions"),

    path("accounts/<int:pk>/transactions", views.AccountTransactionList.as_view(), name="account_transactions"),
    path("accounts/<int:pk>/transactions/both", views.AccBothTransactionList.as_view(), name="account_category_transactions"),

    # budget list and details 
    path("budget", views.UserBudget.as_view(), name="budget"),
    path("budget/<str:interval_type>", views.UserBudgetDetail.as_view(), name="budget_detail"), 

    # bill's list, details, and overdue messages
    path("bills", views.BillList.as_view(), name="bill_list"),
    path("bills/<int:pk>", views.BillsDetail.as_view(), name="bill_detail"), 
    path("overdue_message/", views.OverdueMessageList.as_view(), name="overdue_message_list"),

    # stock list, and details
    path("stocks", views.StockList.as_view(), name="stock_list"), 
    path("stocks/<str:symbol>", views.StockPriceDetail.as_view(), name="stock_price_detail"),
    path("portfolio_value", views.PortfolioValueList.as_view(), name="porfolio_value_list")
]