from flask_restful import Resource, reqparse
from delugejsonclient import client
from gmusicapi import Musicmanager
import whatapi
from rd_config import whatpassword, whatusername, delugepassword, oauthpath
from socket_io import socketio
from token_auth import  auth
from radiodiscourse import torrents, lock
import os
from threading import Thread
import time
import copy

tclient = client.DelugeJsonClient(delugepassword)

# Populate with existing torrents in torrent client
client_torrents = []
client_torrents = tclient.get_torrent_info()
for t in client_torrents:
    thash = t.get('hash')
    with lock:
        torrents[thash] = {'hash': thash,
                           'name': t.get('name'),
                           'size': t.get('total_size'),
                           'dl': t.get('progress'),
                           'ul': None,
                           'status': 'previous'}

class Torrents(Resource):
    def __init__(self):
        super(Torrents, self).__init__()

    @auth.login_required
    def get(self):
        tlist = []
        for key, value in torrents.items():
            tlist.append(value)
        return tlist

class Torrent(Resource):
    def __init__(self, **kwargs):
        super(Torrent, self).__init__()

    @auth.login_required
    def post(self, id):
        apihandle = whatapi.WhatAPI(username=whatusername, password=whatpassword)
        torrentcontent = apihandle.get_torrent(id)
        tinfo = tclient.add_torrent_verify(torrentcontent, "/home/dev/seed")
        torrenthash = tinfo['hash']
        with lock:
            torrents[torrenthash] = {'id': id,
                                     'hash': torrenthash,
                                     'name': tinfo['name'],
                                     'size': tinfo['total_size'],
                                     'dl': 0,
                                     'ul': 0,
                                     'status': 'started'}
            torrents.move_to_end(torrenthash, last=False)
        # pdb.set_trace()
        upload_thread = Thread(target=self._process_torrent, kwargs={'thash': torrenthash})
        upload_thread.start()
        update_thread = socketio.start_background_task(target=self._update_process_socket, thash=torrenthash)
        return torrents[torrenthash]

    def _process_torrent(self, **kwargs):
        #wait for torrent to download

        torrenthash = kwargs["thash"]
        dl = 0
        tdata = {}
        while dl < 100:
            time.sleep(0.5)
            tdata = tclient.get_torrent_info(torrent_hash=[torrenthash])
            with lock:
                dl = tdata[0]["progress"]
                torrents[torrenthash]["dl"] = "{0:.2f}".format(dl)

        gmusic = Musicmanager()
        logged_in = gmusic.login(oauth_credentials=oauthpath, uploader_id=None, uploader_name=None)
        if not logged_in:
            raise Exception('Failed to log into google music')
            
        songpath = tdata[0]["save_path"] + "/" + tdata[0]["name"]
        newsongs = []
        for file in os.listdir(songpath):
            if file.endswith(".mp3"):
                newsongs.append(songpath + '/' + file)

        for song in newsongs:
            print (song)
            results = gmusic.upload(song, enable_matching=False)
            print(results)
            with lock:
                percent = self._update_upload_results(results, newsongs) + float(torrents[torrenthash]['ul'])
                torrents[torrenthash]['ul'] = percent

        with lock:
            torrents[torrenthash]['status'] = 'processed'

    def _update_process_socket(self, **kwargs):
        torrenthash = kwargs.get('thash', None)
        status = None
        while status != 'processed':
            with lock:
                tdata = copy.deepcopy(torrents.get(torrenthash))
                ul = tdata['ul']
                tdata['ul'] = "{0:.2f}".format(ul)
                socketio.emit('torrentUpdate', tdata, namespace='/socket')
                status = tdata.get('status')
            socketio.sleep(0.5)

    def _update_upload_results(self, results, songlist):
        total = len(songlist)
        uploaded = len(results[0])
        matched = len(results[1])
        return ((uploaded + matched) / total) * 100