from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from expenseapp.models import DateStockPrice, Stock, PortfolioValue
from expenseapp.serializers import PortfolioValueSerializer, StockSerializer, StockPriceSerializer
from expenseapp.finance import load_stock_data

# handling the list of stocks 
class StockList(APIView): 
    permission_classes = [IsAuthenticated]

    # get the response data 
    def get_response_data(self, request):
        stock_list = Stock.objects.filter(user=request.user)
        response_data = StockSerializer(stock_list, many=True).data
        return response_data
    
    # GET method, return the list of stock of the user 
    def get(self, request, format=None): 
        response_data = self.get_response_data(request)
        return Response(response_data)
    
    # POST method, add the stock the list of stock of user 
    @transaction.atomic
    def post(self, request, format=None): 
        request_data = request.data 
        request_data["user"] = request.user.pk
        symbol = request_data["symbol"]

        # load the price data of the stock with the given symbol 
        try: 
            stock_data = load_stock_data(symbol)
        except IndexError: # if the stock with the given symbol isn't found 
            return Response({"error": "No stock with the given symbol"}, status=status.HTTP_404_NOT_FOUND)
        
        stock_price_data = stock_data.pop("price_data")
        for data_field in list(stock_data.keys()): 
            request_data[data_field] = stock_data[data_field]

        # add to the list 
        new_stock_serializer = StockSerializer(data=request_data)
        if new_stock_serializer.is_valid(): 
            created_stock = new_stock_serializer.save() 

            # add all of the price of the stock
            stock_price_list = [] 
            for i in range(len(stock_price_data)): 
                stock_price_list.append(DateStockPrice(
                    stock=created_stock, date=stock_price_data[i]["date"], given_date_close=stock_price_data[i]["given_date_close"]
                ))
            DateStockPrice.objects.bulk_create(stock_price_list)

            # return the response data
            response_data = self.get_response_data(request)
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(new_stock_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# handling the price detail of the stock 
class StockPriceDetail(APIView): 
    permission_classes = [IsAuthenticated]

    def get_response_data(self, request, symbol): 
        stock = get_object_or_404(Stock, user=request.user, symbol=symbol)
        # list of prices of the stock 
        stock_price_list = stock.datestockprice_set.order_by("date")

        # response data 
        response_data = {
            "stock": StockSerializer(stock).data, 
            "price_list": {}
        }

        price_list = StockPriceSerializer(stock_price_list, many=True).data
        for price in price_list: 
            response_data["price_list"][price["date"]] = price["given_date_close"]
        return response_data
    
    # GET method, return the detail of the stock, including its list of price
    def get(self, request, symbol, format=None): 
        response_data = self.get_response_data(request, symbol)
        return Response(response_data)
    
    # PUT method, update the stock 
    def put(self, request, symbol, format=None): 
        request_data = request.data
        request_data["user"] = request.user.pk
        stock = get_object_or_404(Stock, user=request.user, symbol=symbol)

        updated_stock_serializer = StockSerializer(stock, data=request_data)
        if updated_stock_serializer.is_valid(): 
            updated_stock_serializer.save() 

            # return the response data
            response_data = self.get_response_data(request, symbol)
            return Response(response_data, status=status.HTTP_202_ACCEPTED)
        return Response(updated_stock_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # DELETE method, delete the stock 
    def delete(self, request, symbol, format=None): 
        stock = get_object_or_404(Stock, user=request.user, symbol=symbol)
        stock.delete()
        return Response({"message": "Stock deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    

class PortfolioValueList(APIView): 
    permission_classes = [IsAuthenticated] 

    def get(self, request, format=None): 
        # query the list of portfolios
        portfolio_value_list = PortfolioValue.objects.filter(user=request.user).order_by("date")
        original_data = PortfolioValueSerializer(portfolio_value_list, many=True).data 

        response_data = {}
        for data_item in original_data: 
            response_data[data_item["date"]] = data_item["given_date_value"]
        return Response(response_data)