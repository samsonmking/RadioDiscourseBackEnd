import threading
from time import sleep

import base64
import requests

from delugejsonclient import torrentutils


class LoginException(Exception):
    pass

class RequestException(Exception):
    pass

class DelugeJsonClient:

    def __init__(self):
        self.headers = {
        'Content-type': 'application/json',
        'Accept': 'application/json'
        }
        self.lock = threading.Lock()
        self.session = requests.session()
        self.session.headers = self.headers
        self.password = "deluge"
        self.requestNum = 0

    def _url(self):
        return "http://localhost:8112/json"

    def _num(self):
        with self.lock:
            self.requestNum += 1
            return self.requestNum

    def _login(self):
        num = self._num()
        reply = self.session.post(self._url(),json={'id': num,
                                               'method': 'auth.login',
                                               'params': [self.password]})
        if reply.status_code != 200:
            raise RequestException

        jreply = reply.json()
        if (not jreply["result"]) or (jreply["error"] is not None):
            raise LoginException


    def get_version(self):
        reply = self._request("webapi.get_api_version")
        jreply = reply.json()
        if jreply["error"] is not None:
            raise RequestException(jreply["error"]["message"])
        return jreply["result"]

    #hash_list - [hash1, hash2]
    #field_filter - ["name", "hash", "progress", "save_path"]
    def get_torrent_info(self, **kwargs):

        hash_list = None
        if 'torrent_hash' in kwargs:
            hash_list = kwargs['torrent_hash']

        field_filter = ["hash", "name", "progress", "save_path"]
        if 'filter' in kwargs:
            field_filter = kwargs['filter']

        reply = self._request("webapi.get_torrents", hash_list, field_filter)
        jreply = reply.json()
        if jreply["error"] is not None:
            raise RequestException(jreply["error"]["message"])

        return jreply["result"]["torrents"]

    def _add_torrent_contents(self, torrent_data, dl_location):
        enc_torrent = base64.b64encode(torrent_data).decode('utf-8')
        reply = self._request("webapi.add_torrent", enc_torrent)
        jreply = reply.json()
        if jreply["error"] is not None:
            raise RequestException(jreply["error"]["message"])

    def add_torrent_verify(self, torrent_file, dl_location):
        torrent_data = torrent_file.read()
        self._add_torrent_contents(torrent_data, dl_location)
        file_hash = torrentutils.get_hash_from_torrent_contents(torrent_data)
        sleep(1)
        t_hash = self.get_torrent_info(torrent_hash=[file_hash], filter=["hash"])[0]["hash"]
        if t_hash != file_hash:
            raise RequestException("Could not verify torrent uploaded")
        return t_hash

    def remove_torrent(self, torrent_hash, remove_data):
        reply = self._request("webapi.remove_torrent", torrent_hash, remove_data)
        jreply = reply.json()
        if (not jreply["result"]) or (jreply["error"] is not None):
            raise RequestException("Failed to remove torrent " + torrent_hash)

    def _request(self, action, *args):
        num = self._num()
        reply = self.session.post(self._url(),json={'id': num,
                                               'method': action,
                                               'params': args})
        if reply.status_code != 200:
            raise RequestException
        jreply = reply.json()
        # Ensure this is the correct reply
        if jreply["id"] != num:
            raise RequestException("Reply id mismatch")
        # If we're not logged in, authenticate, and try again
        error= jreply["error"]
        if error is not None:
            if error["message"] == "Not authenticated":
                self._login()
                return self._request(action, *args)

        return reply

if __name__ == '__main__':
    client = DelugeJsonClient()
    #print(client.get_version())
    #client.remove_torrent("eb0ae0559542e4980c9ac84217c60ef2c4733d06", False)
    tfile = open("/var/lib/deluge/Downloads/yuck.torrent", 'rb')
    print(client.add_torrent_verify(tfile, "/var/lib/deluge/Downloads"))
