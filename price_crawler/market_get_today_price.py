
# coding: utf-8
'''
功能: 把當日上市個股股價資料抓取並存進資料庫
資料來源: http://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL

資料庫schema: {
    'code': 2330,
    'history': [{
        'date',
        'open',
        'high',
        'low',
        'close',
        'volumn'
    }],
    'MA': {
        'MA_5': [],
        'MA_10': [],
        'MA_20': []
    }
}

邏輯:
1)獲取股價JSON
2)擷取出開高低收以及交易股(千)
3)檢查該股是否已存在資料庫
4)已存在: 將當日資料pack，push進該股的history，更新MA
5)不存在: 新增該股並push當日資料進history
'''


import requests
import time
from pymongo.mongo_client import MongoClient
from datetime import datetime
import pprint
import json
import re
import copy
import twstock as ts
import os

# in order to use move_average method
ts_stock = ts.Stock('2330')

# pretty print function
pp = pprint.PrettyPrinter(indent = 4)

# source and date format
url = 'http://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL'
time_format = "%Y%m%d"

# DateError when data has been saved
class DateError(Exception):
    pass

class MarketCrawler:
    def __init__(self, db_link = 'mongodb://localhost:27017/'):
        # db config stuff, and check if it's cloud db
        if '.com' in db_link:
            client = MongoClient(db_link)
            db = client.get_database()
        else:
            db = MongoClient(db_link)['Stock']

        # get code and price collection
        self.stockCollec = db['price']
        self.codeCollect = db['code']

        # check if today's data has been saved
        latest_save_date = self.stockCollec.find_one()['history'][-1]['date']

        # if saved, raise Error
        if latest_save_date == datetime.strptime(time.strftime(time_format), time_format):
            raise DateError(f"{latest_save_date}'s data has been saved!")

    # check if stock already in DB
    def isStockInDB(self, code):
        return self.stockCollec.find({'code': code}).count() > 0

    # parsing price from json
    def pack_price(self, stock, this_date):
        return {
            'date': datetime.strptime(this_date, time_format),
            'open': float(re.sub(',', '', stock[4])),
            'high': float(re.sub(',', '', stock[5])),
            'low': float(re.sub(',', '', stock[6])),
            'close': float(re.sub(',', '', stock[7])),
            'volumn': float(re.sub(',', '', stock[2])) // 1000
        }

    def updateMA(self, code):

        # get the latest 20 days history price
        this_stock_history = self.stockCollec.find_one({'code': code})['history']

        # append latest 20 days closing price
        all_close = []
        for this_day in this_stock_history[-20:]:
            all_close.append(this_day['close'])

        # append latest 5 days volumn
        all_volumn = []
        for this_day in this_stock_history[-5:]:
            all_volumn.append(this_day['volumn'])


        new_5MA = ts_stock.moving_average(all_close[-5:], 5)
        new_10MA = ts_stock.moving_average(all_close[-10:], 10)
        new_20MA = ts_stock.moving_average(all_close[-20:], 20)

        vol_5_ma = ts_stock.moving_average(all_volumn, 5)

        if len(new_5MA) > 0:
            new_5MA = new_5MA[0]
            self.stockCollec.update({'code': code}, {'$push': {
                'MA.MA_5': new_5MA,
            }})

        if len(new_10MA) > 0:
            new_10MA = new_10MA[0]
            self.stockCollec.update({'code': code}, {'$push': {
                'MA.MA_10': new_10MA,
            }})

        if len(new_20MA) > 0:
            new_20MA = new_20MA[0]
            self.stockCollec.update({'code': code}, {'$push': {
                'MA.MA_20': new_20MA,
            }})

        if len(vol_5_ma) == 1:
            vol_5_ma = vol_5_ma[0]
            self.stockCollec.update({'code': code}, {'$push': {
                'volumn_5_ma': vol_5_ma
            }})

    def start(self):
        # request and get stock price data, store in price_obj
        # get today data
        res = requests.get(url)
        dayObj = json.loads(res.text)
        price_obj = dayObj['data']

        # pp.pprint(price_obj)

        # get all market code from DB
        market_code = self.codeCollect.find_one({})['marketCode']

        # total stock update
        total = 0

        # loop through all stock price today and save to DB
        for i, stock in enumerate(price_obj):
            code = stock[0].rstrip()

            # exclude ETF
            if code not in market_code: continue

            if self.isStockInDB(code):
                thisPrice = self.pack_price(stock, dayObj['date'])
                self.stockCollec.update({'code': code}, {'$push': {
                    'history': {
                        '$each': [copy.deepcopy(thisPrice)],
                        '$sort': {'date': 1}
                    }}})

                self.updateMA(code)
            else:
                thisStock = {'code': code, 'history': [self.pack_price(stock)]}
                self.stockCollec.insert_one(copy.deepcopy(thisStock))

            # add total
            total += 1

        print(f'Total update: {total}')

if __name__ == '__main__':
    # mlab_link = os.environ['mlab_db_link']
    crawler = MarketCrawler()
    crawler.start()




