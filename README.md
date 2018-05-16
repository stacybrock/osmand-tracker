# osmand-tracker

## Requirements

* Python 3.6+
* GDAL
* packages in `requirements.txt`

Installing the required packages within a Python virtualenv is strongly recommended.

### Fiona on MacOS

I ran into issues with the PyPI package of Fiona on MacOS 10.12.6 where Fiona would throw `Symbol not found: _sqlite3_column_table_name` or similar errors. As a workaround, install Fiona by compiling it from source.

```
(tracker-virtualenv)$ brew install gdal
(tracker-virtualenv)$ git clone git://github.com/Toblerity/Fiona.git
(tracker-virtualenv)$ cd Fiona
(tracker-virtualenv)$ python setup.py build_ext -I/path/to/gdal/include -L/path/to/gdal/lib -lgdal install
```

## Configuration

```
TRACKER_DEVICE_KEY
TRACKER_TIMEZONE https://www.iana.org/time-zones
TRACKER_METRIC_UNITS True or False
GOOGLE_MAPS_API_KEY
```
