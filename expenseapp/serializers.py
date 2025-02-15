from .models import User
from . import models
from rest_framework.serializers import ValidationError as DRFValidationError
from rest_framework import serializers, fields
import json

class RegisterSerializer(serializers.ModelSerializer): 
    class Meta: 
        model = models.User
        fields = ["first_name", "last_name", "email address", "username", "password", "password_again"]

    # field of second password 
    # TODO: what is the write_only parameters ?
    password_again = serializers.CharField(max_length=20, required=True, write_only=True)

    # validate if 2 passwords the user entered match each other 
    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_again'): 
            raise DRFValidationError({"password": "2 passwords don't match."})
        return attrs

    # create the new user with the given validated info 
    def create(self, validated_data): 
        validated_data.pop("password_again")
        password = validated_data.pop("password")
        created_user = User.objects.create(**validated_data)

        # built-in method to hash the password of the user 
        created_user.set_password(password)
        created_user.save()
        return created_user


# the serializer of the account 
class AccountSerializer(serializers.ModelSerializer): 
    class Meta: 
        model = models.Account 
        fields = "__all__"

    # overidding the representation of the date field 
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation["due_date"]:
            representation["due_date"] = instance.due_date.strftime("%m/%d/%Y")
        return representation


# the serializer of the transaction 
class TransactionSerializer(serializers.ModelSerializer): 
    class Meta: 
        model = models.Transaction
        exclude = ["user"] 

    # create the account objects given the validated data
    def create(self, validated_data): 
        # create the transaction with the associated user, and account 
        account = validated_data.pop("account")
        user = account.user
        transaction = models.Transaction.objects.create(user=user, account=account, **validated_data)
        return transaction 

    # overidding the representation of the datetime field 
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["account_name"] = instance.account.name
        representation.pop("account")
        representation["occur_date"] = instance.occur_date.strftime("%m/%d/%Y")
        return representation


# the serializer of the budget plan
class BudgetPlanSerializer(serializers.ModelSerializer): 
    class Meta: 
        model = models.BudgetPlan
        fields = "__all__"

    # update the account instance given the validated data from json 
    def update(self, instance, validated_data): 
        # only update if the instance and validated data has the same interval type
        if instance.interval_type != validated_data["interval_type"]: 
            raise DRFValidationError({
                "message": "The data has different interval type. Can't update."
            })

        instance.recurring_income = validated_data.get("recurring_income", instance.recurring_income)
        instance.portion_for_expense = validated_data.get("portion_for_expense", instance.portion_for_expense)
        
        # update the JSON
        for category in list(validated_data["category_portion"].keys()): 
            instance.category_portion[category] = validated_data["category_portion"][category]

        instance.save()
        # call the original update() method 
        return instance
    

# the serializer of the bills 
class BillSerializer(serializers.ModelSerializer): 
    class Meta: 
        model = models.Bill
        fields = "__all__"

    # overidding the representation of the datetime field 
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["due_date"] = instance.due_date.strftime("%m/%d/%Y")
        representation["pay_account_name"] = instance.pay_account.name
        return representation
    

# the serializer of the overdue bill message 
class OverdueBillMessageSerializer(serializers.ModelSerializer): 
    class Meta: 
        model = models.OverdueBillMessage
        exclude = ["appear_date"] 

    def to_representation(self, instance):
        representation =  super().to_representation(instance)
        representation["bill_due_date"] = instance.bill_due_date.strftime("%m/%d/%Y")
        return representation
    

# the serializer of the price of stock on each date 
class StockPriceSerializer(serializers.ModelSerializer): 
    class Meta:
        model = models.DateStockPrice
        fields = "__all__"

    def to_representation(self, instance):
        representation =  super().to_representation(instance)
        representation["date"] = instance.date.strftime("%m/%d/%Y")
        return representation


# serializer of the stock 
class StockSerializer(serializers.ModelSerializer): 
    class Meta: 
        model = models.Stock
        fields = "__all__"

    # restrict the field the user can update 
    def update(self, instance, validated_data): 
        # the user can't update 
        if validated_data["symbol"] != instance.symbol: 
            raise DRFValidationError("The data has different symbol. Can't update.")
        return super().update(instance, validated_data)

    # add change between 2 closes 
    def to_representation(self, instance):
        representation =  super().to_representation(instance)
        # change percentage from the previous close to the current close 
        representation.pop("previous_close")
        change = (instance.current_close - instance.previous_close) 
        representation["change"] = '{0:.2f}'.format(change)

        # change format of the date
        representation["last_updated_date"] = instance.last_updated_date.strftime("%m/%d/%Y")
        return representation
    

# serializer of the value of the porfolio
class PortfolioValueSerializer(serializers.ModelSerializer): 
    class Meta: 
        model = models.PortfolioValue
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["date"] = instance.date.strftime("%m/%d/%Y")
        return representation