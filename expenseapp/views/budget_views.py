from django.http import Http404
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from expenseapp.models import BudgetPlan, OverdueBillMessage, Transaction, Bill
from expenseapp.serializers import BudgetPlanSerializer, BillSerializer, OverdueBillMessageSerializer
from expenseapp.finance import get_budget_response_data, adjust_account_balance
from datetime import date, datetime

# handling the budget plan of the user 
class UserBudget(APIView): 
    permission_classes = [IsAuthenticated]

    def get_response_data(self, request): 
        # query and serialize the user 
        response_data = {"month": {}, "bi_week": {}, "week": {}}
        for time_type in list(response_data.keys()): 
            response_data[time_type] = get_budget_response_data(request.user, time_type)
        return response_data
    
    # GET method 
    def get(self, request, format=None): 
        response_data = self.get_response_data(request)
        return Response(response_data)
    
    # POST method 
    def post(self, request, format=None): 
        request_data = request.data
        request_data["user"] = request.user.pk
        new_plan_serializer = BudgetPlanSerializer(data=request_data)

        if new_plan_serializer.is_valid(): 
            new_plan_serializer.save() # call the create method 

            # return new budget plan
            response_data = self.get_response_data(request)
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(new_plan_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# handling the the budget plan of each interval type 
class UserBudgetDetail(APIView): 
    permission_classes = [IsAuthenticated]

    def get_budget_plan(self, request, interval_type): 
        # query the user and check if the user has plan of this type
        try: 
            selected_budget_plan = request.user.budgetplan_set.get(interval_type=interval_type)
        except BudgetPlan.DoesNotExist: 
            raise Http404("Budget plan with given type doesn't exist.")
        
        # return the plane
        return selected_budget_plan
    
    # GET method, just return the plan of the given interval type
    def get(self, request, interval_type, format=None): 
        response_data = get_budget_response_data(request.user, interval_type)
        return Response(response_data)
    
    # PUT method, update the plan of the given interval type 
    def put(self, request, interval_type, format=None): 
        request_data = request.data
        request_data["user"] = request.user.pk
        budget_plan = self.get_budget_plan(request, interval_type)
        updated_plan_serializer = BudgetPlanSerializer(budget_plan, data=request_data)
    
        if updated_plan_serializer.is_valid(): 
            updated_plan_serializer.save() # call update() method 

            # custom data to be returned 
            custom_data = {"month": {}, "bi_week": {}, "week": {}}
            for time_type in list(custom_data.keys()): 
                custom_data[time_type] = get_budget_response_data(request.user, time_type)

            return Response(custom_data, status=status.HTTP_202_ACCEPTED)
        return Response(updated_plan_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # DELETE method, delete the plan 
    def delete(self, request, interval_type, format=None): 
        budget_plan = self.get_budget_plan(request, interval_type)
        budget_plan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# handling the list of bills of the user 
class BillList(APIView): 
    # get the response data 
    def get_response_data(self, request):
        bills_list = Bill.objects.filter(user=request.user)
        response_data = BillSerializer(bills_list, many=True).data
        return response_data 
    
    # GET method, return list of bills for the user 
    def get(self, request, format=None): 
        response_data = self.get_response_data(request)
        return Response(response_data)
    
    # POST method, add new bill to the list of bills 
    def post(self, request, format=None): 
        request_data = request.data
        request_data["user"] = request.user.pk
        new_bill_serializer = BillSerializer(data=request_data)
        if new_bill_serializer.is_valid(): 
            new_bill_serializer.save() # call the create() method 

            # return the new list of bills 
            response_data = self.get_response_data(request)
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(new_bill_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# handling the detail of the bills 
class BillsDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BillSerializer

    # get object and the serializer class 
    def get_object(self):
        try: 
            return Bill.objects.get(pk=self.kwargs["pk"])
        except Bill.DoesNotExist: 
            raise Http404("Bill with the given pk not found.")

    # overriding the destroying behavior 
    def perform_destroy(self, instance):
        # if there is pay account and the bills isn't overdue yet
        if instance.pay_account != None and instance.due_date >= date.today():
    
            # create transactions indicating that user's paid the bills 
            new_transaction = Transaction.objects.create(
                account=instance.pay_account, user=instance.user, 
                description=f"Payment: {instance.description}", category=instance.category,
                amount=instance.amount, occur_date=datetime.now()
            )
            # adjust the account 
            adjust_account_balance(new_transaction.account, new_transaction)

        # destroy the bills 
        instance.delete()


class OverdueMessageList(APIView): 
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None): 
        overdue_message_list = OverdueBillMessage.objects.filter(user=request.user)
        response_data = OverdueBillMessageSerializer(overdue_message_list, many=True).data
        return Response(response_data)
    