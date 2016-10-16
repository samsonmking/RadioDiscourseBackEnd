from flask_restful import Resource, reqparse
import whatapi
from rd_config import  whatusername, whatpassword
from token_auth import auth

class WhatCD(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('artist_search', type = str)
        super(WhatCD, self).__init__()

    @auth.login_required
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