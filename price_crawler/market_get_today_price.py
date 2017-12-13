
# coding: utf-8
'''
功能: 把當日個股股價資料抓取並存進資料庫
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

# in order to use move_average method
ts_stock = ts.Stock('2330')

# pretty print function
pp = pprint.PrettyPrinter(indent = 4)

# source and date format
url = 'http://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL'
time_format = "%Y%m%d"


# db config
db = MongoClient()['Stock']
stockCollec = db['price']
codeCollect = db['code']

# check if stock already in DB
def isStockInDB(code):
    return stockCollec.find({'code': code}).count() > 0

# parsing price from json
def pack_price(stock):
    return {
        'date': datetime.strptime(today, time_format),
        'open': float(re.sub(',', '', stock[4])),
        'high': float(re.sub(',', '', stock[5])),
        'low': float(re.sub(',', '', stock[6])),
        'close': float(re.sub(',', '', stock[7])),
        'volumn': float(re.sub(',', '', stock[2])) // 1000
    }

def updateMA(code):

    # get the latest 20 days history price
    this_stock_history = stockCollec.find_one({'code': code})['history']

    # append latest 20 days closing price
    all_close = []
    for this_day in this_stock_history[-20:]:
        all_close.append(this_day['close'])


    new_5MA = ts_stock.moving_average(all_close[-5:], 5)
    new_10MA = ts_stock.moving_average(all_close[-10:], 10)
    new_20MA = ts_stock.moving_average(all_close[-20:], 20)

    if len(new_5MA) > 0:
        new_5MA = new_5MA[0]
        stockCollec.update({'code': code}, {'$push': {
            'MA.MA_5': new_5MA,
        }})

    if len(new_10MA) > 0:
        new_10MA = new_10MA[0]
        stockCollec.update({'code': code}, {'$push': {
            'MA.MA_10': new_10MA,
        }})

    if len(new_20MA) > 0:
        new_20MA = new_20MA[0]
        stockCollec.update({'code': code}, {'$push': {
            'MA.MA_20': new_20MA,
        }})

# request and get stock price data, store in price_obj
res = requests.get(url)
dayObj = json.loads(res.text)
today = dayObj['date']
price_obj = dayObj['data']

# pp.pprint(price_obj)

# get all market code from DB
market_code = codeCollect.find_one({})['marketCode']

# total stock update
total = 0

# loop through all stock price today and save to DB
for i, stock in enumerate(price_obj):
    code = stock[0].rstrip()

    # exclude ETF
    if code not in market_code: continue
    
    if isStockInDB(code):
        thisPrice = pack_price(stock)
        stockCollec.update({'code': code}, {'$push': {
            'history': {
                '$each': [copy.deepcopy(thisPrice)],
                '$sort': {'date': 1}
            }}})

        updateMA(code)
    else:
        thisStock = {'code': code, 'history': [pack_price(stock)]}
        stockCollec.insert_one(copy.deepcopy(thisStock))

    # add total
    total += 1

print(f'Total update: {total}')




