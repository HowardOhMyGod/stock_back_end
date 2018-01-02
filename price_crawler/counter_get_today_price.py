# coding: utf-8
'''
功能: 把當日上櫃個股股價資料抓取並存進資料庫
資料來源: http://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php?l=zh-tw&d=106/12&stkno={code}&_=1513094300431

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
- 從DB取出上櫃代碼，依這些代碼輸入URL開始抓取
- 獲取股價JSON
- 擷取出開高低收以及交易股
- 減收收盤價有沒有值，如果沒有此股就跳過以下步驟
- 檢查該股是否已存在資料庫
    - 已存在: 將當日資料pack，push進該股的history，更新MA
    - 不存在: 新增該股並push當日資料進history
'''


import requests
import json
from pymongo import MongoClient
import re
from datetime import datetime
import twstock as ts
import time
import os

time_format = "%Y/%m/%d"

ts_stock = ts.Stock('2330')

# DateError when data has been saved
class DateError(Exception):
    pass

class CounterCrawler:
    def __init__(self, db_link = os.environ['local_db']):

        db = MongoClient(db_link)['Stock']

        # get code and price collection
        self.codeCollect = db['code']
        self.priceCollect = db['price']

        # check if today's data has been saved
        latest_save_date = self.priceCollect.find_one({'code': '1258'})['history'][-1]['date']

        # if saved, raise Error
        if latest_save_date == datetime.strptime(time.strftime(time_format), time_format):
            raise DateError(f"{latest_save_date}'s data has been saved!")

        # 取得所有已存在DB的上櫃公司代碼
        self.all_code = self.codeCollect.find_one({})['counterCode']

        # 新增比數
        self.total = 0

    # 打包當日開高低收與交易張數
    def pack_price(self, a_day):
        def toYear(year):
            # 民國轉西元
            ss = year.split('/')
            year = str(int(ss[0]) + 1911)
            return f'{year}/{ss[1]}/{ss[2]}'

        # 檢查各input值是否不為空值，或是字串
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

    # 檢查該股是否已存在於DB
    def isStockInDB(self, code):
        return self.priceCollect.find({'code': code}).count() > 0

    # 在history增加新一天的股價資料後，必須更新該股的MA List
    def updateMA(self, code):

        # get the latest 20 days history price
        this_stock_history = self.priceCollect.find_one({'code': code})['history']

        # append latest 20 days closing price
        all_close = []
        for this_day in this_stock_history[-20:]:
            all_close.append(this_day['close'])

        # append latest 5 days volumn
        all_volumn = []
        for this_day in this_stock_history[-5:]:
            all_volumn.append(this_day['volumn'])

        # compute MA
        new_5MA = ts_stock.moving_average(all_close[-5:], 5)
        new_10MA = ts_stock.moving_average(all_close[-10:], 10)
        new_20MA = ts_stock.moving_average(all_close[-20:], 20)

        vol_5_ma = ts_stock.moving_average(all_volumn, 5)

        # 檢查該股是否有足夠天數計算MA，如果沒有上面回傳的List會是空值，就不跟新MA list
        if len(new_5MA) > 0:
            new_5MA = new_5MA[0]
            self.priceCollect.update({'code': code}, {'$push': {
                'MA.MA_5': new_5MA,
            }})

        if len(new_10MA) > 0:
            new_10MA = new_10MA[0]
            self.priceCollect.update({'code': code}, {'$push': {
                'MA.MA_10': new_10MA,
            }})

        if len(new_20MA) > 0:
            new_20MA = new_20MA[0]
            self.priceCollect.update({'code': code}, {'$push': {
                'MA.MA_20': new_20MA,
            }})

        if len(vol_5_ma) == 1:
            vol_5_ma = vol_5_ma[0]
            self.priceCollect.update({'code': code}, {'$push': {
                'volumn_5_ma': vol_5_ma
            }})

    # 擷取股價主程式
    def start(self):
        def get_year_month():
            year = datetime.strftime(datetime.now(),"%Y")
            month = datetime.strftime(datetime.now(),"%m")
            year = int(year) - 1911

            return year, month

        year, month = get_year_month()

        for code in self.all_code:
            url = f'http://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php?l=zh-tw&d={year}/{month}&stkno={code}&_=1513094300431'
            res = requests.get(url)
            print(code)

            # 取得所有股票資料陣列
            monthPrice = json.loads(res.text)['aaData']

            # 選取最新一天的股價
            try:
                today_price = monthPrice[-1]
            except:
                print(f"{code}: no price.")
                continue

            # 打包成DB 格式
            a_day_price = self.pack_price(today_price)

            # 如果當日無收盤資料，就不將該筆存進DB，MA計算將不包含到該日
            if a_day_price['close'] is None: continue

            ## insert DB ##
            # 該股已存在DB
            if self.isStockInDB(code):
                self.priceCollect.update({'code': code}, {'$push': {
                    'history': {
                        '$each': [a_day_price],
                        '$sort': {'date': 1}
                    }
                }})

                # history 加入最近一日股價後，更新MA
                self.updateMA(code)
                self.total += 1

            # 該股不存在DB
            else:
                print(f"{code} not exist!")

                # 新增該股的document並寫入
                thisStock = {'code': code, 'history': [a_day_price]}
                self.priceCollect.insert_one(thisStock)


if __name__ == '__main__':
    crawler = CounterCrawler()
    crawler.start()
    print('Total update: ', crawler.total)
