from django.contrib import admin
from .models import (
    BudgetPlan, User, Account, Transaction, Bill, Stock, 
    DateStockPrice, PortfolioValue, OverdueBillMessage
)

admin.site.register(User)
admin.site.register(Account)
admin.site.register(Transaction)
admin.site.register(BudgetPlan)
admin.site.register(Bill)
admin.site.register(Stock)
admin.site.register(DateStockPrice)
admin.site.register(PortfolioValue)
admin.site.register(OverdueBillMessage)