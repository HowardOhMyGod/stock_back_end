import os
from mymodule.module import load_module

mongodb = load_module(os.path.dirname(__file__), '../db', 'mongodb')

class BaseChecker:
    options = {
            'k_size': 0.07,
            'up_size': 0,
            'sticky_days': 10,
            'volumn_big': 2,
            'sticky_level': 0.5,
            'volumn_size': 500,
            'risk_group': 'Mid'
        }

    def __init__(self, this_stock, options = None):
        self.MA = this_stock['MA']
        self.user_opt = options

    def set_options(self):
        '''設定篩選參數，如果self.user_opt不為None，將self.options更新為使用者的設定'''

        if self.user_opt is None:
            return
        else:
            for option, value in self.user_opt.items():
                if option in self.options and value is not None:
                    self.options[option] = value

    def is_sticky(self, mv_list):
        '''檢查糾結: input: MA list, 三日的MA差距'''

        day = self.options['sticky_days']
        cond = self.options['sticky_level']

        first = abs(mv_list[1][-1] - mv_list[0][-1])  # today 10MA - 5MA
        second = abs(mv_list[1][-day] - mv_list[0][-day])  # 10 days 10MA - 5MA
        third = abs(mv_list[1][-day] - mv_list[2][-day])  # 10 days 10MA - 20MA

        return (first <= cond and second <= cond
                and third <= cond)

    def is_k_size(self, latest_price):
        '''K棒大小: close/open -1'''

        size = self.options['k_size']

        return ((latest_price['close'] / latest_price['open']) - 1) >= size

    def is_HC_range(self, latest_prcie):
        '''高價與收盤價距離'''
        dis = self.options['up_size']

        return latest_prcie['high'] - latest_prcie['close'] <= dis

    def is_volumn(self, volumn, today_vol_5ma):
        '''成交量大小範圍'''
        bigger_than = self.options['volumn_big']
        bigger_size = self.options['volumn_size']

        return (volumn / today_vol_5ma >= bigger_than and
                volumn >= bigger_size)

    def is_close_big_than_5MA(self, latest_prcie, today_5MA):
        '''收盤大於5MA'''
        return latest_prcie['close'] > today_5MA

    def is_up_5ma(self, ma_list):
        '''檢查上彎5MA'''
        return ma_list[0][-1] > ma_list[0][-2]

class BaseStarter:
    def __init__(self, options = None):
        self.db = mongodb.Mongo.connect('Stock')

        self.options = options
        self.risk_groups = self.get_risk_codes()

    def get_risk_level_stock(self, collection):
        return collection.find({'code': {
            '$in': self.risk_groups
        }})

    def get_risk_codes(self):
        risk_group = 'mid_risk_group'

        if self.options['risk_level'] == 'High':
            risk_group = 'high_risk_group'
        elif self.options['risk_level'] == 'Low':
            risk_group = 'low_risk_group'

        return self.db['code'].find_one()[risk_group]
