""" THESE ARE FUNCTIONS COMPUTING THE FINANCE OF THE USER'S BUDGET AND BILLS """

from typing import Dict
from expenseapp.models import BudgetPlan, User
from .utils import *


# calculate the actual compostion percentage of each category vs the goal
def budget_composition_percentage(arg_user: User, period_type: str) -> Dict: 
    queried_plan = BudgetPlan.objects.get(user=arg_user, interval_type=period_type)
 
    # the total expense of each category 
    first_date, last_date = get_current_dates(period_type)
    category_expense = category_expense_dict(arg_user, first_date, last_date)

    # dictionary mapping the type's name to the set of composition percentage of that type
    budget_percentage = {"goal": {}, "actual": {}}
    for category in list(queried_plan.category_portion.keys()): 
        budget_percentage["goal"][category] = queried_plan.category_portion[category]

    total_expense = category_expense["Expense"]
    # if the total expense is 0, then there is no composition
    if total_expense != 0: 
        for category in list(budget_percentage["goal"].keys()): 
            this_category_expense = category_expense[category]
            # calculate the percentage  
            budget_percentage["actual"][category] = (this_category_expense / total_expense) * 100
            budget_percentage["actual"][category] = round(budget_percentage["actual"][category], 2)
    return budget_percentage


# calculate the the progress percentage of each towards that category's budget
def budget_progress_percentage(arg_user: User, interval_type: str) -> Dict: 

    # query the budget plan and total budget
    queried_plan = BudgetPlan.objects.get(user=arg_user, interval_type=interval_type)
    total_budget = float(queried_plan.recurring_income * queried_plan.portion_for_expense / 100)
 
    # the total expense of each category 
    # dates of the current interval of given type
    first_date, last_date = get_current_dates(interval_type) 
    category_expenses = category_expense_dict(arg_user, first_date, last_date)

    """
        dictionary mapping each category to its current expense,
        budget, and its progress percentage 
    """
    progress_percentage = {"Expense": {"budget": total_budget}}

    # add budget to the category first
    for category in list(queried_plan.category_portion.keys()):
        this_category_budget = float(queried_plan.category_portion[category])
        progress_percentage[category] = {
            "budget": this_category_budget * total_budget / 100
        }

    # iterate through each key in the progress percentage dict to add current
    for category in list(progress_percentage.keys()):
        # the current expense of this category 
        progress_percentage[category]["current"] = category_expenses[category]

        # make the code look more neat, really 
        current_progress = progress_percentage[category]["current"]
        budget_progress = progress_percentage[category]["budget"]

        # calculate the progress percentage 
        if current_progress < budget_progress: 
            percentage = (current_progress / budget_progress) * 100
            progress_percentage[category]["percentage"] = round(percentage, 2)
        else: 
            # otherwise, percentage is automatically 100%
            progress_percentage[category]["percentage"] = 100

    return progress_percentage


# get response data for budget plan
def get_budget_response_data(arg_user: User, period_type: str) -> Dict: 
    # budget data
    budget_response = {}
    try: 
        this_plan = BudgetPlan.objects.get(user=arg_user, interval_type=period_type)
    except BudgetPlan.DoesNotExist: 
        return budget_response # return the empty dictionary 
    
    # composition percentage and progress percentage
    budget_composition_dict = budget_composition_percentage(arg_user, period_type)
    budget_progress_dict = budget_progress_percentage(arg_user, period_type)

    budget_response = {
        "id": this_plan.pk,   
        "income": this_plan.recurring_income,
        "expense_portion": this_plan.portion_for_expense, # the budget percentage vs total budget
        "composition": budget_composition_dict, 
        "progress": budget_progress_dict
    }
    return budget_response
