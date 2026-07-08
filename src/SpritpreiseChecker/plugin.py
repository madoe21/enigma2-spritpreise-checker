# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os

from Components.config import (
    ConfigInteger,
    ConfigSelection,
    ConfigSubsection,
    ConfigText,
    config,
)
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import SCOPE_PLUGINS, resolveFilename

from . import _
from .core.api import SpritpreiseCheckerApiClient
from .screens import SpritpreiseCheckerMainScreen, SpritpreiseCheckerSettingsScreen
from .core.store import SpritpreiseCheckerStore

SETTINGS_FILE = "/etc/enigma2/settings"

# True: use aspect-specific transparent icon files (no cropping, no clipping).
# False: always use the original plugin.png (can look larger but may be stretched by skin).
USE_ASPECT_ICON_VARIANTS = True

if not hasattr(config.plugins, "spritpreisechecker"):
    config.plugins.spritpreisechecker = ConfigSubsection()

config.plugins.spritpreisechecker.fuel_type = ConfigSelection(
    default="diesel",
    choices=[("diesel", "Diesel"), ("e5", "Super E5"), ("e10", "Super E10")],
)
config.plugins.spritpreisechecker.plz = ConfigText(default="", fixed_size=False)
config.plugins.spritpreisechecker.street = ConfigText(default="", fixed_size=False)
config.plugins.spritpreisechecker.house_number = ConfigText(default="", fixed_size=False)
config.plugins.spritpreisechecker.radius = ConfigInteger(default=5, limits=(1, 25))
config.plugins.spritpreisechecker.map_zoom = ConfigInteger(default=17, limits=(12, 19))
config.plugins.spritpreisechecker.api_key = ConfigText(default="", fixed_size=False)


