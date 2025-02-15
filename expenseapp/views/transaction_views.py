from django.http import Http404
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.validators import ValidationError
from expenseapp.models import Account, Transaction
from expenseapp.serializers import TransactionSerializer
from expenseapp.finance import get_current_dates
from datetime import date
from calendar import monthrange
from expenseapp.finance import adjust_account_balance

# TODO: ADD PAGINATION

# base transaction view to handle pagination 
class TransactionView(APIView): 
    permission_classes = [IsAuthenticated]


# handling the list of transactions of the user 
class UserTransactionList(APIView): 
    permission_classes = [IsAuthenticated]

    # get custom data as a response to the API 
    def get_response_data(self, request):
        # query and serialize the transaction list 
        transaction_list = Transaction.objects.filter(user=request.user).order_by("-occur_date")[:20]
        response_data = TransactionSerializer(transaction_list, many=True).data
        return response_data
    
    # GET method, return the list of 15 latest transactions 
    def get(self, request, format=None): 
        response_data = self.get_response_data(request)
        return Response(response_data)
    
    # POST method, create new transaction
    def post(self, request, format=None): 
        new_trans_serializer = TransactionSerializer(data=request.data)
        if new_trans_serializer.is_valid(): 
            new_transaction = new_trans_serializer.save() # call the create method 

            # adjust balance of the associated account 
            adjust_account_balance(new_transaction.account, new_transaction)

            response_data = self.get_response_data(request)
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(new_trans_serializer.errors, status = status.HTTP_400_BAD_REQUEST)


"""
view to handle the list of transactions between 2 given dates in the endpoints 
requires pagination 
params: first_date, last_date 
"""
class IntervalTransactionList(TransactionView): 

    def get(self, request, format=None): 
        # get the params 
        arg_first_date = request.query_params.get("first_date")
        arg_last_date = request.query_params.get("last_date")

        # validate 
        if arg_first_date is None or arg_last_date is None: 
            raise ValidationError({"message": "First date or last date unspecified"})
        
        # convert string to actual date obj
        first_date_list = arg_first_date.split("-")
        last_date_list = arg_last_date.split("-")

        first_date = date(int(first_date_list[0]), int(first_date_list[1]), int(first_date_list[2]))
        last_date = date(int(last_date_list[0]), int(last_date_list[1]), int(last_date_list[2]))

        # list of transactions between 2 dates 
        transaction_list = Transaction.objects.filter(
            user=request.user, 
            occur_date__gte=first_date, occur_date__lte=last_date).order_by("-occur_date")

        # return serialized data
        return Response(TransactionSerializer(transaction_list, many=True).data)
    

"""
view to handle the list of latest transactions in each category for the user 
requires pagination 
"""
class CategoryTransactionList(TransactionView): 

    def get(self, request, arg_cat, format=None): 
        # get query param and validate 
        if arg_cat is None: 
            raise ValidationError({"error": "Category not specified"})

        first_date, last_date = get_current_dates(period_type="month")

        transaction_list = Transaction.objects.filter(
            user=request.user, category=arg_cat,
            occur_date__gte=first_date, occur_date__lte=last_date).order_by("-occur_date")
        
        # serialized data 
        return Response(TransactionSerializer(transaction_list, many=True).data)
    

"""
views to handle list of transactions of category between 2 dates
requires pagination 
params: first_date, last_date, category
""" 
class BothTransactionList(TransactionView): 

    def get(self, request, format=None): 
        # get the query params and validate 
        category = request.query_params.get("category")
        if category is None: 
            raise ValidationError({"message": "Category not specified"})

        arg_first_date = request.query_params.get("first_date")
        arg_last_date = request.query_params.get("last_date")

        if arg_first_date is None or arg_last_date is None: 
            raise ValidationError({"message": "first date or last date not specified"})
        
        # process 
        first_date_list = arg_first_date.split("-")
        last_date_list = arg_last_date.split("-")

        first_date = date(int(first_date_list[0]), int(first_date_list[1]), int(first_date_list[2]))
        last_date = date(int(last_date_list[0]), int(last_date_list[1]), int(last_date_list[2]))

        transaction_list = Transaction.objects.filter(
            user=request.user, category=category, 
            occur_date__gte=first_date, occur_date__lte=last_date).order_by("-occur_date")
        
        return Response(TransactionSerializer(transaction_list, many=True).data)


# view to handle the 20 latest transactions of the account
class AccountTransactionList(generics.ListAPIView): 
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queried_account = get_object_or_404(Account, pk=self.kwargs["pk"])
        return Transaction.objects.filter(account=queried_account).order_by("-occur_date")[:20]
    

"""
handling the list of latest transactions in each category for the account
requires pagination 
params: category
"""
class AccBothTransactionList(TransactionView): 

    def get(self, request, pk, format=None):
        arg_category = request.query_params.get("category")
        if arg_category is None: 
            raise ValidationError({"error": "Category not specified"})
        
        queried_account = get_current_dates(Account, pk=pk)
        
        # the list of transactions with picked category 
        first_date, last_date = get_current_dates(period_type="month")

        transaction_list = Transaction.objects.filter(
            account=queried_account, category=arg_category, 
            occur_date__gte=first_date, occur_date__lte=last_date).order_by("-occur_date")
        
        return Response(TransactionSerializer(transaction_list, many=True).data)