from flask import Flask, request
from collections import OrderedDict
from rd_config import debug
app = Flask(__name__)
app.config['SECRET_KEY'] = 'top secret!'

# Allow Cross Origin Requests (for debugging)
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    if request.method == 'OPTIONS':
        response.headers['Access-Control-Allow-Methods'] = 'DELETE, GET, POST, PUT'
        headers = request.headers.get('Access-Control-Request-Headers')
        if headers:
            response.headers['Access-Control-Allow-Headers'] = headers
    return response

if debug:
    app.after_request(add_cors_headers)

torrents = OrderedDict()