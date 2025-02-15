from decimal import Decimal
from typing import Dict
from datetime import date, timedelta
import yfinance as yf

# get the first date of last month and current date 
def get_first_and_last_dates(): 
    current_date = date.today() # the last date (which is today)

    """
        the first date (which is first date of last month)
        month and year of the last date 
    """
    current_month, current_year = current_date.month, current_date.year
    prev_month, prev_year = current_month - 1, current_year
    if prev_month < 0: 
        prev_month, prev_year = 12, prev_year - 1

    first_date_last_month = date(year=prev_year, month=prev_month, day=1)
    return first_date_last_month, current_date


# convert the date obj to string 
def to_string(arg_date): 
    return f"{arg_date.year}-{arg_date.month}-{arg_date.day}"


# convert string to the date obj
def to_date(arg_str): 
    str_arr = arg_str.split("-")
    return date(year=int(str_arr[0]), month=int(str_arr[1]), day=int(str_arr[2]))


"""
    load the initial price of the stock since first date of last month
    till the today along with current data of the stock 
"""
def load_stock_data(symbol: str) -> Dict: 
    # get the first and last date 
    first_date, last_date = get_first_and_last_dates()
    # load data of the stock's info 
    recent_data = yf.download([symbol], start=to_string(first_date), end=to_string(last_date))

    # current info of the stock 
    custom_data = {
        "current_close": round(Decimal(recent_data["Adj Close"].iloc[-1]), 2),
        "previous_close": round(Decimal(recent_data["Adj Close"].iloc[-2]), 2), 
        "open": round(Decimal(recent_data["Open"].iloc[-1]), 2), 
        "high": round(Decimal(recent_data["High"].iloc[-1]), 2), 
        "low": round(Decimal(recent_data["Low"].iloc[-1]), 2), 
        "volume": int(recent_data["Volume"].iloc[-1]),
    }

    # the price of the stock over the past
    custom_data["price_data"] = []
    current_date = first_date 
    while current_date < last_date: 
        try: 
            given_date_price = recent_data["Adj Close"][to_string(current_date)]
            item_data = {
                "date": current_date, 
                "given_date_close": float(round(given_date_price, 2))
            }
            custom_data["price_data"].append(item_data)
        # the key error means that the price of stock on that date doesn't exist
        except KeyError: 
            pass
        current_date += timedelta(days=1) # increment the date

    # the date the price of the stock was updated 
    last_updated_date = custom_data["price_data"][-1]["date"]
    custom_data["last_updated_date"] = last_updated_date
    return custom_data


# update the info the stock, and add new record of the stock price 
def update_stock_data(symbol: str) -> Dict: 
    previous_date = to_string(date.today() - timedelta(days=1))
    today = to_string(date.today())
    
    # return the Panda data frame 
    updated_data = yf.download(symbol, start=previous_date, end=today)
    
    custom_data = {
        "new_close": round(Decimal(updated_data["Adj Close"].iloc[0]), 2), 
        "new_open": round(Decimal(updated_data["Open"].iloc[0]), 2), 
        "new_high": round(Decimal(updated_data["High"].iloc[0]), 2), 
        "new_low": round(Decimal(updated_data["Low"].iloc[0]), 2), 
        "new_volume": int(updated_data["Volume"].iloc[0])
    }
    return custom_data