from flask import Flask
from flask_restful import Resource, Api, reqparse, abort

from tech_signal_check.breakChecker import CheckStarter

app = Flask(__name__)
api = Api(app)


# front end post payload argument
parser = reqparse.RequestParser()

# set argument type
parser.add_argument("k_size", type=float)
parser.add_argument("up_size", type=float)
parser.add_argument("sticky_days", type=int)
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
        args = parser.parse_args()
        print(args)
        checker = CheckStarter(args)
        checker.start()
        pass_company = checker.pass_company

        return {'pass_count': len(pass_company),
               'pass_company': pass_company}


api.add_resource(BreakChecker, '/breakcheck')

if __name__ == '__main__':
    app.run(debug=True)