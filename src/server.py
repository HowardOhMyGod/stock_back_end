from flask import Flask
from flask_cors import CORS
from flask_restful import Resource, Api, reqparse, abort

from tech_signal_check.breakChecker import CheckStarter
from tech_signal_check.historyChecker import HisStarter

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})
api = Api(app)


# front end post payload argument
parser = reqparse.RequestParser()

# set argument type
parser.add_argument("k_size", type=float)
parser.add_argument("up_size", type=float)
parser.add_argument("sticky_days", type=int)
parser.add_argument("sticky_level", type=float)
parser.add_argument("volumn_big", type=float)
parser.add_argument("volumn_size", type=int)
parser.add_argument("risk_level", type=str)


# set breakcheck route
'''功能: 接受前端篩選條件，傳給ChckerStarter'''
'''回傳Json: {
    'pass_count': int,
    'pass_company: list(dict)
}'''
class BreakChecker(Resource):
    def post(self):
        # 取得post payload
        args = parser.parse_args()
        print(args)

        # 取得前五天股票市場符合技術分析標的
        today_checker = CheckStarter(options=args)
        today_checker.start()
        pass_company = today_checker.pass_company

        # 取得回測結果 index
        history_checker = HisStarter(options=args)
        history_checker.start()
        result_index = history_checker.result_index

        return {
                'pass_count': len(pass_company),
                'pass_company': pass_company,
                'his_index': result_index}


api.add_resource(BreakChecker, '/breakcheck')

if __name__ == '__main__':
    app.run(host='0.0.0.0 ')