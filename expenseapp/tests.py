
from .models import (
    category_dict,
    User, Account, Transaction, DateStockPrice, Stock, PortfolioValue
)
from .finance import (
    category_expense_dict, expense_composition_percentage, expense_change_percentage, 
    get_first_and_last_dates
)
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Sum
from datetime import date, timedelta, datetime
import random
import json

"""THE FUNCTIONS TO UPLOAD TEST RECORDS TO THE DATABASE TO TEST FINANCE LOGICS"""


# write function to upload data to database so that we can test utils
@transaction.atomic
def upload_category_transactions(num_transaction_each: int=3): 
    # create the transactions 
    random.seed(4) # to ensure same sequence of random floats were generated 
    transactions_to_create = []

    for category in list(category_dict.keys()):
        for i in range(num_transaction_each):
            # append transaction for this month 
            transactions_to_create.append(Transaction(
                user=User.objects.get(username="mikeusername"), account=Account.objects.get(account_number=1000),
                description=f"Test {category} Transaction #{i + 1} this month", category=category,
                amount=round(random.uniform(5, 100), 2), occur_date=timezone.now()
            ))

            # one transaction for the previous month 
            transactions_to_create.append(Transaction(
                user=User.objects.get(username="mikeusername"), account=Account.objects.get(account_number=1000),
                description=f"Test {category} Transaction #{i + 1} previous month", category=category,
                amount=round(random.uniform(5, 100), 2), occur_date=(timezone.now() - timedelta(days=28))
            ))

    created_transactions = Transaction.objects.bulk_create(transactions_to_create)
    print(f"{len(created_transactions)} transactions were created.")

    # compute category expense this month and previous month using utils 
    this_month_category_expense = category_expense_dict(
        arg_obj=User.objects.get(username="mikeusername"), 
        first_date=date.today(), last_date=date.today() + timedelta(days=1)
    )
    
    prev_month_category_expense = category_expense_dict(
        arg_obj=User.objects.get(username="mikeusername"),
        first_date=date.today() - timedelta(days=1), last_date=date.today()
    )
    
    # compute category composition 
    category_composition = expense_composition_percentage(arg_obj=User.objects.get(username="mikeusername"))
    
    # compute category change 
    category_change = expense_change_percentage(arg_obj=User.objects.get(username="mikeusername"))
    
    print(json.dumps(this_month_category_expense, indent=4))
    print(json.dumps(prev_month_category_expense, indent=4))

    print(json.dumps(category_composition, indent=4))
    print(json.dumps(category_change, indent=4))


# upload transactions along the interval 
@transaction.atomic
def upload_interval_transactions(num_transactions_each: int=2): 
    # create transactions 
    random.seed(3)
    transactions_to_create = [] 
    test_account_numbers = [1000, 1001, 2000, 3000] 

    
    current_date = date.today() - timedelta(weeks=17)
    while current_date <= date.today(): 
        # convert the date to the timezone-aware datetime object 
        converted_datetime = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))

        # for each date, create the num transactions 
        for i in range(num_transactions_each): 
            cat = random.choice(list(category_dict.keys()))

            # append one transaction for this month 
            transactions_to_create.append(Transaction(
                user=User.objects.get(username="mikeusername"), account=Account.objects.get(account_number=random.choice(test_account_numbers)),
                description=f"Test {current_date.strftime("%m/%d/%Y")} {cat} Transaction #{i + 1}", category=cat,
                amount=round(random.uniform(20, 50), 2), occur_date=converted_datetime
            ))

        current_date += timedelta(days=1)

    created_transactions = Transaction.objects.bulk_create(transactions_to_create)
    print(f"{len(created_transactions)} transactions were created.")


@transaction.atomic
def delete_test_transactions(): 
    Transaction.objects.filter(description__contains="Test").delete()
    print("Test Transaction deleted successfully")


@transaction.atomic
def upload_test_portfolio_values(): 
    user = User.objects.get(username="mikeusername")
    stocks = [stock for stock in Stock.objects.filter(user=user)]
    created_portfolio_values = []

    first_date, last_date = get_first_and_last_dates()
    current_date = first_date 
    while current_date <= last_date: 
        date_prices = DateStockPrice.objects.filter(date=current_date, stock__in=stocks)
        date_prices = date_prices.annotate(total_value=F("given_date_close") * F("stock__shares"))
        total_value = date_prices.aggregate(total=Sum("total_value", default=0))["total"]

        if total_value != 0: 
            created_portfolio_values.append(
                PortfolioValue(user=user, date=current_date, given_date_value=total_value))
        # INCREMENT
        current_date += timedelta(days=1)
    num_values = PortfolioValue.objects.bulk_create(created_portfolio_values)
    print(f"{len(num_values)} created!")
