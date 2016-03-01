import bencoder
import hashlib

def get_hash_from_torrent_file(tfile):
    return get_hash_from_torrent_contents(tfile.read())

def get_hash_from_torrent_contents(tcontents):
    d=bencoder.decode(tcontents)
    info = d[b"info"]
    return hashlib.sha1(bencoder.encode(info)).hexdigest()

if __name__ == "__main__":
    f=open("/var/lib/deluge/Downloads/yndi.torrent", 'rb')
    print(get_hash_from_torrent_file(f))