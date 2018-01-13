
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

from datetime import datetime
from crawler import PriceCrawler

import requests
import json
import re

class MarketCrawler(PriceCrawler):
    url = 'http://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL'
    src_time_format = "%Y%m%d"

    # parsing price from json
    def pack_price(self, a_day):
        return {
            'date': datetime.strptime(self.today_date, self.src_time_format),
            'open': float(re.sub(',', '', a_day[4])),
            'high': float(re.sub(',', '', a_day[5])),
            'low': float(re.sub(',', '', a_day[6])),
            'close': float(re.sub(',', '', a_day[7])),
            'volumn': float(re.sub(',', '', a_day[2])) // 1000
        }

    def request(self):
        # request and get stock price data, store in price_obj

        # get today data
        res = requests.get(self.url)

        day_obj = json.loads(res.text)
        self.today_date = day_obj['date']

        all_stocks = day_obj['data']

        return all_stocks

    def start(self):
        # get all market code from DB
        market_code = self.code_clt.find_one({})['marketCode']

        all_stocks = self.request()

        # loop through all stock price today and save to DB
        for i, stock in enumerate(all_stocks):
            code = stock[0].rstrip()
            print(code)

            # exclude ETF
            if code not in market_code: continue
            if super().is_saved(code):
                print(f'{code} today price has been saved!')
                continue

            today_price = self.pack_price(stock)

            super().update_price(code, today_price)

        # close the collection cursors
        self.price_clt.close()
        self.code_clt.close()

if __name__ == '__main__':
    crawler = MarketCrawler()
    crawler.start()
    print(f'Total update: {crawler.total}')




