from db.mongodb import Mongo
from datetime import datetime
import twstock as ts
import time


class PriceCrawler:
    try:
        ts_stock = ts.Stock('2330')

    except Exception:
        raise TwStockError("twstock module fail...")

    time_format = "%Y/%m/%d"

    def __init__(self):
        db = Mongo.connect('Stock')

        self.code_clt = db['code']
        self.price_clt = db['price']

        self.total = 0
        self.today_date = None

    def is_saved(self, code):
        latest_save_time = self.price_clt.find_one({'code': code})['history'][-1]['date']

        if latest_save_time == datetime.strptime(time.strftime(self.time_format), self.time_format):
            return True

    def is_stock_in_price(self, code):
        return Mongo.is_in_collection(self.price_clt, {'code': code})

    def get_20_close(self, code):
        # get the latest 20 days history price
        this_stock_history = self.price_clt.find_one({'code': code})['history']

        # append latest 20 days closing price
        all_close = []
        for this_day in this_stock_history[-20:]:
            all_close.append(this_day['close'])

        return all_close

    def get_5_volumn(self, code):
        # get the latest 20 days history price
        this_stock_history = self.price_clt.find_one({'code': code})['history']

        # append latest 5 days volumn
        all_volumn = []
        for this_day in this_stock_history[-5:]:
            all_volumn.append(this_day['volumn'])

        return all_volumn

    def calc_ma(self, close_list, volumn_list):
        # compute MA
        new_5MA = self.ts_stock.moving_average(close_list[-5:], 5)
        new_10MA = self.ts_stock.moving_average(close_list[-10:], 10)
        new_20MA = self.ts_stock.moving_average(close_list[-20:], 20)

        vol_5_ma = self.ts_stock.moving_average(volumn_list, 5)

        return new_5MA, new_10MA, new_20MA, vol_5_ma

    # 在history增加新一天的股價資料後，必須更新該股的MA List
    def update_ma(self, code):
        close_20_day = self.get_20_close(code)
        volumn_5_day = self.get_5_volumn(code)

        new_5MA, new_10MA, new_20MA, vol_5_ma = self.calc_ma(close_20_day, volumn_5_day)

        # 檢查該股是否有足夠天數計算MA，如果沒有上面回傳的List會是空值，就不跟新MA list
        if len(new_5MA) > 0:
            new_5MA = new_5MA[0]
            self.price_clt.update_one({'code': code}, {'$push': {
                'MA.MA_5': new_5MA,
            }})

        if len(new_10MA) > 0:
            new_10MA = new_10MA[0]
            self.price_clt.update_one({'code': code}, {'$push': {
                'MA.MA_10': new_10MA,
            }})

        if len(new_20MA) > 0:
            new_20MA = new_20MA[0]
            self.price_clt.update_one({'code': code}, {'$push': {
                'MA.MA_20': new_20MA,
            }})

        if len(vol_5_ma) == 1:
            vol_5_ma = vol_5_ma[0]
            self.price_clt.update_one({'code': code}, {'$push': {
                'volumn_5_ma': vol_5_ma
        }})

    def update_price(self, code, today_price):
        if self.is_stock_in_price(code):
            self.price_clt.update_one({'code': code}, {'$push': {
                'history': {
                    '$each': [today_price],
                    '$sort': {'date': 1}
                }
            }})

            self.update_ma(code)
            self.total += 1

        else:
            this_stock = {'code': code, 'history': [today_price]}
            self.price_clt.insert_one(this_stock)


class TwStockError(Exception):
    pass

if __name__ == '__main__':
    crawler = PriceCrawler()
    print(crawler.is_stock_in_price('230'))