from flask_socketio import SocketIO, emit
from rd_config import async_mode
from radiodiscourse import torrents, app

socketio = SocketIO(app, async_mode=async_mode)

@socketio.on('connect', namespace='/socket')
def connect():
    pass