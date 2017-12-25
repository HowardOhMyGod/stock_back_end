from pymongo import MongoClient
from datetime import datetime
import os
import pprint

class BasicFilter:
    def __init__(self, risk_level):
        # db config
        client = MongoClient(os.environ['local_db'])
        db = client['Stock']

        # get collections
        self.basic_collect = db['basic']
        self.price_collect = db['price']

        # convert risk level
        self.risk_level = risk_level
        self.risk_level = self.convert_risk(self)

        # get all stocks from risk level
        self.stocks = self.basic_collect.find({
            'risk_level': self.risk_level
        } , {'_id': 0})


    @staticmethod
    def convert_risk(self):
        if self.risk_level == 'Low':
            return '1'
        elif self.risk_level == 'Mid':
            return '2'
        elif self.risk_level == 'High':
            return '3'
    @staticmethod
    def get_today_price(self, code):
        this_stock = self.price_collect.find_one({
            'code': code
        })

        close_price = this_stock['history'][-1]['close']
        today_date = this_stock['history'][-1]['date'].strftime("%Y/%m/%d")

        return close_price, today_date


    def pack_industry(self):
        all = {}
        for stock in self.stocks:
            type = stock['industry_type']
            stock['close'], stock['date'] = self.get_today_price(self, stock['code'])


            if type in all:
                all[type].append(stock)
            else:
                all[type] = []
                all[type].append(stock)

        return all

if __name__ == '__main__':
    filter = BasicFilter("Mid")
    all = filter.pack_industry()

    pp = pprint.PrettyPrinter(indent= 4)
    pp.pprint(all)


