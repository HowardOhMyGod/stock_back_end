
# coding: utf-8

from pymongo import MongoClient


class TechChecker:
    def __init__(self, stock):
        self.latest_prcie = stock['history'][-1]
        self.MA = stock['MA']
        self.ma_list = self.get_ma_list(self.MA)

    def get_ma_list(self, MA):
        mv_5_3d = MA['MA_5'][-10:]
        mv_10_3d = MA['MA_10'][-10:]
        mv_20_3d = MA['MA_20'][-10:]

        if len(mv_5_3d) != 10 or len(mv_10_3d) != 10 or len(mv_20_3d) != 10:
            return None

        return (mv_5_3d, mv_10_3d, mv_20_3d)

    '''檢查糾結: input: MA list, 三日的MA差距'''
    def is_sticky(self, mv_list, cond_1=1, cond_2=1, cond_3=1, cond_4 = 1):
        first = abs(mv_list[1][-1] - mv_list[0][-1])  # 10MA - 5MA
        second = abs(mv_list[1][-10] - mv_list[0][-10])  # 10MA - 5MA
        third = abs(mv_list[1][-10] - mv_list[2][-10])  # 10MA - 5MA
        forth = abs(mv_list[0][-5] - mv_list[1][-5])  # 5MA - 10MA
        five = abs(mv_list[0][-7] - mv_list[1][-7])
        six = abs(mv_list[0][-3] - mv_list[1][-3])

        return (first <= cond_1 and second <= cond_2
                and third <= cond_3 and forth <= cond_4 and five <= 1 and six <= 1)

    '''K棒大小: close/open -1'''
    def is_k_size(self, latest_price, size=0.06):
        return ((latest_price['close'] / latest_price['open']) - 1) >= size

    '''高價與收盤價距離'''
    def is_HC_range(self, latest_prcie, dis=0.01):
        return latest_prcie['high'] - latest_prcie['close'] <= dis

    '''成交量大小範圍'''
    def isVolumn(self, volumn, bigger_than=500):
        return volumn >= bigger_than

    '''收盤大於幾倍5MA'''
    def is_close_big_than_5MA(self, latest_prcie, today_5MA, dis=1):
        return latest_prcie['close'] / today_5MA >= dis

    '''檢查上彎5MA'''
    def is_up_5ma(self, ma_list):
        return ma_list[0][-1] > ma_list[0][-2]

    '''檢查主程式'''
    def is_break(self):
        if self.ma_list is None: return False

        return (self.is_sticky(self.ma_list) and
                self.is_k_size(self.latest_prcie) and
                self.is_close_big_than_5MA(self.latest_prcie, self.ma_list[0][-1]) and
                self.is_HC_range(self.latest_prcie) and
                self.isVolumn(self.latest_prcie['volumn']) and
                self.is_up_5ma(self.ma_list))


if __name__ == '__main__':
    tech_pass_company = []
    lost = 0
    priceCollect = MongoClient()['Stock']['price']

    stocks = priceCollect.find({})

    for stock in stocks:
        try:
            stock_check = TechChecker(stock)
            if stock_check.is_break():
                tech_pass_company.append(stock['code'])
        except:
            print(stock['code'])
            lost += 1

    print(f"Break Company: {tech_pass_company}")
    print(f"lost count: {lost}")

