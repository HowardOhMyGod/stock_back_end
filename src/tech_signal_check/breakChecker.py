
# coding: utf-8

from datetime import datetime
from checker import BaseChecker, BaseStarter


'''
功能: 檢查該股當日交易資料是否符合均線糾結，向上突破的特徵
物件參數: 該股documet
回傳值: True or False
'''
class TechChecker(BaseChecker):
    def __init__(self, stock, back_days = 1, options = None):
        super().__init__(stock, options=options)

        # 取得該股最近一天的交易資訊
        self.latest_prcie = stock['history'][-back_days]

        # 取得該股vlolumn_5MA
        self.today_volumn_5ma = stock['volumn_5_ma'][-back_days]

        # 檢測前n天的資料: 1 = 前一天， 2 = 前兩天
        self.back_days = back_days

        # 取得指定天數的5, 10, 20 MA, 格式: tuple(5_ma[back_days], 10_ma[back_days], 20_ma[back_days])
        self.ma_list = self.get_ma_list(self.MA)

    '''取得近期特定天數的MA tuple'''
    def get_ma_list(self, MA):
        day = self.options['sticky_days']
        back_days = self.back_days - 1

        if back_days != 0:
            mv_5_3d = MA['MA_5'][-day - back_days: -back_days]
            mv_10_3d = MA['MA_10'][-day - back_days : -back_days]
            mv_20_3d = MA['MA_20'][-day - back_days: -back_days]
        else:
            mv_5_3d = MA['MA_5'][-day:]
            mv_10_3d = MA['MA_10'][-day:]
            mv_20_3d = MA['MA_20'][-day:]

        #  檢查該股資料有沒有齊全，沒有回傳None，主程式會跳過此股
        if len(mv_5_3d) != day or len(mv_10_3d) != day or len(mv_20_3d) != day:
            return None

        return (mv_5_3d, mv_10_3d, mv_20_3d)

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

class CheckStarter(BaseStarter):
    def __init__(self, back_days = 5, options = None):
        super().__init__(options=options)

        self.pass_company = []
        self.lost_company = []

        self.stocks = super().get_risk_level_stock(self.db['price'])

        self.back_days = back_days

    def start(self):
        for stock in self.stocks:
            try:
                # 檢查前10天內有無符合特徵的股票
                for back_day in range(1, self.back_days):
                    stock_check = TechChecker(stock, back_day, self.options)

                    # add stock code, name, close_price as dict to pass list
                    if stock_check.is_break():
                        self.pass_company.append({
                            'name': stock['name'],
                            'code': stock['code'],
                            'date': stock_check.latest_prcie['date'].strftime("%Y/%m/%d"),
                            'today_close_price': stock_check.latest_prcie['close']
                        })

            except Exception as e:
                # print(e)
                self.lost_company.append(stock['code'])

        # close cursor
        self.stocks.close()
        self.pass_company = sorted(self.pass_company,
                                      key=lambda stock: datetime.strptime(stock['date'], "%Y/%m/%d"),
                                      reverse = True)
if __name__ == '__main__':
    checker = CheckStarter(options={'k_size': 0.07, 'risk_level': 'Mid'})
    checker.start()

    print(f"Pass Company: {checker.pass_company}")
    print(f"Lost Company: {checker.lost_company}, count: {len(checker.lost_company)}")

