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

# Populate with existing torrents in torrent client
torrents = {}
client_torrents = []
client_torrents = tclient.get_torrent_info()
for t in client_torrents:
    thash = t.get('hash')
    torrents[thash] = {'hash': thash,
                       'name': t.get('name'),
                       'size': t.get('total_size'),
                       'dl': t.get('progress'),
                       'ul': None}

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
        self.reqparse = reqparse.RequestParser()
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
        torrents[torrenthash] = {'id': id,
                                 'hash': torrenthash,
                                 'name': tinfo['name'],
                                 'size': tinfo['total_size'],
                                 'dl': 0,
                                 'ul': 0}
        thread = socketio.start_background_task(target=self._process_torrent, thash=torrenthash)
        return torrents[torrenthash]

    def _process_torrent(self, **kwargs):
        #wait for torrent to download

        torrenthash = kwargs["thash"]
        dl = 0
        tdata = {}
        while dl < 100:
            tdata = tclient.get_torrent_info(torrent_hash=[torrenthash])
            dl = tdata[0]["progress"]
            torrents[torrenthash]["dl"] = "{0:.2f}".format(dl)
            socketio.emit('torrentUpdate', torrents[torrenthash], namespace='/socket')
            socketio.sleep(1)

        gmusic = Musicmanager()
        gmusic.login(oauth_credentials=u'/home/dev/oauth.cred', uploader_id=None, uploader_name=None)

        songpath = tdata[0]["save_path"] + "/" + tdata[0]["name"]
        newsongs = []
        for file in os.listdir(songpath):
            if file.endswith(".mp3"):
                newsongs.append(songpath + '/' + file)

        for song in newsongs:
            results = gmusic.upload(song, enable_matching=False)
            percent = self._update_upload_results(results, newsongs) + torrents[torrenthash]['ul']
            torrents[torrenthash]['ul'] = "{0:.2f}".format(percent)
            socketio.emit('torrentUpdate', torrents[torrenthash], namespace='/socket')
            socketio.sleep(1)

    def _update_upload_results(self, results, songlist):
        total = len(songlist)
        uploaded = len(results[0])
        matched = len(results[1])
        return ((uploaded + matched) / total) * 100

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
            tgroups = results.get('response').get('torrentgroup')
            for t in tgroups:
                t.pop('artists', None)
                t.pop('extendedArtists', None)
                t.pop('tags', None)

            return {'artist_search': artist_search,
                    'results': tgroups}

        except whatapi.RequestException as err:
            return {'artist_search': artist_search,
                    'error': 'request exception'}



api.add_resource(Torrent, '/rd/api/torrent/<string:id>', endpoint = 'torrent')
api.add_resource(WhatCD, '/rd/api/whatcd', endpoint = 'whatcd')

if __name__ == '__main__':
    #app.run(host='0.0.0.0', debug=True)
    socketio.run(app, host='0.0.0.0', debug=True)
