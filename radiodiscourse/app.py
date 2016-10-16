from flask_restful import Api
from socket_io import socketio
from torrent import Torrent, Torrents
from what_cd import WhatCD
from token_auth import Token
from radiodiscourse import app
from rd_config import debug

api = Api(app)
api.add_resource(Torrent, '/rd/api/torrent/<string:id>', endpoint = 'torrent')
api.add_resource(Torrents, '/rd/api/torrents', endpoint = 'torrents')
api.add_resource(WhatCD, '/rd/api/whatcd', endpoint = 'whatcd')
api.add_resource(Token, '/rd/api/auth', endpoint = 'token')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=debug)
