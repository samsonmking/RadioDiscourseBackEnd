from flask_restful import Resource, reqparse
from delugejsonclient import client
from gmusicapi import Musicmanager
import whatapi
from rd_config import whatpassword, whatusername
from socket_io import socketio
from token_auth import  auth
from radiodiscourse import torrents
import os

tclient = client.DelugeJsonClient("deluge")

# Populate with existing torrents in torrent client
client_torrents = []
client_torrents = tclient.get_torrent_info()
for t in client_torrents:
    thash = t.get('hash')
    torrents[thash] = {'hash': thash,
                       'name': t.get('name'),
                       'size': t.get('total_size'),
                       'dl': t.get('progress'),
                       'ul': None}

class Torrent(Resource):
    def __init__(self, **kwargs):
        super(Torrent, self).__init__()

    @auth.login_required
    def post(self, id):
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
            percent = self._update_upload_results(results, newsongs) + float(torrents[torrenthash]['ul'])
            torrents[torrenthash]['ul'] = "{0:.2f}".format(percent)
            socketio.emit('torrentUpdate', torrents[torrenthash], namespace='/socket')
            socketio.sleep(1)

    def _update_upload_results(self, results, songlist):
        total = len(songlist)
        uploaded = len(results[0])
        matched = len(results[1])
        return ((uploaded + matched) / total) * 100