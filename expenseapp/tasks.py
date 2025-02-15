from timeit import default_timer
from celery import shared_task
from .models import (
    Account, PortfolioValue, User, Stock, DateStockPrice, 
    Transaction, OverdueBillMessage 
)
from django.db import transaction
from django.db.models import F, Sum
from datetime import timedelta, date
from .finance import update_stock_data

# update the due date of the credit account (every month)
@shared_task(bind=True, max_retries=1, default_retry_delay=60)
@transaction.atomic
def update_credit_due_date(self) -> None:
    try:
        # query the list of credit accounts 
        credit_accounts_to_create = []
        for account in Account.objects.filter(account_type="Credit", due_date__lte=date.today()): 
            # increment the due date 
            if account.due_date.month == 12:
                account.due_date.replace(year=account.due_date.year + 1, month=1)
            else: 
                account.due_date.replace(month=account.due_date.month + 1)
            # append to the list 
            credit_accounts_to_create.append(account)
        # credit account to 
        Account.objects.bulk_update(credit_accounts_to_create, ["due_date"])
    except Exception as exc: 
        # print the traceback of the errors 
        raise self.retry(exc=exc)


# update the info of the stock and create the record for the previous day
@shared_task(bind=True, max_retries=1, default_retry_delay=60)
@transaction.atomic
def update_info_and_create_price(self) -> None: 
    try: 
        # if it's sunday or monday, we won't need to check for the change since the market is closed 
        weekday = date.today().weekday()
        if weekday == 0 or weekday == 6: 
            print(f"There is nothing to update.")
            return  
        
        updated_stock_list = []
        updated_field_list = ["previous_close", "current_close", "open", "low", "high", "volume", "last_updated_date"]

        for stock in Stock.objects.all(): 
            # fetch the updated info about the stock 
            updated_stock_data = update_stock_data(stock.symbol)

            """
                update the data of each stock instance in the database
                current close, previous_close, open, low, high, volume
            """
            stock.previous_close = stock.current_close
            stock.current_close = updated_stock_data["new_close"]
            stock.open = updated_stock_data["new_open"]
            stock.low = updated_stock_data["new_low"]
            stock.high = updated_stock_data["new_high"]
            stock.volume = updated_stock_data["new_volume"]

            # update the last_updated_date 
            if stock.last_updated_date.weekday() == 4: 
                stock.last_updated_date += timedelta(days=3)
            else: 
                stock.last_updated_date += timedelta(days=1)

            # add stock the list of stocks to update 
            updated_stock_list.append(stock)
                
        # using bulk_update() to update with only 1 query 
        num_updated_stock = Stock.objects.bulk_update(updated_stock_list, updated_field_list)
        updated_stock_queryset = Stock.objects.all()
        print(f"{num_updated_stock} stocks updated successfully!")

        # create the new date price instance for the updated stock
        created_stock_price_list = []
        for updated_stock in updated_stock_queryset: 
            created_stock_price_list.append(DateStockPrice(
                stock=updated_stock, date=updated_stock.last_updated_date, 
                given_date_close=updated_stock.current_close,
            ))
        # bulk_create() to make it more efficient 
        created_queryset = DateStockPrice.objects.bulk_create(created_stock_price_list)
        print(f"{len(created_queryset)} dates stock price created")

        # create the value of the portfolio 
        create_portfolio_value()
        
    except Exception as exc: 
         raise self.retry(exc=exc)


# create the new portfolio value for the previous date 
def create_portfolio_value() -> None: 
    # the date previous to the date in real time 
    previous_date = date.today() - timedelta(days=1)
    created_portfolio_value_list = []

    for user in User.objects.all(): 
        # compute the total value of the user's portfolio 
        user_portfolio = Stock.objects.filter(user=user).annotate(total_value=F("current_close") * F("shares"))
        total_value = user_portfolio.aggregate(total=Sum("total_value", default=0))["total_value"]

        created_portfolio_value_list.append(PortfolioValue(
            user=user, date=previous_date, given_date_value=total_value
        ))
    PortfolioValue.objects.bulk_create(created_portfolio_value_list)


# delete the list of date prices and portfolio prices that were beyond first day of last month
@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def delete_price(self) -> None: 
    try:
        # compute the first date of last month
        current_month, current_year = date.today().month, date.today().year
        prev_month, prev_year = current_month - 1, current_year
        if prev_month < 0: 
            prev_month, prev_year = 12, prev_year - 1
        first_date_last_month = date(year=prev_year, month=prev_month, day=1)

        # query the list of price instance and delete 
        DateStockPrice.objects.filter(date__lt=first_date_last_month).delete()
        PortfolioValue.objects.filter(date__lt=first_date_last_month).delete()
    except Exception as exc: 
        raise self.retry(exc=exc)
        

# delete the list of transactions that 
@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def delete_transactions(self) -> None: 
    try:
        # compute the first date of 5 months ago 
        first_date_this_month = date(year=date.today().year, month=date.today().month, day=1)
        filter_date = first_date_this_month - timedelta(weeks=18)

        # query the list of transactions that are 5months old and delete
        old_transaction_list = Transaction.objects.filter(occur_date__lt=filter_date)
        old_transaction_list.delete()
    except Exception as exc: 
        self.retry(exc=exc)


# delete overdue bills, and add the messages to the list 
@shared_task(bind=True, max_retries=1, default_retry_delay=60)
@transaction.atomic
def delete_overdue_bills_and_messages(self) -> None: 
    try:
        for user in User.objects.all(): 
            # query the given user's list of overdue bills 
            overdue_bill_list = user.bills_set.filter(due_date__lt=date.today())
            created_overdue_message_list = []

            # add the overdue message corresponding to the bills
            for overdue_bill in overdue_bill_list: 
                created_overdue_message_list.append(OverdueBillMessage(
                    user=user, bill_description=overdue_bill.description, 
                    bill_amount=overdue_bill.amount, bill_due_date=overdue_bill.due_date, 
                     appear_date=date.today()
                ))
            OverdueBillMessage.objects.bulk_create(created_overdue_message_list)
            # delete the queryset 
            overdue_bill_list.delete()
        
        """
            automatically delete the overdue bills message that are one day old
            query the list of 1-day-old overdue messages and delete them 
        """
        overdue_message_list = OverdueBillMessage.objects.filter(appear_date__lt=date.today())
        overdue_message_list.delete()
    except Exception as exc: 
        self.retry(exc=exc)
