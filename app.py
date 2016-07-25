from flask import Flask, request
from flask_restful import Api, Resource, reqparse, fields, marshal
from flask_socketio import SocketIO, emit
from delugejsonclient import client
from gmusicapi import Musicmanager
import time
import whatapi
import os

async_mode = None

app = Flask(__name__)
api = Api(app)
socketio = SocketIO(app, async_mode=async_mode)
tclient = client.DelugeJsonClient("deluge")

#configs
whatusername = 'pinkyoshimi'
whatpassword = 'tabasco4Life'
oauthpath = '/home/dev/oauth.cred'

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    if request.method == 'OPTIONS':
        response.headers['Access-Control-Allow-Methods'] = 'DELETE, GET, POST, PUT'
        headers = request.headers.get('Access-Control-Request-Headers')
        if headers:
            response.headers['Access-Control-Allow-Headers'] = headers
    return response
app.after_request(add_cors_headers)

cookies =  None

torrents = {}

def _get_torrent_list():
    tlist = []
    for key, value in torrents.items():
        tlist.append(value)
    return tlist

@socketio.on('connect', namespace='/socket')
def connect():
    emit('torrentList', _get_torrent_list())



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
        return 'hello'

    def post(self, id):
        args = self.reqparse.parse_args()
        apihandle = whatapi.WhatAPI(username=whatusername, password=whatpassword)
        torrentcontent = apihandle.get_torrent(id)
        tinfo = tclient.add_torrent_verify(torrentcontent, "/home/dev/seed")
        torrenthash = tinfo['hash']
        thread = socketio.start_background_task(target=self._process_torrent, thash=torrenthash)
        torrents[torrenthash] = {'id': id,
                                'hash': torrenthash,
                                'name': tinfo['name'],
                                'size': tinfo['total_size'],
                                'dl': 0,
                                'ul': 0}
        return torrents[torrenthash]

    def _process_torrent(self, **kwargs):
        #wait for torrent to download

        torrenthash = kwargs["thash"]
        dl = 0
        tdata = {}
        while dl < 100:
            socketio.sleep(1)
            tdata = tclient.get_torrent_info(torrent_hash=[torrenthash])
            dl = tdata[0]["progress"]
            torrents[torrenthash]["dl"] = dl
            socketio.emit('torrentUpdate', torrents[torrenthash], namespace='/socket')

        socketio.emit('torrentUpdate', torrents[torrenthash], namespace='/socket')
        songpath = tdata[0]["save_path"] + "/" + tdata[0]["name"]
        newsongs = []
        for file in os.listdir(songpath):
            if file.endswith(".mp3"):
                newsongs.append(songpath + '/' + file)
        socketio.emit('torrentUpdate', torrents[torrenthash], namespace='/socket')
        gmusic = Musicmanager()
        gmusic.login(oauth_credentials=u'/home/dev/oauth.cred', uploader_id=None, uploader_name=None)
        results = gmusic.upload(newsongs, enable_matching=False)
        percent_uploaded = self._get_upload_results(results)
        torrents[torrenthash]["ul"] = percent_uploaded
        socketio.emit('torrentUpdate', torrents[torrenthash], namespace='/socket')

    def _get_upload_results(self, results):
        uploaded = len(results[0])
        matched = len(results[1])
        no_upload = len(results[2])
        total = uploaded + matched + no_upload
        return (uploaded / total) * 100

class WhatCD(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('artist_search', type = str)
        super(WhatCD, self).__init__()

    def get(self):
        try:
            args = self.reqparse.parse_args()
            artist_search = args["artist_search"]
            apihandle = whatapi.WhatAPI(username=whatusername, password=whatpassword)
            results = apihandle.request("artist", artistname=artist_search)
            return {'artist_search': artist_search,
                    'results': results["response"]["torrentgroup"]}
        except whatapi.RequestException as err:
            return {'artist_search': artist_search,
                    'error': 'request exception'}



api.add_resource(Torrent, '/rd/api/torrent/<string:id>', endpoint = 'torrent')
api.add_resource(WhatCD, '/rd/api/whatcd', endpoint = 'whatcd')

if __name__ == '__main__':
    #app.run(host='0.0.0.0', debug=True)
    socketio.run(app, host='0.0.0.0', debug=True)
