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
import re
from datetime import datetime
from crawler import PriceCrawler


def get_year_month():
    year = datetime.strftime(datetime.now(), "%Y")
    month = datetime.strftime(datetime.now(), "%m")
    year = int(year) - 1911

    return year, month


def date_format(date):
    # 民國轉西元
    ss = date.split('/')
    date = str(int(ss[0]) + 1911)

    return f'{date}/{ss[1]}/{ss[2]}'

class CounterCrawler(PriceCrawler):
    def __init__(self):

        # 初始化 Parent
        super().__init__()

        # 取得所有已存在DB的上櫃公司代碼
        self.counter_codes = self.code_clt.find_one({})['counterCode']

    # 打包當日開高低收與交易張數
    def pack_price(self, a_day):

        # 檢查各input值是否不為空值，或是字串
        try: date = datetime.strptime(date_format(a_day[0]), self.time_format)
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

    def request(self, code):
        year, month = get_year_month()

        url = f'http://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php?l=zh-tw&d={year}/{month}&stkno={code}&_=1513094300431'
        res = requests.get(url)
        print(code)

        # 取得所有股票資料陣列
        this_month_price = json.loads(res.text)['aaData']

        return this_month_price


    def get_today_price(self, code):
        this_month_price = self.request(code)

        try:
            today_price = this_month_price[-1]

        except IndexError:
            return None

        else:
            return today_price

    # 擷取股價主程式
    def start(self):

        for code in self.counter_codes:
            # 判斷此股是否已經存有今日資料
            if super().is_saved(code):
                print(f'{code} today price has been saved!')
                continue

            # request 今日價格
            today_price = self.get_today_price(code)

            # continue if no today price
            if not today_price: continue

            # 打包成DB 格式
            today_price = self.pack_price(today_price)

            # 如果當日無收盤資料，就不將該筆存進DB，MA計算將不包含到該日
            if today_price['close'] is None: continue

            # 更新此股價格，同事會更新5MA 10MA 20MA，交易量5MA
            super().update_price(code, today_price)


if __name__ == '__main__':
    crawler = CounterCrawler()
    crawler.start()
    print('Total update: ', crawler.total)
