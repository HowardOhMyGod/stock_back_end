from pymongo import MongoClient
import os
import pprint

class BasicFilter:
    def __init__(self, risk_level):
        # db config
        client = MongoClient(os.environ['local_db'])
        db = client['Stock']
        self.basic_collect = db['basic']

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

    def pack_industry(self):
        all = {}
        for stock in self.stocks:
            type = stock['industry_type']

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


