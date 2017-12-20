
# coding: utf-8

from pymongo import MongoClient
import os

'''
功能: 檢查該股當日交易資料是否符合均線糾結，向上突破的特徵
物件參數: 該股documet
回傳值: True or False
'''
class TechChecker:
    def __init__(self, stock, options = None):
        # 取得該股最近一天的交易資訊
        self.latest_prcie = stock['history'][-1]

        # 取得該股MA
        self.MA = stock['MA']

        # 取得該股vlolumn_5MA
        self.today_volumn_5ma = stock['volumn_5_ma'][-1]

        # 使用者選擇的options
        self.user_opt = options

        # 預設的篩選條件
        self.options = {
            'k_size': 0.07,
            'up_size': 0,
            'sticky_days': 10,
            'volumn_big': 2,
            'volumn_size': 500
        }

        # 取得指定天數的5, 10, 20 MA, 格式: tuple(5_ma[back_days], 10_ma[back_days], 20_ma[back_days])
        self.ma_list = self.get_ma_list(self.MA)

    '''設定篩選參數，如果self.user_opt不為None，將self.options更新為使用者的設定'''
    def set_options(self):
        if self.user_opt is None: return
        else:
            for option, value in self.user_opt.items():
                if option in self.options and value is not None:
                    self.options[option] = value

    '''取得近期特定天數的MA tuple'''
    def get_ma_list(self, MA):
        day = self.options['sticky_days']

        mv_5_3d = MA['MA_5'][-day:]
        mv_10_3d = MA['MA_10'][-day:]
        mv_20_3d = MA['MA_20'][-day:]

        #  檢查該股資料有沒有齊全，沒有回傳None，主程式會跳過此股
        if len(mv_5_3d) != day or len(mv_10_3d) != day or len(mv_20_3d) != day:
            return None

        return (mv_5_3d, mv_10_3d, mv_20_3d)

    '''檢查糾結: input: MA list, 三日的MA差距'''
    def is_sticky(self, mv_list, cond_1=1, cond_2=1, cond_3=1, cond_4 = 1):
        day = self.options['sticky_days']

        first = abs(mv_list[1][-1] - mv_list[0][-1])  # 10MA - 5MA
        second = abs(mv_list[1][-day] - mv_list[0][-day])  # 10MA - 5MA
        third = abs(mv_list[1][-day] - mv_list[2][-day])  # 10MA - 5MA
        forth = abs(mv_list[0][-5] - mv_list[1][-5])  # 5MA - 10MA
        five = abs(mv_list[0][-7] - mv_list[1][-7])
        six = abs(mv_list[0][-3] - mv_list[1][-3])

        return (first <= cond_1 and second <= cond_2
                and third <= cond_3 and forth <= cond_4 and five <= 1 and six <= 1)

    '''K棒大小: close/open -1'''
    def is_k_size(self, latest_price):
        size = self.options['k_size']

        return ((latest_price['close'] / latest_price['open']) - 1) >= size

    '''高價與收盤價距離'''
    def is_HC_range(self, latest_prcie):
        dis = self.options['up_size']

        return latest_prcie['high'] - latest_prcie['close'] <= dis

    '''成交量大小範圍'''
    def is_volumn(self, volumn, today_vol_5ma):
        bigger_than = self.options['volumn_big']
        bigger_size = self.options['volumn_size']

        return (volumn / today_vol_5ma >= bigger_than and
                volumn >= bigger_size)

    '''收盤大於5MA'''
    def is_close_big_than_5MA(self, latest_prcie, today_5MA):
        return latest_prcie['close'] > today_5MA

    '''檢查上彎5MA'''
    def is_up_5ma(self, ma_list):
        return ma_list[0][-1] > ma_list[0][-2]

    '''檢查主程式'''
    def is_break(self):
        # 缺少MA資料，跳過此股
        if self.ma_list is None: return False

        # 設定options
        self.set_options()

        return (self.is_sticky(self.ma_list) and
                self.is_k_size(self.latest_prcie) and
                self.is_close_big_than_5MA(self.latest_prcie, self.ma_list[0][-1]) and
                self.is_HC_range(self.latest_prcie) and
                self.is_volumn(self.latest_prcie['volumn'], self.today_volumn_5ma) and
                self.is_up_5ma(self.ma_list))


'''
功能: 檢查資料庫每支股票是否有符合技術新特徵
start完後內部資料:
pass_company: list of stock dict (符合特徵之股票代碼，名稱，當日收盤價)
lost_company: list of stock code (有缺少資料之股票代碼)
'''

class CheckStarter:
    def __init__(self, options = None):
        self.pass_company = []
        self.lost_company = []

        db_link = os.environ['local_db']
        # get price collections
        priceCollect = MongoClient(db_link)['Stock']['price']

        # get all stock document in price
        self.__stocks = priceCollect.find({})

        # user input options, pass to TechChecker
        self.options = options

    def start(self):
        for stock in self.__stocks:
            try:
                stock_check = TechChecker(stock, self.options)

                # add stock code, name, close_price as dict to pass list
                if stock_check.is_break():
                    self.pass_company.append({
                        'name': stock['name'],
                        'code': stock['code'],
                        'today_close_price': stock_check.latest_prcie['close']
                    })

            except Exception as e:
                # print(e)
                self.lost_company.append(stock['code'])

        # close cursor
        self.__stocks.close()

if __name__ == '__main__':
    checker = CheckStarter({'k_size': 0.06})
    checker.start()

    print(f"Pass Company: {checker.pass_company}")
    print(f"Lost Company: {checker.lost_company}, count: {len(checker.lost_company)}")

