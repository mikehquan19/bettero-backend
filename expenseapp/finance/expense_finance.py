""" THESE ARE FUNCTIONS COMPUTING THE FINANCE OF THE USER'S EXPENSE """

from typing import Dict, List, Tuple
from django.db.models import Sum
from datetime import date, timedelta
from expenseapp.models import Account, Transaction, User, category_dict
from .utils import *


# return the total balance of all debit accounts of the user as a tuple 
def total_balance_and_amount_due(arg_user: User) -> Tuple: 
    # list of debit and credit accounts 
    debit_account_list = Account.objects.filter(user=arg_user, account_type="Debit")
    credit_account_list = Account.objects.filter(user=arg_user, account_type="Credit")

    # compute the total balance (balance of debit accounts) and amount due (credit accounts)
    total_balance = debit_account_list.aggregate(total=Sum("balance", default=0))["total"]
    total_amount_due = credit_account_list.aggregate(total=Sum("balance", default=0))["total"]
    return (total_balance, total_amount_due)


# return the total income of the user of this interval
def total_income(arg_user: User, arg_first_date: date=None, arg_last_date: date=None) -> float: 
    # determine the first and last date of the month
    first_date, last_date = get_current_dates("month", arg_first_date, arg_last_date)

    # query the list of incomes of the user between the first and last date 
    income_list = Transaction.objects.filter(
        user=arg_user, category="Income", 
        occur_date__gte=first_date, occur_date__lte=last_date
    )

    # compute the total income 
    total_income = income_list.aggregate(total=Sum("amount", default=0))["total"]
    return total_income 


# return the dictionary mapping the date to the total expense of that date 
# up until the current date 
def daily_expense(arg_user: User, arg_first_date: date=None, arg_last_date: date=None) -> Dict: 
    daily_exepense = {} # result dict 

    if not arg_first_date or not arg_last_date: 
        first_date , last_date = date(
            year=date.today().year, 
            month=date.today().month, 
            day=1), date.today()
    else: 
        first_date, last_date = arg_first_date, arg_last_date
    
    # loop through the dates from first date to today 
    current_date = first_date
    while current_date <= last_date: 
        # query list of expenses between current date and next date 
        current_expense_list = Transaction.objects.filter(
            user=arg_user, 
            occur_date__gte=current_date, 
            occur_date__lt=(current_date + timedelta(days=1))).exclude(category="Income")
        
        # compute the total_expense 
        total_expense = float(current_expense_list.aggregate(total=Sum("amount", default=0))["total"])

        # add the mapping betweeen date and expense to the dict
        daily_exepense[current_date.strftime("%m/%d/%Y")] = total_expense
        current_date += timedelta(days=1)

    return daily_exepense 


"""
    calculate the percent composition of each expense category
    return the dict mapping each category to its composition percentage
""" 
def expense_composition_percentage(arg_obj, arg_first_date: date=None, arg_last_date: date=None) -> Dict: 
    # dictionary mapping the category to the total expense this month 
    first_date, last_date = get_current_dates("month", arg_first_date, arg_last_date)
    category_expense = category_expense_dict(arg_obj, first_date, last_date)
    
    """
        dictionary mapping the expense's category to the percentage of expense
        avoid hardcoding the category 
    """
    composition_percentage = {category : 0.0 for category in list(category_dict.keys()) if category != "Income"}

    # total expense indicates that no transactions have been made 
    if category_expense["Total"] != 0:  
        # list of the keys of this dictionary
        for category in list(composition_percentage.keys()):  
            composition_percentage[category] = (category_expense[category] / category_expense["Total"]) * 100
            composition_percentage[category] = round(composition_percentage[category], 2)

    return composition_percentage


# calculate how the total expenses and expense of each category have changed 
def expense_change_percentage(arg_obj, period_type: str="month", arg_first_date: date=None, arg_last_date: date=None) -> Dict: 
    # the first and last date of the current period and the previous period
    curr_date1, curr_date2 = get_current_dates(period_type, arg_first_date, arg_last_date)
    prev_date1, prev_date2 = get_previous_dates(period_type, curr_date1, curr_date2)

    # dict mapping the expense's category to amount for the current and previous month 
    curr_expense_dict = category_expense_dict(arg_obj, curr_date1, curr_date2)
    prev_expense_dict = category_expense_dict(arg_obj, prev_date1, prev_date2)

    # dict mapping each category to the list [current, previous, change percentage]
    change_percentage = {category : 0.0 for category in list(category_dict.keys()) if category != "Income"}

    # calculate the change percentage 
    for category in list(change_percentage.keys()): 
        if prev_expense_dict[category] != 0: 
            # calculate the percentage change and then add to the dict
            change_percentage[category] = curr_expense_dict[category] - prev_expense_dict[category]
            change_percentage[category] = (change_percentage[category] / prev_expense_dict[category]) * 100
            change_percentage[category] = round(change_percentage[category], 2)
        else: 
            # if no expenses made during previous month, obviously expenses increase 100% 
            change_percentage[category] = 100.00 if curr_expense_dict[category] != 0 else 0.00

    return change_percentage


# adjust the balance of the debit account based on the amount and flow
# return nothing
def adjust_account_balance(account: Account, transaction: Transaction) -> None: 
    # multiplier will determine the result based on if transaction is expense or income
    multiplier = 1 
    if transaction.category == "Income":
        multiplier = -1
    """
        if the account is debit, amount is extracted from the balance
        otherwise, amount is added to the balance
    """
    if account.account_type == "Debit":
        account.balance -= multiplier * transaction.amount
    else:  
        account.balance += multiplier * transaction.amount
    # save the adjustment to the database 
    account.save() 


# return the list of latest intervals (month, bi_week, or week), intervals = tuple (first_date, last_date)
def latest_periods(period_type: str, num_periods: int) -> List: 
    # the list of latest time intervals 
    latest_intervals = [] 
    first_date, last_date = get_current_dates(period_type)
    for i in range(num_periods): 
        latest_intervals.append((first_date, last_date))
        first_date, last_date = get_previous_dates(period_type, first_date, last_date)
    return latest_intervals


# return the total expense of each interval depending on the type of the interval
def interval_total_expense(arg_user: User) -> Dict: 
    # the latest months, bi-weeks, and weeks in the dictionary 
    latest_periods_dict = {}
    num_latest_periods = 5 # get the data of 5 latest periods 
    for time_type in ["month", "bi_week", "week"]: 
        latest_periods_dict[time_type] = latest_periods(time_type, num_latest_periods)

    # the dictionary mapping the interval type to the list of expense of each interval
    period_expense_dict = {}
    for period_type in list(latest_periods_dict.keys()): 
        period_expense_dict[period_type] = []
        interval_list = latest_periods_dict[period_type]

        # compute total expense for each interval of the list 
        for interval in interval_list: 
            # first and last date of the interval 
            first_date, last_date = interval[0], interval[1]

            # first key-value pair of total_expense_dict is total expense of all categories
            total_expense = category_expense_dict(arg_user, first_date, last_date)["Total"]

            # the expense change and composition of the user during this period
            expense_change = expense_change_percentage(arg_user, period_type, first_date, last_date)
            expense_composition = expense_composition_percentage(arg_user, first_date, last_date)
            
            # daily expense of the user during this period
            period_daily_expense = daily_expense(arg_user, first_date, last_date)
            
            period_expense_dict[period_type].append({
                "first_date": first_date, 
                "last_date": last_date, 
                "total_expense": total_expense,
                "expense_change": expense_change, 
                "expense_composition": expense_composition,
                "daily_expense": period_daily_expense,
            })
     
    return period_expense_dict