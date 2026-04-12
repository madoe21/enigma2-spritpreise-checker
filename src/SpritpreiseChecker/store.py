# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import os
import time

CACHE_FILE = "/etc/enigma2/spritpreisechecker_cache.json"
GEO_FILE = "/etc/enigma2/spritpreisechecker_geo.json"


class SpritpreiseCheckerStore(object):
    def __init__(self, cache_file=CACHE_FILE, geo_file=GEO_FILE):
        self.cache_file = cache_file
        self.geo_file = geo_file

    def _read_json(self, path, fallback):
        try:
            with open(path, "r") as handle:
                return json.load(handle)
        except Exception:
            return fallback

    def _write_json(self, path, data):
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
        with open(path, "w") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)

    def save_price_cache(self, stations, fuel_type, plz, radius):
        payload = {
            "updated": int(time.time()),
            "fuel_type": fuel_type,
            "plz": str(plz),
            "radius": int(radius),
            "stations": stations or [],
        }
        self._write_json(self.cache_file, payload)

    def load_price_cache(self):
        data = self._read_json(self.cache_file, {})
        if not isinstance(data, dict):
            return {}
        if not isinstance(data.get("stations"), list):
            data["stations"] = []
        return data

    def get_coordinates(self, key):
        data = self._read_json(self.geo_file, {})
        if not isinstance(data, dict):
            return None
        value = data.get(str(key))
        if not isinstance(value, dict):
            return None
        lat = value.get("lat")
        lng = value.get("lng")
        if lat is None or lng is None:
            return None
        return value

    def set_coordinates(self, key, lat, lng):
        data = self._read_json(self.geo_file, {})
        if not isinstance(data, dict):
            data = {}
        data[str(key)] = {"lat": float(lat), "lng": float(lng)}
        self._write_json(self.geo_file, data)
