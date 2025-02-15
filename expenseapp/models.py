from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

category_dict = {
    "Income": "INCOME",
    "Housing": "HOUSING",
    "Automobile": "AUTO",
    "Medical": "MEDICAL",
    "Subscription": "SUBSCRIPTION",
    "Grocery": "GROCERY", 
    "Dining": "FOOD & DRINK", 
    "Shopping": "SHOPPING", 
    "Gas": "GAS",
    "Others": "OTHERS",
}

# the user account of the app 
class User(AbstractUser): 
    def __str__(self):
        return self.username; 


# the financial account of the user, in general 
class Account(models.Model): 
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    account_number = models.IntegerField()
    name = models.CharField(max_length=50)
    institution = models.CharField(max_length=50)
    account_type = models.CharField(max_length=20, choices={"Debit": "DEBIT", "Credit": "CREDIT"})
    balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, 
        validators=[MinValueValidator(limit_value=Decimal(0.0))]
    )
    # this is strictly for credit accounts 
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    # representation of the account using the account's name 
    def __str__(self): 
        return self.name
    

# transaction in general of the account 
class Transaction(models.Model): 
    # user and account associated with it 
    account = models.ForeignKey(Account, on_delete=models.CASCADE, default=1)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    description = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=category_dict)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, default = 0, 
        validators=[MinValueValidator(limit_value=Decimal(0.01))]
    )
    occur_date = models.DateTimeField("The date transaction was made") # hours were used to sort 

    # representation of the transaction 
    def __str__(self): 
        return self.description
    

def get_default_dict(): 
    return dict(
        Housing=10, 
        Automobile=10, 
        Medical=10, 
        Subscription=10, 
        Grocery=10,
        Dining=10,
        Shopping=10,
        Gas=10,
        Others=20
    )

# the budget plan of the user over the 
class BudgetPlan(models.Model): 
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    # type of the budget plan (budget over month, bi-week, or week)
    interval_type = models.CharField(max_length=20, choices={"month": "MONTH", "bi_week": "BI WEEK", "week": "WEEK"})
    recurring_income = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal(0.01), 
        validators=[MinValueValidator(limit_value=Decimal(0.01))]
    )
    # the portion of the recurring income used for expense (in percentage)
    portion_for_expense = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal(0.0), 
        validators=[
            MinValueValidator(limit_value=Decimal(0)),
            MaxValueValidator(limit_value=Decimal(100)), 
        ])
    category_portion = models.JSONField(default=get_default_dict) # it needs to have same field as category_dict

    class Meta: 
        ordering = ["user"] # this will group the budget plans of same user together 

    # validate the budget plan 
    def clean(self): 
        # the queryset of user's budget plan, excluding this instance. if no instance, id = None
        budget_plan_list = self.user.budgetplan_set.exclude(id=self.id)
        max_plan_count = 3 # the max number of budget plans

        # validate if the number of budget plans exceed 3 
        if budget_plan_list.count() > max_plan_count - 1: 
            raise ValidationError("The number of budget plans must be less than or equal 3")

        # validate if this budget plan overlaps the previous ones
        budget_plan_list = budget_plan_list.filter(interval_type=self.interval_type)
        if budget_plan_list.exists(): 
            raise ValidationError(f"This budget plan's interval overlaps the previous ones ({self.id})")

        # validate if the category percentages don't add up to 100%
        total_percent = sum([float(percent) for percent in list(self.category_portion.values())])
        if total_percent != 100: 
            raise ValidationError("All of the category portions don't add up to 100%")


    # override in order to invoke clean() method before saving the instance 
    def save(self, *args, **kwargs): 
        self.full_clean()
        return super().save(*args, **kwargs)

    # representation of the budget plan using the plan's user name and its type
    def __str__(self): 
        return f"{self.user}'s {self.interval_type} budget plan"


# the montly bills of the user 
class Bill(models.Model): 
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    pay_account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL, default=1)
    description = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=category_dict, default="Housing")
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, default = 0, 
        validators=[MinValueValidator(limit_value=Decimal(1.00))])
    due_date = models.DateField() 

    def __str__(self): 
        return self.description
    

# the value of the user's portfolio
class PortfolioValue(models.Model): 
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    date = models.DateField()

    # valuer of the porfolio on the given date 
    min_validator = [MinValueValidator(limit_value=Decimal(0.00))]
    given_date_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=min_validator)

    def __str__(self): 
        return f"{self.user}'s portfolio value on {self.date}"


# the stock that the user holds
class Stock(models.Model):
    min_validator = [MinValueValidator(limit_value=Decimal(0.00))]

    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    corporation = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    shares = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=min_validator)

    # close price of the stock on the updated date 
    previous_close = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=min_validator)
    current_close = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=min_validator)

    # open, low, and high price of the stock 
    open = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=min_validator)
    low = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=min_validator)
    high = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=min_validator)

    volume = models.BigIntegerField(default=0)  # volume of the stock's trading 
    last_updated_date = models.DateField("The last date the stock was updated")

    # validate if the user has 2 different stocks of the same symbol 
    def clean(self): 
        # the list of stock with this stock symbol, but excluding this stock, if no instance, id = None
        stock_list = self.user.stock_set.exclude(id=self.id).filter(symbol=self.symbol)
        if stock_list.exists(): 
            raise ValidationError(f"This stock overlaps the previous ones ({self.id})")
    
     # override in order to invoke clean() method before saving the instance 
    def save(self, *args, **kwargs): 
        self.full_clean()
        return super().save(*args, **kwargs) 

    # representation of the stock 
    def __str__(self): 
        return self.symbol
    

# the price of the stock of the specific date 
# only store the price of the stock on any date as of the first date of last month 
# (1 month + x days of this month)
class DateStockPrice(models.Model): 
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, default=1)
    date = models.DateField()
    given_date_close =  models.DecimalField(  # the close price of the given stock on the given date 
        max_digits=10, decimal_places=2, default=0, 
        validators=[MinValueValidator(limit_value=Decimal(0.00))]
    )
    
    class Meta: 
        # order the stock price based on the stock and the date 
        ordering = ["stock", "date"]
    
    # representation of the stock's price 
    def __str__(self): 
        return f"{self.stock.symbol}'s close on {self.date}"
    

# the message telling the user that the there are overdue bills 
class OverdueBillMessage(models.Model): 
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    bill_description = models.CharField(max_length=200)
    bill_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default = 0, 
        validators=[MinValueValidator(limit_value=Decimal(1.00))]
    )
    bill_due_date = models.DateField("The date the overdue bill was due", null=True)
    appear_date = models.DateField("The date the message was created", null=True)

    def __str__(self): 
        return self.bill_description
    
