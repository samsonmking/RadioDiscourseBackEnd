from flask import Flask, request
from flask_socketio import SocketIO, emit
from rd_config import async_mode
from radiodiscourse import torrents, app

socketio = SocketIO(app, async_mode=async_mode)

def _get_torrent_list():
    tlist = []
    for key, value in torrents.items():
        tlist.append(value)
    return tlist

@socketio.on('connect', namespace='/socket')
def connect():
    emit('torrentList', _get_torrent_list())