#!flask/bin/python
from flask import Flask, request, abort, render_template, Response, g
from pathlib import Path
from shapely.geometry import Point, Polygon
import xml.etree.ElementTree as ET
import fiona
import json
import os
import pendulum
import secrets
import pprint
pp = pprint.PrettyPrinter(indent=2)

SCRIPTPATH = os.path.dirname(os.path.abspath(__file__))
TRACKER_TIMEZONE = os.getenv('TRACKER_TIMEZONE', 'America/Los_Angeles')
TRACKER_METRIC_UNITS = os.getenv('TRACKER_METRIC_UNITS') == 'True'

app = Flask(__name__)

def write_log(trackpoint):
    # Write raw trackpoint data to log file
    now = pendulum.now(TRACKER_TIMEZONE)
    logfile = now.format('YYYYMMDD') + '.json'
    with open(f"{SCRIPTPATH}/logs/{logfile}", 'a') as f:
        f.write(json.dumps(trackpoint) + "\n")

def write_track(trackpoint):
    # Write trackpoint to track file
    now = pendulum.now(TRACKER_TIMEZONE)
    date = now.format('YYYYMMDD')
    trackfile = f"{SCRIPTPATH}/tracks/{date}.xml"
    if os.path.isfile(trackfile):
        tree = ET.parse(trackfile)
        root = tree.getroot()
        markers = root.find('markers')
    else:
        root = ET.Element('track')
        markers = ET.SubElement(root, 'markers')
        tree = ET.ElementTree(root)

    marker = {}
    if trackpoint['timestamp'] == None:
        return False
    else:
        marker['id'] = trackpoint['timestamp']
        time = pendulum.from_timestamp(int(trackpoint['timestamp']) / 1000, tz=TRACKER_TIMEZONE)
        marker['time'] = time.to_rfc2822_string()
    if trackpoint['latitude'] == None:
        return False
    else:
        marker['lat'] = str(trackpoint['latitude'])
    if trackpoint['longitude'] == None:
        return False
    else:
        marker['lon'] = str(trackpoint['longitude'])
    if not trackpoint['hdop'] == None:
        marker['hdop'] = trackpoint['hdop']
    if not trackpoint['altitude'] == None:
        if TRACKER_METRIC_UNITS:
            altitude = "{}m".format(trackpoint['altitude'])
        else:
            altitude = "{}ft".format(round(trackpoint['altitude'] * 3.280839895, 2))
        marker['altitude'] = altitude
    if not trackpoint['speed'] == None:
        if TRACKER_METRIC_UNITS:
            speed = "{}kph".format(round(trackpoint['speed'] * 0.001 * 60 * 60, 2))
        else:
            speed = "{}mph".format(round(trackpoint['speed'] / 1000 * 60 * 60 * 0.62137, 2))
        marker['speed'] = speed
    if not trackpoint['bearing'] == None:
        cardinal_directions = [ 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'N' ]
        marker['bearing'] = cardinal_directions[round((trackpoint['bearing'] % 360) / 45)]

    ET.SubElement(markers, 'marker', marker)
    tree.write(trackfile)
    return True

def in_securezone(lat=0, lon=0):
    # Returns True if coordinates are within the defined secure zone
    point = Point(lon, lat)
    with fiona.open(SCRIPTPATH + '/securezone.geojson', 'r') as securezone:
        for polygon in securezone:
            g = polygon['geometry']
            assert g['type'] == "Polygon"
            # pp.pprint(g['coordinates'][0])
            polygon = Polygon(g['coordinates'][0])
            return polygon.contains(point)
    return True

def get_adjacent_tracks(date):
    date_str = date.format('YYYYMMDD')

    tracks = list(map(lambda t: t.stem, Path('tracks/').glob('*.xml')))
    tracks.append(date_str)
    tracks = sorted(set(tracks))

    prev_track = ''
    next_track = ''
    for i, v in enumerate(tracks):
        if v == date_str:
            prev_track = tracks[i-1] if i-1 > -1 else ''
            next_track = tracks[i+1] if i+1 < len(tracks) else ''
    return (prev_track, next_track)

@app.route('/')
def index():
    return "These aren't the droids you're looking for."

@app.route('/log', methods=['GET'])
def log():
    # Log trackpoint from OsmAnd
    #
    # Query Params:
    #   lat: REQUIRED latitude value
    #   lon: REQUIRED longitude value
    #   timestamp: REQUIRED timestamp (example: 1508102861383)
    #   hdop: horizontal dilution of precision
    #   altitude:
    #   speed:
    #   bearing:
    #   key: REQUIRED device key, must match key defined in environment variable
    key = request.args.get('key')
    if not key == os.getenv('TRACKER_DEVICE_KEY', secrets.token_hex(16)): abort(403)

    trackpoint = {
        'latitude': float(request.args.get('lat')), #float('44.54562'),
        'longitude': float(request.args.get('lon')), #float('-122.31106'), #-123 inside securezone
        'timestamp': request.args.get('timestamp'), #'1508102861383',
        'hdop': request.args.get('hdop'), #'4.5509996',
        'altitude': float(request.args.get('altitude')), #float('161'),
        'speed': float(request.args.get('speed')), #float('22.09'),
        'bearing': float(request.args.get('bearing')) #float('256.4')
    }
    pp.pprint(trackpoint)
    write_log(trackpoint)
    if in_securezone(lat=trackpoint['latitude'], lon=trackpoint['longitude']): return ''
    write_track(trackpoint)
    return 'OK'

@app.route('/track/<int:date>', methods=['GET'])
def get_track(date):
    trackfile = f"{SCRIPTPATH}/tracks/{date}.xml"
    if os.path.isfile(trackfile):
        with open(trackfile, 'r') as tf:
            return Response(tf.read(), mimetype='text/xml')
    return ''

@app.route('/view', methods=['GET'])
def view():
    if request.args.get('date'):
        date = pendulum.from_format(request.args.get('date'), 'YYYYMMDD')
    else:
        date = pendulum.now(TRACKER_TIMEZONE)
    (g.previous_track, g.next_track) = get_adjacent_tracks(date)
    print("previous_track: "+g.previous_track)
    print("next_track: "+g.next_track)

    g.GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')
    return render_template('base.html')

if __name__ == '__main__':
    app.run(debug=True)
