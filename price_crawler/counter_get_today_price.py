# coding: utf-8

import requests
import json
from pymongo import MongoClient
import re
from datetime import datetime
import twstock as ts

time_format = "%Y/%m/%d"

ts_stock = ts.Stock('2330')

db = MongoClient()['Stock']
codeCollect = db['code']
priceCollect = db['price']

all_code = codeCollect.find_one({})['counterCode']


def pack_price(a_day):
    def toYear(year):    
        # 民國轉西元
        ss = year.split('/')
        year = str(int(ss[0]) + 1911)
        return f'{year}/{ss[1]}/{ss[2]}'
    
    try: date = datetime.strptime(toYear(a_day[0]), time_format)
    except: date = None
    
    try: open_price = float(re.sub(',', '', a_day[3]))
    except: open_price = None
        
    try: high = float(re.sub(',', '', a_day[4]))
    except: high = None
        
    try: low = float(re.sub(',', '', a_day[5]))
    except: low = None
    
    try: close = float(re.sub(',', '', a_day[6]))
    except: close = None
    
    try: volumn = float(re.sub(',', '', a_day[1]))
    except: volumn = None
    
    return {
        'date': date,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volumn': volumn
    }

def isStockInDB(code):
    return priceCollect.find({'code': code}).count() > 0

def updateMA(code):

    # get the latest 20 days history price
    this_stock_history = priceCollect.find_one({'code': code})['history']

    # append latest 20 days closing price
    all_close = []
    for this_day in this_stock_history[-20:]:
        all_close.append(this_day['close'])


    new_5MA = ts_stock.moving_average(all_close[-5:], 5)
    new_10MA = ts_stock.moving_average(all_close[-10:], 10)
    new_20MA = ts_stock.moving_average(all_close[-20:], 20)

    if len(new_5MA) > 0:
        new_5MA = new_5MA[0]
        priceCollect.update({'code': code}, {'$push': {
            'MA.MA_5': new_5MA,
        }})

    if len(new_10MA) > 0:
        new_10MA = new_10MA[0]
        priceCollect.update({'code': code}, {'$push': {
            'MA.MA_10': new_10MA,
        }})

    if len(new_20MA) > 0:
        new_20MA = new_20MA[0]
        priceCollect.update({'code': code}, {'$push': {
            'MA.MA_20': new_20MA,
        }})

total = 0

for code in all_code:
    url = f'http://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php?l=zh-tw&d=106/12&stkno={code}&_=1513094300431'
    res = requests.get(url)
    print(code)
    monthPrice = json.loads(res.text)['aaData']
    today_price = monthPrice[-1]

    a_day_price = pack_price(today_price)

    # 如果當日無收盤資料，就不將該筆存進DB
    if a_day_price['close'] is None: continue

    # insert DB
    if isStockInDB(code):
        priceCollect.update({'code': code}, {'$push': {
            'history': {
                '$each': [a_day_price],
                '$sort': {'date': 1}
            }
        }})

        updateMA(code)
    else:
        print(f"{code} not exist!")
        thisStock = {'code': code, 'history': [a_day_price]}
        priceCollect.insert_one(thisStock)

    total += 1

print(f'Total update: {total}')


