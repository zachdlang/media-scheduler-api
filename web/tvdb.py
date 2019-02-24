# Standard library imports
import os
import requests
import json
from urllib.request import urlretrieve

# Third party imports
from flask import url_for, current_app as app
from PIL import Image

# Local imports
from sitetools.utility import get_static_file


class TVDBException(Exception):
	pass


def get_headers():
	headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json',
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
	}
	return headers


def login():
	data = {
		'apikey': app.config['TVDB_APIKEY'],
		'userkey': app.config['TVDB_USERKEY'],
		'username': app.config['TVDB_USERNAME']
	}
	headers = get_headers()
	resp = requests.post('https://api.thetvdb.com/login', data=json.dumps(data), headers=headers)
	if resp.status_code == 503:
		raise TVDBException('TVDB currently down. Please try again later.')
	resp = json.loads(resp.text)
	if 'Error' in resp:
		raise TVDBException(resp['Error'])
	return resp['token']


def send_request(url, params, token=None):
	if token is None:
		token = login()
	headers = get_headers()
	headers['Authorization'] = 'Bearer %s' % token
	r = requests.get(url, params=params, headers=headers).text
	resp = json.loads(r)
	if 'Error' in resp:
		if resp['Error'].lower() == 'resource not found':
			# No search results
			resp['data'] = []
		else:
			raise TVDBException(resp['Error'])
	return resp


def series_search(name):
	params = {'name': name}
	resp = send_request('https://api.thetvdb.com/search/series', params)
	return resp['data']


def episode_search(tvshow_tvdb_id, airdate, token=None):
	params = {'firstAired': airdate}
	try:
		resp = send_request('https://api.thetvdb.com/series/%s/episodes/query' % tvshow_tvdb_id, params, token=token)
	except TVDBException as e:
		if 'No results for your query' in str(e):
			resp = {'data': []}
		else:
			raise
	return resp['data']


def image_search(tvshow_tvdb_id):
	params = {'keyType': 'poster'}
	resp = send_request('https://api.thetvdb.com/series/%s/images/query' % tvshow_tvdb_id, params)
	return resp['data']


def get_poster(tvdb_id):
	if not os.path.exists(get_static_file('/images/poster_%s.jpg' % tvdb_id)):
		try:
			resp = image_search(tvdb_id)
		except TVDBException as e:
			print(e)
			return None
		if len(resp) > 0:
			top_poster = resp[0]
			for r in resp:
				if r['ratingsInfo']['average'] > top_poster['ratingsInfo']['average']:
					top_poster = r
		urlretrieve('http://thetvdb.com/banners/%s' % top_poster['fileName'], get_static_file('/images/poster_%s.jpg' % tvdb_id))
		img = Image.open(get_static_file('/images/poster_%s.jpg' % tvdb_id))
		img_scaled = img.resize((int(img.size[0] / 2), int(img.size[1] / 2)), Image.ANTIALIAS)
		img_scaled.save(get_static_file('/images/poster_%s.jpg' % tvdb_id), optimize=True, quality=95)
	return url_for('static', filename='images/poster_%s.jpg' % tvdb_id)
