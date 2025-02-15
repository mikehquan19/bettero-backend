"""
THESE ARE THE SUPPLEMENTAL FUNCTIONS THAT WILL SUPPORT OTHER FINANCE FUNCTIONS
"""

from ast import Tuple
from typing import Dict
from django.db.models import Sum
from expenseapp.models import category_dict
from datetime import date, timedelta
from calendar import monthrange

# get the current first and last dates based on the interval type
def get_current_dates(period_type: str=None, arg_first_date: date=None, arg_last_date: date=None) -> Tuple: 
    if not arg_first_date: 
        if period_type != "month": 
            # the number of days of the intervals of given type (week or bi_week)
            in_between_days = 7 if period_type == "week" else 14

            # first and last date of the current interval 
            last_date = date.today() + timedelta(days=(6 - date.today().weekday()))
            first_date = last_date - timedelta(days=(in_between_days - 1))
        else: 
            """
                if the type is month
                first date and last date of the current month
            """
            first_date = date(year=date.today().year, month=date.today().month, day=1)
            last_date = date(
                year=date.today().year, 
                month=date.today().month, 
                day=monthrange(date.today().year, date.today().month)[1]
            )
    else: 
        first_date, last_date = arg_first_date, arg_last_date

    return first_date, last_date 


# get the previous first and last dates 
def get_previous_dates(period_type: str, arg_first_date: date, arg_last_date: date) -> Tuple: 
    if period_type != "month": 
        # the number of days of the intervals of given type (week or bi_week)
        in_between_days = 7 if period_type == "week" else 14
            
        prev_first_date = arg_first_date - timedelta(days=in_between_days)
        prev_last_date = arg_last_date - timedelta(days=in_between_days)
    else: 
        current_year, current_month = arg_first_date.year, arg_first_date.month
        
        # compute the previous month, or year (if necessary)
        previous_month, previous_year = current_month - 1, current_year
        if previous_month == 0:
            previous_month, previous_year = 12, current_year - 1

        prev_first_date = arg_first_date - timedelta(days=monthrange(previous_year, previous_month)[1])
        prev_last_date = arg_last_date - timedelta(days=monthrange(current_year, current_month)[1])

    return prev_first_date, prev_last_date 


# return the dictionary mapping the expense's category to amount for the interval between 2 dates
def category_expense_dict(arg_obj, first_date: date, last_date: date) -> Dict:
    # query the list of transactions (in general) incomes and expenses between 2 dates 
    expense_list = arg_obj.transaction_set.filter(
        occur_date__gte=first_date, 
        occur_date__lte=last_date).exclude(category="Income")
    
    income_list = arg_obj.transaction_set.filter(
        occur_date__gte=first_date, occur_date__lte=last_date, category="Income"
    )
    
    """
    calculate the total expense and the expense of each category
    use the GROUP_BY technique for better query
    """ 
    category_expense = {category: 0.0 for category in list(category_dict.keys())}
    annotated_results = expense_list.values("category").annotate(
        total_amount=Sum("amount", default=0)).order_by()
    for result in annotated_results: 
        category_expense[result["category"]] = float(result["total_amount"])

    # compute expense transactions, and income transactions
    category_expense["Expense"] = float(expense_list.aggregate(total=Sum("amount", default=0))["total"])
    category_expense["Income"] = float(income_list.aggregate(total=Sum("amount", default=0))["total"])

    # total transactions is really just sum of expense and income 
    category_expense["Total"] = category_expense["Expense"] + category_expense["Income"]
    return category_expense