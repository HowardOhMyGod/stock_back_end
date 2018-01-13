from pymongo import MongoClient
from mymodule.module import load_module
import os
import pprint

mongodb = load_module(os.path.dirname(__name__), '../db', 'mongodb')

class dbError(Exception):
    pass

'''
回傳Highchart 繪圖需要的資料格式
input: 股瞟代碼
output: 該股裡使股價陣列
'''
class Price:
    def __init__(self, code):
        self.code = code

        # db config
        db = mongodb.Mongo.connect('Stock')

        self.__price_collect = db['price']

        if self.code_in_db():
            self.history = self.__price_collect.find_one({'code': code})['history']
        else:
            raise dbError("Code is not found!")

    def code_in_db(self):
        return self.__price_collect.find({'code': self.code}).count() > 0

    def pack_price(self, this_date):
        this = []
        this.append(this_date['date'].timestamp() * 1000)
        this.append(this_date['open'])
        this.append(this_date['high'])
        this.append(this_date['low'])
        this.append(this_date['close'])
        this.append(this_date['volumn'])

        return this

    def return_price(self):
        all_data = []

        for this_date in self.history:
            this = self.pack_price(this_date)
            all_data.append(this)

        return all_data

if __name__ == '__main__':
    pp = pprint.PrettyPrinter(indent= 4)
    p = Price('308')
    data = p.return_price()

    pp.pprint(data)