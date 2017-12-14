
# coding: utf-8

from pymongo import MongoClient

'''
功能: 檢查該股當日交易資料是否符合均線糾結，向上突破的特徵
物件參數: 該股documet
回傳值: True or False
'''
class TechChecker:
    def __init__(self, stock):
        # 取得該股最近一天的交易資訊
        self.latest_prcie = stock['history'][-1]

        # 取得該股MA
        self.MA = stock['MA']

        # 取得該股vlolumn_5MA
        self.today_volumn_5ma = stock['volumn_5_ma'][-1]

        # 取得指定天數的5, 10, 20 MA, 格式: (5_ma[back_days], 10_ma[back_days], 20_ma[back_days])
        self.ma_list = self.get_ma_list(self.MA)

        # 回去檢查back_days的ma, 影響到get_ma_list, is_sticky
        self.back_days = 10

    def get_ma_list(self, MA):
        mv_5_3d = MA['MA_5'][-10:]
        mv_10_3d = MA['MA_10'][-10:]
        mv_20_3d = MA['MA_20'][-10:]

        #  檢查該股資料有沒有齊全，沒有回傳None，主程式會跳過此股
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
    def is_volumn(self, volumn, today_vol_5ma, bigger_than=1.5):
        return (volumn / today_vol_5ma >= bigger_than and
                volumn >= 500)

    '''收盤大於幾倍5MA'''
    def is_close_big_than_5MA(self, latest_prcie, today_5MA, dis=1):
        return latest_prcie['close'] / today_5MA >= dis

    '''檢查上彎5MA'''
    def is_up_5ma(self, ma_list):
        return ma_list[0][-1] > ma_list[0][-2]

    '''檢查主程式'''
    def is_break(self):
        # 缺少MA資料，跳過此股
        if self.ma_list is None: return False

        return (self.is_sticky(self.ma_list) and
                self.is_k_size(self.latest_prcie) and
                self.is_close_big_than_5MA(self.latest_prcie, self.ma_list[0][-1]) and
                self.is_HC_range(self.latest_prcie) and
                self.is_volumn(self.latest_prcie['volumn'], self.today_volumn_5ma) and
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