class AppContext(object):
    def __init__(self):
        self._load_settings_from_file()
        self.store = SpritpreiseCheckerStore()
        self.api = SpritpreiseCheckerApiClient(self.store)

    def _load_settings_from_file(self):
        # Fallback: read values directly from Enigma2 settings if available.
        if not os.path.exists(SETTINGS_FILE):
            return

        values = {}
        try:
            with open(SETTINGS_FILE, "r") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or not line.startswith("config.plugins.spritpreisechecker."):
                        continue
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    values[key] = value.strip()
        except Exception:
            return

        fuel = values.get("config.plugins.spritpreisechecker.fuel_type")
        plz = values.get("config.plugins.spritpreisechecker.plz")
        street = values.get("config.plugins.spritpreisechecker.street")
        house_number = values.get("config.plugins.spritpreisechecker.house_number")
        radius = values.get("config.plugins.spritpreisechecker.radius")
        map_zoom = values.get("config.plugins.spritpreisechecker.map_zoom")
        api_key = values.get("config.plugins.spritpreisechecker.api_key")

        if fuel:
            fuel = fuel.strip().lower()
            if fuel in ("diesel", "e5", "e10"):
                config.plugins.spritpreisechecker.fuel_type.value = fuel
        if plz:
            plz = "".join([ch for ch in plz if ch.isdigit()])
            config.plugins.spritpreisechecker.plz.value = plz[:5]
        if street is not None:
            config.plugins.spritpreisechecker.street.value = street.strip()
        if house_number is not None:
            config.plugins.spritpreisechecker.house_number.value = house_number.strip()
        if radius:
            try:
                config.plugins.spritpreisechecker.radius.value = int(radius)
            except Exception:
                pass
        if map_zoom:
            try:
                config.plugins.spritpreisechecker.map_zoom.value = int(map_zoom)
            except Exception:
                pass
        if api_key:
            config.plugins.spritpreisechecker.api_key.value = api_key

    def _normalize_plz(self, value):
        text = (value or "").strip()
        digits = "".join([ch for ch in text if ch.isdigit()])
        if len(digits) != 5:
            return ""
        return digits

    def settings_complete(self):
        return bool(self.get_api_key() and self.get_plz() and self.get_radius() > 0 and self.get_fuel_type())

    def get_fuel_type(self):
        value = (config.plugins.spritpreisechecker.fuel_type.value or "").strip().lower()
        if value in ("diesel", "e5", "e10"):
            return value
        return ""

    def get_plz(self):
        return self._normalize_plz(config.plugins.spritpreisechecker.plz.value)

    def get_radius(self):
        try:
            value = int(config.plugins.spritpreisechecker.radius.value)
            if value < 1:
                return 1
            if value > 25:
                return 25
            return value
        except Exception:
            return 5

    def get_api_key(self):
        return (config.plugins.spritpreisechecker.api_key.value or "").strip()

    def get_street(self):
        return (config.plugins.spritpreisechecker.street.value or "").strip()

    def get_house_number(self):
        return (config.plugins.spritpreisechecker.house_number.value or "").strip()

    def get_map_zoom(self):
        try:
            value = int(config.plugins.spritpreisechecker.map_zoom.value)
            if value < 12:
                return 12
            if value > 19:
                return 19
            return value
        except Exception:
            return 17

    def refresh_prices(self):
        fuel_type = self.get_fuel_type()
        plz = self.get_plz()
        street = self.get_street()
        house_number = self.get_house_number()
        radius = self.get_radius()
        api_key = self.get_api_key()

        stations, updated, error = self.api.fetch_prices(api_key, plz, radius, street, house_number)
        if stations:
            self.store.save_price_cache(stations, fuel_type, plz, radius)
            return {
                "stations": stations,
                "updated": updated,
                "error": None,
                "from_cache": False,
            }

        cache = self.store.load_price_cache()
        cached_stations = cache.get("stations") if isinstance(cache, dict) else []
        cache_radius = -1
        try:
            cache_radius = int(cache.get("radius", -1)) if isinstance(cache, dict) else -1
        except Exception:
            cache_radius = -1

        cache_matches_query = bool(
            isinstance(cache, dict)
            and str(cache.get("plz", "")) == str(plz)
            and cache_radius == int(radius)
            and str(cache.get("fuel_type", "")) == str(fuel_type)
        )

        if cache_matches_query and isinstance(cached_stations, list) and cached_stations:
            return {
                "stations": cached_stations,
                "updated": cache.get("updated"),
                "error": error,
                "from_cache": True,
            }

        return {
            "stations": [],
            "updated": updated,
            "error": error,
            "from_cache": False,
        }


_APP = None


def get_app():
    global _APP
    if _APP is None:
        _APP = AppContext()
    return _APP


def main(session, **kwargs):
    app = get_app()
    if app.settings_complete():
        session.open(SpritpreiseCheckerMainScreen, app)
    else:
        session.open(SpritpreiseCheckerSettingsScreen, app, True)


def _icon_file_for_aspect_ratio():
    try:
        from enigma import getDesktop

        size = getDesktop(0).size()
        width = int(size.width())
        height = int(size.height())
        if height > 0:
            ratio = float(width) / float(height)
            if ratio < 1.5:
                return "plugin_4x3.png"
            if ratio < 1.7:
                return "plugin_16x10.png"
            return "plugin_16x9.png"
    except Exception:
        pass

    return "plugin_16x9.png"


def _resolve_plugin_icon_path():
    if not USE_ASPECT_ICON_VARIANTS:
        return resolveFilename(SCOPE_PLUGINS, "Extensions/SpritpreiseChecker/res/plugin.png")

    icon_name = _icon_file_for_aspect_ratio()
    icon_path = resolveFilename(SCOPE_PLUGINS, "Extensions/SpritpreiseChecker/res/%s" % icon_name)
    if os.path.exists(icon_path):
        return icon_path
    return resolveFilename(SCOPE_PLUGINS, "Extensions/SpritpreiseChecker/res/plugin.png")


def Plugins(**kwargs):
    plugin_icon = _resolve_plugin_icon_path()
    return [
        PluginDescriptor(
            name=_("Spritpreise-Checker"),
            description=_("Spritpreise-Checker"),
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon=plugin_icon,
            fnc=main,
        )
    ]
