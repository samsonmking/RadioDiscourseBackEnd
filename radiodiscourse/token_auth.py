from flask import Flask, request, g
from flask_restful import Resource, reqparse
from flask_httpauth import HTTPTokenAuth
from itsdangerous import TimedJSONWebSignatureSerializer as JWT
from rd_config import users
from radiodiscourse import  app

# Token will last for a week

jwt = JWT(app.config['SECRET_KEY'], expires_in=604800000)
auth = HTTPTokenAuth('Bearer')

@auth.verify_token
def verify_token(token):
    g.user = None
    bytes = token.encode('utf-8')
    try:
        data = jwt.loads(bytes)
    except:
        return False
    if 'username' in data:
        g.user = data['username']
        return True
    return False

class Token(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser();
        self.reqparse.add_argument('username', type=str, location='json')
        self.reqparse.add_argument('password', type=str, location='json')

    @auth.login_required
    def get(self):
        return self._generate_token(g.user)

    def post(self):
        args = self.reqparse.parse_args()
        user = args['username']
        attempted_pass = args['password']
        correct_pass = users.get(user, None)
        if correct_pass and correct_pass == attempted_pass:
            return self._generate_token(user)

        return {'error': 'Unable to generate a token for this user'}

    def _generate_token(self, user):
        token = jwt.dumps({'username': user})
        return {'auth_token': token.decode('utf-8')}