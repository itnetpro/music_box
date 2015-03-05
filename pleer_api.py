# -*- encoding: utf-8 -*-
# http://pleer.com/

import os
import math
import datetime
import json
import requests
import urllib
import cStringIO
import soundcloud
from PIL import Image

PLEER_API_TOKEN_URL = 'http://api.pleer.com/token.php'
PLEER_API_URL = 'http://api.pleer.com/index.php'
PLEER_API_ID = '826310'
PLEER_API_KEY = 'NSRv3CrghEReFHYdid1l'

LASTFM_API_URL = 'http://ws.audioscrobbler.com/2.0/'
LASTFM_API_USER = 'f1aky927'
LASTFM_API_KEY = '800972591a0e02f1ec49a852deac2292'
LASTFM_API_SECRET = '5a97c3f8d962040b7f129b71fba4a2a0'


SOUNDCLOUND_ID = 'd7595953ebb1b85873c0af6574cadbce'
SOUNDCLOUND_SECRET = '636a0074924cc739e72b3b50a462dcac'


class Pleer(object):

    def __init__(self):
        self.token = None
        self.token_time = None
        self.token_update()

    def token_update(self):
        now = datetime.datetime.now()
        if (self.token_time and self.token) and\
                (now - self.token_time).total_seconds() < 3000:
            return

        res = requests.post(
            PLEER_API_TOKEN_URL,
            auth=(PLEER_API_ID, PLEER_API_KEY),
            data={'grant_type': 'client_credentials'})

        self.token = json.loads(res.content)['access_token']
        self.token_time = now

    def search(self, query):
        self.token_update()

        res = requests.post(
            PLEER_API_URL,
            data={'access_token': self.token,
                  'method': 'tracks_search',
                  'query': query,
                  'quality': 'good',
                  'result_on_page': '20'}
        )

        res_data = json.loads(res.content)
        if int(res_data['count']) < 1:
            yield None

        for key, data in res_data['tracks'].iteritems():
            yield {
                'artist': data['artist'],
                'track': data['track'],
                'stream_link': self.get_stream_link(data['id']),
                'image_link': self.get_image_link(data['artist'], data['track']),
                'time': self.get_track_time(data['lenght']),
                'ttime': int(math.floor(float(data['lenght'])))
            }

    def get_population(self):
        self.token_update()
        res = requests.post(
            PLEER_API_URL,
            data={'access_token': self.token,
                  'method': 'get_top_list',
                  'list_type': '2',
                  'page': '1',
                  'language': 'ru'}
        )

        res_data = json.loads(res.content)
        if int(res_data['tracks']['count']) < 1:
            yield None

        for key, data in res_data['tracks']['data'].iteritems():
            yield {
                'artist': data['artist'],
                'track': data['track'],
                'stream_link': self.get_stream_link(data['id']),
                'image_link': self.get_image_link(data['artist'], data['track']),
                'time': self.get_track_time(data['lenght']),
                'ttime': int(math.floor(float(data['lenght'])))
            }

    def get_stream_link(self, uid):
        res = requests.post(
            PLEER_API_URL,
            data={'access_token': self.token,
                  'method': 'tracks_get_download_link',
                  'track_id': uid,
                  'reason': 'listen'}
        )
        return json.loads(res.content)['url']

    def get_image_link(self, artist, track):
        res = requests.get(
            LASTFM_API_URL,
            params={
                'method': 'track.getInfo',
                'user': LASTFM_API_USER,
                'api_key': LASTFM_API_KEY,
                'artist': artist,
                'track': track,
                'format': 'json'
            }
        )
        try:
            link = json.loads(
                res.content)['track']['album']['image'][-1]['#text']
            if not link:
                return 'img/no-photo.png'
            filename = link.split('/')[-1]
            filepath = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), 'downloads/', filename)
            if not os.path.exists(filepath):
                fle = cStringIO.StringIO(urllib.urlopen(link).read())
                img = Image.open(fle)
                img.save(filepath)

            return filepath

        except (KeyError, IndexError):
            return self.get_image_artist_link(artist) or os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'img/no-photo.png')

    def get_image_artist_link(self, artist):
        res = requests.get(
            LASTFM_API_URL,
            params={
                'method': 'artist.getInfo',
                'user': LASTFM_API_USER,
                'api_key': LASTFM_API_KEY,
                'artist': artist,
                'format': 'json'
            }
        )
        try:
            link = json.loads(
                res.content)['artist']['image'][-1]['#text']
            if not link:
                return
            filename = link.split('/')[-1]
            filepath = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), 'downloads/', filename)
            if not os.path.exists(filepath):
                fle = cStringIO.StringIO(urllib.urlopen(link).read())
                img = Image.open(fle)
                img.save(filepath)
            return filepath

        except (KeyError, IndexError):
            return None

    def get_track_time(self, lenght):
        minute = math.floor(int(lenght) / 60.)
        second = int(lenght) - minute * 60
        return '%02d:%02d' % (minute, second)


class SoundCloundPleer(object):

    def __init__(self):
        self.client = soundcloud.Client(client_id=SOUNDCLOUND_ID)

    def search(self, query):
        tracks = self.client.get('/tracks', q=query)

        for track in tracks:
            try:
                yield {
                    'artist': track.title.split(' - ', 1)[0],
                    'track': track.title.split(' - ', 1)[1],
                    'stream_link': self.get_stream_link(track.stream_url),
                    'image_link': self.get_image_link(track.artwork_url),
                    'time': self.get_track_time(track.duration / 1000),
                    'ttime': int(math.floor(float(track.duration / 1000)))
                }
            except Exception as e:
                continue

    def get_population(self):
        tracks = self.client.get('/tracks')

        for track in tracks:
            try:
                yield {
                    'artist': track.title.split(' - ', 1)[0],
                    'track': track.title.split(' - ', 1)[1],
                    'stream_link': self.get_stream_link(track.stream_url),
                    'image_link': self.get_image_link(track.artwork_url),
                    'time': self.get_track_time(track.duration / 1000),
                    'ttime': int(math.floor(float(track.duration / 1000)))
                }
            except Exception as e:
                continue

    def get_track_time(self, lenght):
        minute = math.floor(int(lenght) / 60.)
        second = int(lenght) - minute * 60
        return '%02d:%02d' % (minute, second)

    def get_image_link(self, link):
        if not link:
            return os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'img/no-photo.png')
        link = link.replace('-large', '-t500x500')
        try:
            filename = link.split('/')[-1]
            filepath = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), 'downloads-soundclound/', filename)
            if not os.path.exists(filepath):
                fle = cStringIO.StringIO(urllib.urlopen(link).read())
                img = Image.open(fle)
                img.save(filepath)
            return filepath

        except (KeyError, IndexError):
            return os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'img/no-photo.png')

    def get_stream_link(self, link):
        link = '%s?consumer_key=%s' % (link, SOUNDCLOUND_ID)
        u = urllib.urlopen(link)
        return u.url.replace('https://', 'http://')