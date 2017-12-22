
from pymongo import MongoClient
import pprint
import os

class HisChecker:
    def __init__(self, stock, result_index, options = None):
        # 取得在該股歷史資料中，第20天(包含)之後的資料
        self.test_days = stock['history'][19:]

        self.MA = stock['MA']
        self.code = stock['code']

        # 取得在該股歷史資料中，第20天(包含)之後的volumn_5_ma
        self.volumn_5ma = stock['volumn_5_ma'][14:]

        # 使用者選擇的options
        self.user_opt = options

        # 策略衡量總指標
        self.result_index = result_index

        # 所有股票進出場明細
        self.collect = []

        # 預設的篩選條件
        self.options = {
            'k_size': 0.07,
            'up_size': 0,
            'sticky_days': 10,
            'sticky_level': 0.5,
            'volumn_big': 2,
            'volumn_size': 300,
            'risk_level': 'Mid'
        }

    '''設定篩選參數，如果self.user_opt不為None，將self.options更新為使用者的設定'''
    def set_options(self):
        if self.user_opt is None:
            return
        else:
            for option, value in self.user_opt.items():
                if option in self.options and value is not None:
                    self.options[option] = value

    '''取得待測日起為止的前sticky_day天MA資料'''
    def get_ma_list(self, MA, day):
        today_5 = 15 + day
        today_10 = 10 + day
        today_20 = day

        # 前N天
        sticky_day = self.options['sticky_days']

        mv_5_list = MA['MA_5'][today_5 - sticky_day:today_5]
        mv_10_list = MA['MA_10'][today_10 - sticky_day:today_10]
        mv_20_list = MA['MA_20'][today_20 - sticky_day:today_20]

        if len(mv_5_list) != sticky_day or len(mv_10_list) != sticky_day or len(mv_20_list) != sticky_day:
            return None

        return (mv_5_list, mv_10_list, mv_20_list)

    '''檢查糾結: input: MA list, 三日的MA差距'''
    def is_sticky(self, mv_list):
        day = self.options['sticky_days']
        cond = self.options['sticky_level']

        first = abs(mv_list[1][-1] - mv_list[0][-1])  # today 10MA - 5MA
        second = abs(mv_list[1][-day] - mv_list[0][-day])  # 10 days 10MA - 5MA
        third = abs(mv_list[1][-day] - mv_list[2][-day])  # 10 days 10MA - 20MA

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
        # 設定options
        self.set_options()
        buy = False
        a_trade = {}
        # print(self.code)
        for day, latest_price in enumerate(self.test_days):
            ma_list = self.get_ma_list(self.MA, day)

            # 缺少MA資料，跳過該日
            if ma_list is None: continue

            # 進場
            if self.should_buy(latest_price, ma_list, self.volumn_5ma[day]) and not buy:
                a_trade['buy'] = latest_price
                a_trade['ma'] = [ma_list[0][-1], ma_list[1][-1], ma_list[2][-1]]
                buy = True

            # 出場
            elif self.should_sell(latest_price, ma_list[1][-1]) and buy:
                a_trade['sell'] = latest_price
                a_trade['return_rate'] = (a_trade['sell']['close'] - a_trade['buy']['close'])/ a_trade['sell']['close']

                # update index_result
                self.result_index['total_rate'] += a_trade['return_rate']
                self.result_index['trade_num'] += 1

                # 計算持有天數
                holding_days = a_trade['sell']['date'] - a_trade['buy']['date']
                self.result_index['holding_days'] += holding_days.days

                # 計算正報酬次數、累積正報酬
                if a_trade['return_rate'] > 0:
                    self.result_index['pos_rate'] += a_trade['return_rate']
                    self.result_index['pos_num'] += 1

                    # 最大正報酬率
                    if a_trade['return_rate'] > self.result_index['max_pos_rate']:
                        self.result_index['max_pos_rate'] = a_trade['return_rate']

                # 計算負報酬次數、累積負報酬
                else:
                    self.result_index['na_rate'] += a_trade['return_rate']
                    self.result_index['na_num'] += 1

                    # 最小負報酬率
                    if a_trade['return_rate'] < self.result_index['min_na_rate']:
                        self.result_index['min_na_rate'] = a_trade['return_rate']

                buy = False
                self.collect.append(a_trade)


class HisStarter:
    def __init__(self, options = None):
        client = MongoClient(os.environ['local_db'])
        self.__db = client['Stock']
        history_collect = self.__db['history']

        # 設定風險標的
        self.options = options
        risk_groups = self.get_risk_codes()

        # 取得風險標的資料
        self.stocks = history_collect.find({'code' : {
            '$in': risk_groups
        }})

        # 策略結果指標
        self.result_index = {
            'total_rate': 0, # 總累積報酬率
            'trade_num': 0,  # 總交易次數
            'pos_rate': 0,   # 累積正報酬率
            'pos_num': 0,    # 累積正報酬次數
            'na_rate': 0,    # 累積負報酬率
            'na_num': 0,      # 累積負報酬次數
            'max_pos_rate': 0, # 最大正報酬
            'min_na_rate': 1,   # 最小負報酬率
            'holding_days': 0,     # 總持有天數
            'avg_rate': None,
            'avg_hold_days': None,
            'win_rate': None
        }

        # 交易資料
        self.trade_data = {}

    def get_risk_codes(self):
        risk_group = 'mid_risk_group'

        if self.options['risk_level'] == 'High':
            risk_group = 'high_risk_group'
        elif self.options['risk_level'] == 'Low':
            risk_group = 'low_risk_group'

        return self.__db['code'].find_one()[risk_group]

    def start(self):
        print('HisStarter start!')
        for stock in self.stocks:
            checker = HisChecker(stock, self.result_index, self.options)
            checker.start()

            if len(checker.collect) > 0:
                self.trade_data[checker.code] = checker.collect

        # 計算平均指標
        self.result_index['win_rate'] = self.result_index['pos_num'] / self.result_index['trade_num']
        self.result_index['avg_hold_days'] = self.result_index['holding_days'] / self.result_index['trade_num']
        self.result_index['avg_rate'] = self.result_index['total_rate'] / self.result_index['trade_num']

if __name__ == '__main__':
    his_starter = HisStarter({'risk_level': 'Mid'})
    his_starter.start()

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(his_starter.result_index)
