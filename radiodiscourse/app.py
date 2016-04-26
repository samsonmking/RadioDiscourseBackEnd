from flask import Flask
from flask.ext.restful import Api, Resource, reqparse, fields, marshal
from delugejsonclient import client
import whatapi

app = Flask(__name__)
api = Api(app)
tclient = client.DelugeJsonClient("deluge")

whatusername = 'pinkyoshimi'
whatpassword = 'tabasco4Life'

torrent_fields = {
    'hash': fields.String,
    'name': fields.String,
    'dl_location': fields.String,
    'dl_progress': fields.Integer,
    'ul_progress': fields.Integer
}

cookies =  None

class Torrent(Resource):
    def __init__(self):

        #Set-up Parser
        self.reqparse = reqparse.RequestParser();
        self.reqparse.add_argument('id', type = str, location = 'json')
        self.reqparse.add_argument('hash', type = str, location = 'json')
        self.reqparse.add_argument('name', type = str, location = 'json')
        self.reqparse.add_argument('dl_location', type = str, location = 'json')
        self.reqparse.add_argument('dl_progress', type = int, location = 'json')
        self.reqparse.add_argument('ul_progress', type = int, location = 'json')
        super(Torrent, self).__init__()

    def get(self, id):
        pass

    def put(self, id):
        args = self.reqparse.parse_args()
        apihandle = whatapi.WhatAPI(username=whatusername, password=whatpassword)
        torrentcontent = apihandle.get_torrent(id)
        torrenthash = tclient.add_torrent_verify(torrentcontent, "/home/dev/seed")
        return {'id': id,
                'hash':torrenthash}

class WhatApi(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('searchstr', type = str, location = 'json' )
        self.reqparse.add_argument('results', type = str, location = 'json')
        super(WhatApi, self).__init__()

    def post(self):
        args = self.reqparse.parse_args()
        searchstr = args["searchstr"]
        apihandle = whatapi.WhatAPI(username=whatusername, password=whatpassword)
        results = apihandle.request("artist", artistname=searchstr)
        return {'searchstr': searchstr,
                'results': results}

api.add_resource(WhatApi, '/rd/api/whatcd', endpoint = 'whatcd')
api.add_resource(Torrent, '/rd/api/torrent/<string:id>', endpoint = 'torrent')

if __name__ == '__main__':
    app.run(debug=True)
