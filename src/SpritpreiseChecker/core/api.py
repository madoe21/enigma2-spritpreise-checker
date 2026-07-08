# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import time

try:
    from urllib import urlencode
    from urllib2 import Request, URLError, urlopen
except ImportError:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    from urllib.error import URLError


class SpritpreiseCheckerApiClient(object):
    LIST_ENDPOINT = "https://creativecommons.tankerkoenig.de/json/list.php"
    NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"

    def __init__(self, store):
        self.store = store

    def _normalize_text(self, value):
        return (value or "").strip()

    def _geo_cache_key(self, plz, street="", house_number=""):
        key_plz = self._normalize_text(str(plz))
        key_street = self._normalize_text(street).lower()
        key_house = self._normalize_text(house_number).lower()
        return "%s|%s|%s" % (key_plz, key_street, key_house)

    def _get_json(self, url, timeout=12, user_agent=None):
        headers = {}
        if user_agent:
            headers["User-Agent"] = user_agent
        req = Request(url, headers=headers)
        response = urlopen(req, timeout=timeout)
        raw = response.read()
        if not isinstance(raw, str):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def geocode_location(self, plz, street="", house_number=""):
        cache_key = self._geo_cache_key(plz, street, house_number)
        cached = self.store.get_coordinates(cache_key)
        if cached:
            return cached.get("lat"), cached.get("lng"), None

        street = self._normalize_text(street)
        house_number = self._normalize_text(house_number)

        query_candidates = []
        if street:
            street_line = ("%s %s" % (house_number, street)).strip()
            query_candidates.append(
                {
                    "country": "de",
                    "postalcode": str(plz),
                    "street": street_line,
                    "format": "json",
                    "limit": 1,
                }
            )

        # Always keep ZIP-only fallback for robustness.
        query_candidates.append(
            {
                "country": "de",
                "postalcode": str(plz),
                "format": "json",
                "limit": 1,
            }
        )

        try:
            for query in query_candidates:
                params = urlencode(query)
                url = "%s?%s" % (self.NOMINATIM_ENDPOINT, params)
                data = self._get_json(url, timeout=12, user_agent="enigma2-spritpreise-checker-plugin/1.0")
                if not data:
                    continue
                first = data[0]
                lat = float(first.get("lat"))
                lng = float(first.get("lon"))
                self.store.set_coordinates(cache_key, lat, lng)
                return lat, lng, None
            return None, None, "No geocoding result"
        except Exception as exc:
            return None, None, str(exc)

    def geocode_zip(self, plz):
        return self.geocode_location(plz)

    def fetch_prices(self, api_key, plz, radius, street="", house_number=""):
        lat, lng, geo_error = self.geocode_location(plz, street, house_number)
        if geo_error:
            return None, None, "Geocoding failed: %s" % geo_error

        params = urlencode(
            {
                "lat": "%.6f" % lat,
                "lng": "%.6f" % lng,
                "rad": int(radius),
                "sort": "dist",
                "type": "all",
                "apikey": api_key,
            }
        )
        url = "%s?%s" % (self.LIST_ENDPOINT, params)

        try:
            payload = self._get_json(url, timeout=12)
        except URLError as exc:
            return None, None, "Network error: %s" % exc
        except Exception as exc:
            return None, None, "API request failed: %s" % exc

        ok = payload.get("ok") if isinstance(payload, dict) else False
        stations = payload.get("stations") if isinstance(payload, dict) else None
        if not ok:
            message = payload.get("message", "Unknown API error") if isinstance(payload, dict) else "Invalid API response"
            return None, None, message

        if not isinstance(stations, list) or len(stations) == 0:
            return [], int(time.time()), "No stations returned"

        return stations, int(time.time()), None
