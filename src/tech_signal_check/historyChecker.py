
from pymongo import MongoClient
import pprint
import os

total_rate = 0
trade_num = 0
win = 0
pos_rate = 0
pos_num = 0
na_rate = 0
na_num = 0

class HisChecker:
    def __init__(self, stock, options = None):
        # 取得在該股歷史資料中，第20天(包含)之後的資料
        self.test_days = stock['history'][19:]

        self.MA = stock['MA']
        self.code = stock['code']

        # 取得在該股歷史資料中，第20天(包含)之後的volumn_5_ma
        self.volumn_5ma = stock['volumn_5_ma'][14:]

        # 使用者選擇的options
        self.user_opt = options

        self.collect = []

        # 預設的篩選條件
        self.options = {
            'k_size': 0.07,
            'up_size': 0,
            'sticky_days': 10,
            'volumn_big': 2,
            'volumn_size': 300
        }

    '''設定篩選參數，如果self.user_opt不為None，將self.options更新為使用者的設定'''
    def set_options(self):
        if self.user_opt is None:
            return
        else:
            for option, value in self.user_opt.items():
                if option in self.options and value is not None:
                    self.options[option] = value

    '''取得待測日起為止的前10天MA資料'''
    def get_ma_list(self, MA, day):
        today_5 = 15 + day
        today_10 = 10 + day
        today_20 = day

        mv_5_list = MA['MA_5'][today_5 - 10:today_5]
        mv_10_list = MA['MA_10'][today_10 - 10:today_10]
        mv_20_list = MA['MA_20'][today_20 - 10:today_20]

        if len(mv_5_list) != 10 or len(mv_10_list) != 10 or len(mv_20_list) != 10:
            return None

        return (mv_5_list, mv_10_list, mv_20_list)

    '''檢查糾結: input: MA list, 三日的MA差距'''
    def is_sticky(self, mv_list, cond = 0.5):
        day = self.options['sticky_days']



        first = abs(mv_list[1][-1] - mv_list[0][-1])  # 10MA - 5MA******
        second = abs(mv_list[1][-day] - mv_list[0][-day])  # 10 days 10MA - 5MA*****
        third = abs(mv_list[1][-day] - mv_list[2][-day])  # 10 days 10MA - 20MA*****
        # forth = abs(mv_list[0][-5] - mv_list[1][-5])  # 5MA - 10MA
        # five = abs(mv_list[0][-7] - mv_list[1][-7])
        # six = abs(mv_list[0][-3] - mv_list[1][-3])

        return (first <= cond and second <= cond
                and third <= cond)

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

    '''出場'''
    def should_sell(self, latest_price, today_ma_20):
        return (latest_price['close'] < today_ma_20 or
                (latest_price['close'] / latest_price['open']) - 1 <= -0.05)

    '''進場'''
    def should_buy(self, latest_price, ma_list, today_volumn_5ma):
        if today_volumn_5ma in [0, None]: return False

        return (self.is_sticky(ma_list) and
                self.is_k_size(latest_price) and
                self.is_close_big_than_5MA(latest_price, ma_list[0][-1]) and
                self.is_HC_range(latest_price) and
                self.is_volumn(latest_price['volumn'], today_volumn_5ma) and
                self.is_up_5ma(ma_list))

    def start(self):
        global total_rate
        global trade_num
        global win, pos_rate, pos_num, na_rate, na_num

        # 設定options
        self.set_options()
        buy = False
        a_trade = {}
        # print(self.code)
        for day, latest_price in enumerate(self.test_days):
            ma_list = self.get_ma_list(self.MA, day)

            # 缺少MA資料，跳過該日
            if ma_list is None: continue

            if self.should_buy(latest_price, ma_list, self.volumn_5ma[day]) and not buy:
                a_trade['buy'] = latest_price
                a_trade['ma'] = [ma_list[0][-1], ma_list[1][-1], ma_list[2][-1]]
                buy = True

            elif self.should_sell(latest_price, ma_list[1][-1]) and buy:
                a_trade['sell'] = latest_price
                a_trade['return_rate'] = (a_trade['sell']['close'] - a_trade['buy']['close'])/ a_trade['sell']['close']
                total_rate += a_trade['return_rate']
                trade_num += 1

                if a_trade['return_rate'] > 0:
                    pos_rate += a_trade['return_rate']
                    pos_num += 1
                    win += 1
                else:
                    na_rate += a_trade['return_rate']
                    na_num += 1

                buy = False
                self.collect.append(a_trade)




if __name__ == '__main__':
    pp = pprint.PrettyPrinter(indent=4)
    local_db = os.environ['local_db']
    client = MongoClient(local_db)

    history_collect = client['Stock']['history']

    stocks = history_collect.find({})
    result = {}
    for i, stock in enumerate(stocks):
        checker = HisChecker(stock)
        checker.start()

        if len(checker.collect) > 0:
            result[checker.code] = checker.collect

    print(f'Average Return: {total_rate / trade_num}')
    print(f'AVP: {pos_rate / pos_num}')
    print(f'AVN: {na_rate / na_num}')
    print(f'Win rate: {win/ trade_num}')
    print(f'Find {len(result.keys())} company pass')
    print(f'total: {trade_num}')

    pp.pprint(result['1235'])
