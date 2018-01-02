import os
import smtplib

from email.mime.text import MIMEText
from datetime import datetime

from price_crawler.counter_get_today_price import CounterCrawler
from price_crawler.market_get_today_price import MarketCrawler


'''Email sender'''
class Email:
    def __init__(self, to):
        self.mymail = 'howard036060006@gmail.com'
        self.smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
        self.smtpObj.starttls()
        self.smtpObj.login(self.mymail, os.environ['gmail_pwd'])

        self.to = to

    def write_mail(self, content):
        msg = MIMEText(content['body'])

        msg['Subject'] = content['subject']
        msg['From'] = self.mymail
        msg['To'] = self.to

        return msg

    def send(self, content):
        mail = self.write_mail(content)
        self.smtpObj.sendmail(self.mymail, self.to, mail.as_string())

'''Update latest stock price in db'''
class PriceUpdater:
    def __init__(self):
        self.__market_crawler = MarketCrawler()
        self.__counter_crawler = CounterCrawler()

    def run(self):
        self.__market_crawler.start()
        self.__counter_crawler.start()

        market_count = self.__market_crawler.total
        counter_count = self.__counter_crawler.total

        # 回傳更新股數
        return market_count, counter_count


if __name__ == '__main__':
    err_msg = None
    # 更新股
    try:
        p_updater = PriceUpdater()
        market_count, counter_count = p_updater.run()
    except Exception as e:
        err_msg = str(e)



    # 寄出Email
    for user in ['howard036060006@gmail.com', 'andy566159@gmail.com']:
        email = Email(user)
        if err_msg is None:
            email.send({
                "subject": f'{datetime.today().strftime("%Y/%m/%d")} Price Update!',
                "body": f'Market update: {market_count}, counter update: {counter_count}'
            })
        else:
            email.send({
                "subject": f'{datetime.today().strftime("%Y/%m/%d")} Price Update!',
                "body": f'Error occur: {err_msg}'
            })

    print("Email sent!")
