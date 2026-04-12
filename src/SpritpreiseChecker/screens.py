# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import time
import math

try:
    from urllib2 import Request, urlopen
except ImportError:
    from urllib.request import Request, urlopen

from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.config import config, configfile, getConfigListEntry
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import SCOPE_PLUGINS, resolveFilename

try:
    from enigma import RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, eListboxPythonMultiContent, gFont, ePoint
except Exception:
    RT_HALIGN_LEFT = 0
    RT_HALIGN_RIGHT = 0
    RT_VALIGN_CENTER = 0
    eListboxPythonMultiContent = None
    gFont = None
    ePoint = None

from . import _

try:
    from Components.Input import Input
    from Screens.InputBox import InputBox
except Exception:
    Input = None
    InputBox = None


class SpritpreiseCheckerMainScreen(Screen):
    INITIAL_CACHE_MAX_AGE = 300

    skin = """
        <screen name="SpritpreiseCheckerMainScreen" position="center,90" size="1180,640" title="Spritpreise-Checker">
            <widget source="title" render="Label" position="20,10" size="1140,36" font="Regular;30" />
            <widget name="updated" position="20,50" size="560,28" font="Regular;22" />
            <widget name="sort_mode" position="600,50" size="560,28" font="Regular;22" halign="right" />
            <widget name="header_station" position="20,84" size="760,28" font="Regular;22" />
            <widget name="header_price" position="770,84" size="180,28" font="Regular;22" halign="right" />
            <widget name="header_distance" position="960,84" size="180,28" font="Regular;22" halign="right" />
            <widget name="list" position="20,115" size="1140,440" scrollbarMode="showOnDemand" />
            <widget source="support" render="Label" position="20,560" size="1140,24" font="Regular;18" foregroundColor="#666666" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,590" size="220,30" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="250,590" size="220,30" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="480,590" size="220,30" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="710,590" size="220,30" alphatest="on" />
            <widget source="key_red" render="Label" position="20,590" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
            <widget source="key_green" render="Label" position="250,590" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
            <widget source="key_yellow" render="Label" position="480,590" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
            <widget source="key_blue" render="Label" position="710,590" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
        </screen>
    """

    def __init__(self, session, app):
        Screen.__init__(self, session)
        self.app = app
        self._rows = []
        self._stations = []
        self._sort_mode = "price_asc"
        self._station_col_width = 60
        self._col_station_x = 0
        self._col_station_w = 760
        self._col_price_x = 750
        self._col_price_w = 180
        self._col_distance_x = 940
        self._col_distance_w = 180
        self._use_multicontent = eListboxPythonMultiContent is not None

        self["title"] = StaticText(_("Spritpreise-Checker"))
        self["updated"] = Label(_("Updated") + ": -")
        self["sort_mode"] = Label("")
        self["header_station"] = Label(_("Station"))
        self["header_price"] = Label(_("Price"))
        self["header_distance"] = Label(_("Distance"))
        if self._use_multicontent:
            self["list"] = MenuList([], content=eListboxPythonMultiContent)
        else:
            self["list"] = MenuList([])

        if gFont is not None:
            try:
                self["list"].l.setFont(0, gFont("Regular", 22))
                self["list"].l.setItemHeight(34)
            except Exception:
                pass
        self["support"] = StaticText("Buy me a coffee: https://buymeacoffee.com/madoe21")

        self["key_red"] = StaticText(_("Close"))
        self["key_green"] = StaticText(_("Refresh"))
        self["key_yellow"] = StaticText(_("Settings"))
        self["key_blue"] = StaticText(_("Information"))

        self["actions"] = ActionMap(
            ["ColorActions", "OkCancelActions", "DirectionActions", "MenuActions"],
            {
                "ok": self.open_selected_station_map,
                "cancel": self.close,
                "red": self.close,
                "green": self.refresh,
                "yellow": self.open_settings,
                "blue": self.open_info,
                "left": self.toggle_sort_mode,
                "right": self.toggle_sort_mode,
                "menu": self.open_main_menu,
            },
            -1,
        )

        self.onLayoutFinish.append(self.load_initial_data)

    def load_initial_data(self):
        if not self.app.settings_complete():
            self.session.open(SpritpreiseCheckerSettingsScreen, self.app, True)
            return

        cache = self.app.store.load_price_cache()
        stations = cache.get("stations") if isinstance(cache, dict) else []
        if isinstance(stations, list) and stations:
            self._stations = stations
            self._apply_sort_and_render()
            self._set_updated(cache.get("updated"))

            # Auto-refresh on startup only when cache is older than 5 minutes.
            try:
                age = max(0, int(time.time()) - int(cache.get("updated") or 0))
            except Exception:
                age = self.INITIAL_CACHE_MAX_AGE + 1

            if age > self.INITIAL_CACHE_MAX_AGE:
                self.refresh(show_cache_info=False)
            return

        self.refresh(show_cache_info=False)
    def _cache_matches_current(self, cache):
        if not isinstance(cache, dict):
            return False
        try:
            cache_radius = int(cache.get("radius", -1))
        except Exception:
            cache_radius = -1
        return bool(
            str(cache.get("plz", "")) == str(self.app.get_plz())
            and cache_radius == int(self.app.get_radius())
            and str(cache.get("fuel_type", "")) == str(self.app.get_fuel_type())
        )

    def load_initial(self):
        if not self.app.settings_complete():
            self.session.open(SpritpreiseCheckerSettingsScreen, self.app, True)
            return

        cache = self.app.store.load_price_cache()
        cache_stations = cache.get("stations") if isinstance(cache, dict) else []
        cache_updated = cache.get("updated") if isinstance(cache, dict) else None
        cache_valid = self._cache_matches_current(cache) and isinstance(cache_stations, list) and bool(cache_stations)

        if cache_valid:
            self._stations = cache_stations
            self._apply_sort_and_render()
            self._set_updated(cache_updated)
            try:
                age = max(0, int(time.time()) - int(cache_updated or 0))
            except Exception:
                age = self.INITIAL_CACHE_MAX_AGE + 1
            if age <= self.INITIAL_CACHE_MAX_AGE:
                return

        self.refresh(show_cache_info=False)

    def _fmt_price(self, value):
        if value is None:
            return "-"
        try:
            formatted = "%.3f" % float(value)
            return formatted.replace(".", ",") + "€/l"
        except Exception:
            return "-"

    def _fmt_distance(self, value):
        if value is None:
            return "-"
        try:
            return "%.1f km" % float(value)
        except Exception:
            return "-"

    def _format_row(self, station):
        name = station.get("name") or "?"
        if len(name) > self._station_col_width:
            name = name[: self._station_col_width - 1] + "~"
        fuel = self.app.get_fuel_type() or "diesel"
        price = self._fmt_price(station.get(fuel))
        dist = self._fmt_distance(station.get("dist"))
        return name, price, dist

    def _format_row_text(self, name, price, dist):
        return "%s | %s | %s" % (name, price, dist)

    def _build_row_item(self, row):
        station = row[1]
        name = row[2]
        price = row[3]
        dist = row[4]
        return [
            station,
            MultiContentEntryText(
                pos=(self._col_station_x, 0),
                size=(self._col_station_w, 34),
                font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=name,
            ),
            MultiContentEntryText(
                pos=(self._col_price_x, 0),
                size=(self._col_price_w, 34),
                font=0,
                flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER,
                text=price,
            ),
            MultiContentEntryText(
                pos=(self._col_distance_x, 0),
                size=(self._col_distance_w, 34),
                font=0,
                flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER,
                text=dist,
            ),
        ]

    def _render_rows(self, stations):
        rows = []
        for station in stations or []:
            name, price, dist = self._format_row(station)
            rows.append((None, station, name, price, dist))

        self._rows = rows
        if not self._use_multicontent:
            labels = [self._format_row_text(row[2], row[3], row[4]) for row in rows]
            if not labels:
                labels = [_("No entries available")]
            self["list"].setList(labels)
            return

        if not rows:
            self["list"].setList(
                [
                    [
                        None,
                        MultiContentEntryText(
                            pos=(0, 0),
                            size=(1140, 34),
                            font=0,
                            flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                            text=_("No entries available"),
                        ),
                    ]
                ]
            )
            return

        self["list"].setList([self._build_row_item(row) for row in rows])

    def _to_float(self, value, fallback=999999.0):
        try:
            return float(value)
        except Exception:
            return float(fallback)

    def _sort_stations(self, stations):
        items = list(stations or [])
        if self._sort_mode == "price_asc":
            fuel = self.app.get_fuel_type() or "diesel"
            items.sort(key=lambda station: self._to_float((station or {}).get(fuel)))
            return items

        items.sort(key=lambda station: self._to_float((station or {}).get("dist")))
        return items

    def _sort_mode_label(self):
        if self._sort_mode == "price_asc":
            return _("Price per liter (ascending)")
        return _("Distance (ascending)")

    def _update_sort_mode_label(self):
        self["sort_mode"].setText(_("Sort by") + ": " + self._sort_mode_label())

    def _apply_sort_and_render(self):
        sorted_stations = self._sort_stations(self._stations)
        self._render_rows(sorted_stations)
        self._update_sort_mode_label()

    def toggle_sort_mode(self):
        if self._sort_mode == "price_asc":
            self._sort_mode = "distance_asc"
        else:
            self._sort_mode = "price_asc"
        self._apply_sort_and_render()

    def sort_by_price(self):
        self._sort_mode = "price_asc"
        self._apply_sort_and_render()
        self.session.open(MessageBox, _("Sort") + ": " + self._sort_mode_label(), MessageBox.TYPE_INFO, timeout=2)

    def sort_by_distance(self):
        self._sort_mode = "distance_asc"
        self._apply_sort_and_render()
        self.session.open(MessageBox, _("Sort") + ": " + self._sort_mode_label(), MessageBox.TYPE_INFO, timeout=2)

    def _set_updated(self, ts):
        if not ts:
            self["updated"].setText(_("Updated") + ": -")
            return
        formatted = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(int(ts)))
        self["updated"].setText(_("Updated") + ": " + formatted)

    def _get_selected_station(self):
        if not self._rows:
            return None
        index = 0
        try:
            index = int(self["list"].getSelectionIndex())
        except Exception:
            try:
                index = int(self["list"].getSelectedIndex())
            except Exception:
                index = 0

        if index < 0 or index >= len(self._rows):
            return None
        return self._rows[index][1]

    def open_selected_station_map(self):
        station = self._get_selected_station()
        if not station:
            self.session.open(MessageBox, _("No entries available"), MessageBox.TYPE_INFO, timeout=3)
            return

        lat = station.get("lat")
        lng = station.get("lng")
        if lng is None:
            lng = station.get("lon")

        if lat is None or lng is None:
            self.session.open(MessageBox, _("No coordinates available for this station"), MessageBox.TYPE_ERROR, timeout=4)
            return

        try:
            lat = float(lat)
            lng = float(lng)
        except Exception:
            self.session.open(MessageBox, _("No coordinates available for this station"), MessageBox.TYPE_ERROR, timeout=4)
            return
        self.session.open(SpritpreiseCheckerMapScreen, self.app, station, lat, lng)

    def refresh(self, show_cache_info=True):
        if not self.app.settings_complete():
            self.session.open(SpritpreiseCheckerSettingsScreen, self.app, True)
            return

        result = self.app.refresh_prices()
        self._stations = result.get("stations") or []
        self._apply_sort_and_render()
        self._set_updated(result.get("updated"))

        if show_cache_info and result.get("from_cache"):
            text = _("Using cached data")
            if result.get("error"):
                text = "%s (%s)" % (text, result.get("error"))
            self.session.open(MessageBox, text, MessageBox.TYPE_INFO, timeout=5)

    def open_settings(self):
        # Return quickly to main screen; avoid blocking network call on close.
        self.session.openWithCallback(lambda *args: self.load_initial_data(), SpritpreiseCheckerSettingsScreen, self.app, False)

    def open_info(self):
        self.session.open(SpritpreiseCheckerInfoScreen)

    def open_main_menu(self):
        options = [
            (_("Close"), "close"),
            (_("Refresh"), "refresh"),
            (_("Sort by price per liter (ascending)"), "sort_price"),
            (_("Sort by distance (ascending)"), "sort_distance"),
            (_("Settings"), "settings"),
            (_("Information"), "info"),
        ]
        self.session.openWithCallback(
            self._on_main_menu_choice,
            ChoiceBox,
            title=_("Main menu"),
            list=options,
        )

    def _on_main_menu_choice(self, choice=None):
        if not choice:
            return
        action = choice[1]
        if action == "close":
            self.close()
        elif action == "refresh":
            self.refresh()
        elif action == "sort_price":
            self.sort_by_price()
        elif action == "sort_distance":
            self.sort_by_distance()
        elif action == "settings":
            self.open_settings()
        elif action == "info":
            self.open_info()


class SpritpreiseCheckerMapScreen(Screen):
    skin = """
        <screen name="SpritpreiseCheckerMapScreen" position="center,90" size="1080,620" title="Spritpreise-Checker Karte">
            <widget source="title" render="Label" position="20,10" size="1040,35" font="Regular;30" />
            <widget name="station" position="20,50" size="1040,36" font="Regular;22" />
            <widget name="details" position="20,84" size="280,56" font="Regular;20" />
            <widget name="tile_0_0" position="306,96" size="156,156" alphatest="blend" scale="1" />
            <widget name="tile_1_0" position="462,96" size="156,156" alphatest="blend" scale="1" />
            <widget name="tile_2_0" position="618,96" size="156,156" alphatest="blend" scale="1" />
            <widget name="tile_0_1" position="306,252" size="156,156" alphatest="blend" scale="1" />
            <widget name="tile_1_1" position="462,252" size="156,156" alphatest="blend" scale="1" />
            <widget name="tile_2_1" position="618,252" size="156,156" alphatest="blend" scale="1" />
            <widget name="tile_0_2" position="306,408" size="156,156" alphatest="blend" scale="1" />
            <widget name="tile_1_2" position="462,408" size="156,156" alphatest="blend" scale="1" />
            <widget name="tile_2_2" position="618,408" size="156,156" alphatest="blend" scale="1" />
            <widget name="marker" position="532,320" size="24,32" alphatest="blend" scale="1" zPosition="10" />
            <widget name="hint" position="20,540" size="1040,24" font="Regular;18" />
            <widget source="support" render="Label" position="20,565" size="1040,24" font="Regular;18" foregroundColor="#666666" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,590" size="220,30" alphatest="on" />
            <widget source="key_red" render="Label" position="20,590" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
        </screen>
    """

    TILE_ENDPOINT = "https://tile.openstreetmap.org"
    TILE_CACHE_DIR = "/tmp/spritpreisechecker_tilecache"
    MAP_ORIGIN_X = 306
    MAP_ORIGIN_Y = 96
    TILE_WIDGET_SIZE = 156
    TILE_GRID_SIZE = 3
    MARKER_W = 24
    MARKER_H = 32
    MARKER_ANCHOR_X = 12
    MARKER_ANCHOR_Y = 31

    def __init__(self, session, app, station, lat, lng):
        Screen.__init__(self, session)
        self.app = app
        self.station = station or {}
        self.lat = float(lat)
        self.lng = float(lng)
        self.zoom = 17
        try:
            self.zoom = int(self.app.get_map_zoom())
        except Exception:
            self.zoom = 17

        self["title"] = StaticText(_("Station map"))
        self["station"] = Label(self._station_line())
        self["details"] = Label(self._detail_line())
        self._tile_keys = []
        for dy in range(3):
            for dx in range(3):
                key = "tile_%d_%d" % (dx, dy)
                self._tile_keys.append(key)
                self[key] = Pixmap()
        self["marker"] = Pixmap()
        self._marker_path = os.path.join(os.path.dirname(__file__), "res", "map_pin.png")
        self["hint"] = Label(_("OK/Exit closes this map"))
        self["support"] = StaticText("Buy me a coffee: https://buymeacoffee.com/madoe21")
        self["key_red"] = StaticText(_("Close"))

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "WizardActions"],
            {
                "ok": self._close_map,
                "cancel": self._close_map,
                "red": self._close_map,
                "back": self._close_map,
            },
            -1,
        )

        self.onLayoutFinish.append(self._load_map)

    def _is_png(self, data):
        return bool(data and data[:8] == b"\x89PNG\r\n\x1a\n")

    def _deg2tile(self, lat, lon, zoom):
        n = float(2 ** zoom)
        x = int((lon + 180.0) / 360.0 * n)
        lat_rad = math.radians(lat)
        y = int((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return x, y

    def _deg2tile_float(self, lat, lon, zoom):
        n = float(2 ** zoom)
        x = (lon + 180.0) / 360.0 * n
        lat_rad = math.radians(lat)
        y = (1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n
        return x, y

    def _move_marker(self, pixel_x, pixel_y):
        if ePoint is None:
            return
        try:
            self["marker"].instance.move(ePoint(int(pixel_x), int(pixel_y)))
        except Exception:
            pass

    def _set_marker_pixmap(self):
        if not os.path.exists(self._marker_path):
            return
        try:
            self["marker"].instance.setPixmapFromFile(self._marker_path)
        except Exception:
            pass

    def _download_bytes(self, url):
        request = Request(url, headers={"User-Agent": "enigma2-spritpreise-checker-plugin/1.0"})
        response = urlopen(request, timeout=2)
        return response.read()

    def _station_line(self):
        name = str(self.station.get("name") or "?").strip()
        parts = [
            str(self.station.get("street") or "").strip(),
            str(self.station.get("houseNumber") or "").strip(),
            str(self.station.get("postCode") or "").strip(),
            str(self.station.get("place") or "").strip(),
        ]
        address = " ".join([part for part in parts if part])
        if not address:
            return name[:100]
        return (name + " | " + address)[:100]

    def _format_price_for_map(self, value):
        try:
            if value is None:
                return "-"
            number = float(value)
            return ("%.3f" % number).replace(".", ",") + " EUR/l"
        except Exception:
            return "-"

    def _format_distance_for_map(self, value):
        try:
            if value is None:
                return "-"
            number = float(value)
            return ("%.1f" % number).replace(".", ",") + " km"
        except Exception:
            return "-"

    def _detail_line(self):
        fuel_type = ""
        try:
            fuel_type = (self.app.get_fuel_type() or "").strip().lower()
        except Exception:
            fuel_type = ""

        price = self.station.get(fuel_type) if fuel_type else None
        if price is None:
            for fallback in ("diesel", "e5", "e10"):
                fallback_price = self.station.get(fallback)
                if fallback_price is not None:
                    price = fallback_price
                    break

        distance = self.station.get("dist")
        return _("Price") + ": " + self._format_price_for_map(price) + "\n" + _("Distance") + ": " + self._format_distance_for_map(distance)

    def _load_tile_map(self):
        try:
            tiles = self.TILE_GRID_SIZE
            center_x, center_y = self._deg2tile(self.lat, self.lng, self.zoom)
            center_xf, center_yf = self._deg2tile_float(self.lat, self.lng, self.zoom)
            offset = tiles // 2
            tile_paths = []

            if not os.path.isdir(self.TILE_CACHE_DIR):
                os.makedirs(self.TILE_CACHE_DIR)

            for dx in range(tiles):
                for dy in range(tiles):
                    tile_x = center_x + dx - offset
                    tile_y = center_y + dy - offset
                    if tile_x < 0 or tile_y < 0:
                        return False
                    cache_path = os.path.join(self.TILE_CACHE_DIR, "%d_%d_%d.png" % (self.zoom, tile_x, tile_y))
                    tile_paths.append((dx, dy, cache_path, tile_x, tile_y))

            # Ensure all tiles are fully available first.
            for _, _, cache_path, tile_x, tile_y in tile_paths:
                cache_ok = False
                if os.path.exists(cache_path):
                    try:
                        with open(cache_path, "rb") as handle:
                            cached = handle.read()
                        cache_ok = self._is_png(cached)
                    except Exception:
                        cache_ok = False

                if not cache_ok:
                    tile_url = "%s/%d/%d/%d.png" % (self.TILE_ENDPOINT, self.zoom, tile_x, tile_y)
                    tile_data = self._download_bytes(tile_url)
                    if not self._is_png(tile_data):
                        return False
                    temp_path = cache_path + ".part"
                    with open(temp_path, "wb") as handle:
                        handle.write(tile_data)
                    try:
                        os.rename(temp_path, cache_path)
                    except Exception:
                        # Fallback for filesystems where rename-overwrite may fail.
                        if os.path.exists(cache_path):
                            os.remove(cache_path)
                        os.rename(temp_path, cache_path)

            # Render in one pass so the map appears complete instead of growing tile-by-tile.
            for dx, dy, cache_path, _, _ in tile_paths:
                key = "tile_%d_%d" % (dx, dy)
                self[key].instance.setPixmapFromFile(cache_path)

            # Place the marker using fractional tile coordinates to avoid left/right/up/down drift.
            left_tile = center_x - offset
            top_tile = center_y - offset
            marker_local_x = (center_xf - float(left_tile)) * self.TILE_WIDGET_SIZE
            marker_local_y = (center_yf - float(top_tile)) * self.TILE_WIDGET_SIZE
            marker_x = self.MAP_ORIGIN_X + marker_local_x - float(self.MARKER_ANCHOR_X)
            marker_y = self.MAP_ORIGIN_Y + marker_local_y - float(self.MARKER_ANCHOR_Y)
            self._move_marker(marker_x, marker_y)

            return True
        except Exception:
            return False

    def _load_map(self):
        self._set_marker_pixmap()
        self["hint"].setText(_("Loading map tiles..."))
        if self._load_tile_map():
            self["hint"].setText(_("OK/Exit closes this map"))
            return

        # Fallback: show link if OSM tile map cannot be loaded on this box/network.
        self["hint"].setText(
            _("Map could not be loaded")
            + " | "
            + "https://www.openstreetmap.org/?mlat=%.6f&mlon=%.6f#map=%d/%.6f/%.6f"
            % (self.lat, self.lng, self.zoom, self.lat, self.lng)
        )

    def _close_map(self):
        self.close()


class SpritpreiseCheckerSettingsScreen(Screen, ConfigListScreen):
    skin = """
        <screen name="SpritpreiseCheckerSettingsScreen" position="center,100" size="980,560" title="Spritpreise-Checker Einstellungen">
            <widget source="title" render="Label" position="20,10" size="940,35" font="Regular;30" />
            <widget name="config" position="20,55" size="940,350" scrollbarMode="showOnDemand" />
            <widget source="hint" render="Label" position="20,415" size="940,50" font="Regular;18" />
            <widget source="support" render="Label" position="20,468" size="940,24" font="Regular;18" foregroundColor="#666666" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,520" size="220,30" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="250,520" size="220,30" alphatest="on" />
            <widget source="key_red" render="Label" position="20,520" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
            <widget source="key_green" render="Label" position="250,520" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
        </screen>
    """

    def __init__(self, session, app, open_main_on_save):
        Screen.__init__(self, session)
        self.app = app
        self.open_main_on_save = bool(open_main_on_save)

        self["title"] = StaticText(_("Settings"))
        self["hint"] = StaticText("")
        self["support"] = StaticText("Buy me a coffee: https://buymeacoffee.com/madoe21")
        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Save"))

        entries = [
            getConfigListEntry(_("Fuel type"), config.plugins.spritpreisechecker.fuel_type),
            getConfigListEntry(_("ZIP code"), config.plugins.spritpreisechecker.plz),
            getConfigListEntry(_("Street"), config.plugins.spritpreisechecker.street),
            getConfigListEntry(_("House number"), config.plugins.spritpreisechecker.house_number),
            getConfigListEntry(_("Radius (km)"), config.plugins.spritpreisechecker.radius),
            getConfigListEntry(_("Map zoom"), config.plugins.spritpreisechecker.map_zoom),
            getConfigListEntry(_("API key"), config.plugins.spritpreisechecker.api_key),
        ]
        ConfigListScreen.__init__(self, entries, session=session)
        try:
            self["config"].onSelectionChanged.append(self._update_help)
        except Exception:
            pass
        self._update_help()

        self["actions"] = ActionMap(
            ["SetupActions", "ColorActions", "OkCancelActions", "WizardActions"],
            {
                "save": self.key_green,
                "cancel": self.key_red,
                "green": self.key_green,
                "red": self.key_red,
                "ok": self.key_ok,
                "back": self.key_red,
            },
            -2,
        )

    def _sanitize_plz(self, value):
        text = (value or "").strip()
        return "".join([ch for ch in text if ch.isdigit()])

    def key_ok(self):
        current = self["config"].getCurrent()
        if current and Input is not None and InputBox is not None:
            if current[1] is config.plugins.spritpreisechecker.plz:
                self.session.openWithCallback(
                    self._on_plz_input,
                    InputBox,
                    title=_("ZIP code"),
                    text=config.plugins.spritpreisechecker.plz.value or "",
                    maxSize=5,
                    type=Input.NUMBER,
                )
                return
            if current[1] is config.plugins.spritpreisechecker.radius:
                self.session.openWithCallback(
                    self._on_radius_input,
                    InputBox,
                    title=_("Radius (km)"),
                    text=str(config.plugins.spritpreisechecker.radius.value or ""),
                    maxSize=2,
                    type=Input.NUMBER,
                )
                return
            if current[1] is config.plugins.spritpreisechecker.street:
                self.session.openWithCallback(
                    self._on_street_input,
                    InputBox,
                    title=_("Street"),
                    text=config.plugins.spritpreisechecker.street.value or "",
                    maxSize=50,
                    type=Input.TEXT,
                )
                return
            if current[1] is config.plugins.spritpreisechecker.house_number:
                self.session.openWithCallback(
                    self._on_house_number_input,
                    InputBox,
                    title=_("House number"),
                    text=config.plugins.spritpreisechecker.house_number.value or "",
                    maxSize=10,
                    type=Input.TEXT,
                )
                return
            if current[1] is config.plugins.spritpreisechecker.map_zoom:
                self.session.openWithCallback(
                    self._on_map_zoom_input,
                    InputBox,
                    title=_("Map zoom"),
                    text=str(config.plugins.spritpreisechecker.map_zoom.value or ""),
                    maxSize=2,
                    type=Input.NUMBER,
                )
                return

        try:
            ConfigListScreen.keyOK(self)
        except Exception:
            self.key_green()

    def _on_plz_input(self, value=None):
        if value is None:
            return
        digits = self._sanitize_plz(value)
        if len(digits) > 5:
            digits = digits[:5]
        config.plugins.spritpreisechecker.plz.value = digits

    def _on_radius_input(self, value=None):
        if value is None:
            return
        digits = "".join([ch for ch in str(value) if ch.isdigit()])
        if not digits:
            return
        try:
            config.plugins.spritpreisechecker.radius.value = int(digits)
        except Exception:
            pass

    def _on_map_zoom_input(self, value=None):
        if value is None:
            return
        digits = "".join([ch for ch in str(value) if ch.isdigit()])
        if not digits:
            return
        try:
            config.plugins.spritpreisechecker.map_zoom.value = int(digits)
        except Exception:
            pass

    def _on_street_input(self, value=None):
        if value is None:
            return
        config.plugins.spritpreisechecker.street.value = str(value).strip()

    def _on_house_number_input(self, value=None):
        if value is None:
            return
        config.plugins.spritpreisechecker.house_number.value = str(value).strip()

    def _update_help(self):
        current = self["config"].getCurrent()
        if not current:
            return
        item = current[1]
        text = _("Please fill all settings")
        if item is config.plugins.spritpreisechecker.fuel_type:
            text = _("Select the fuel type to display in the list")
        elif item is config.plugins.spritpreisechecker.plz:
            text = _("Enter your 5-digit ZIP code")
        elif item is config.plugins.spritpreisechecker.street:
            text = _("Optional: street for more precise distance")
        elif item is config.plugins.spritpreisechecker.house_number:
            text = _("Optional: house number for more precise distance")
        elif item is config.plugins.spritpreisechecker.radius:
            text = _("Enter search radius in km (1-25)")
        elif item is config.plugins.spritpreisechecker.map_zoom:
            text = _("Set map zoom level (12-19), higher means closer")
        elif item is config.plugins.spritpreisechecker.api_key:
            text = _("Enter your Tankerkoenig API key here")
        self["hint"].setText(text)

    def _is_valid(self):
        fuel = (config.plugins.spritpreisechecker.fuel_type.value or "").strip()
        plz = self._sanitize_plz(config.plugins.spritpreisechecker.plz.value)
        api_key = (config.plugins.spritpreisechecker.api_key.value or "").strip()

        try:
            radius = int(config.plugins.spritpreisechecker.radius.value)
        except Exception:
            radius = 0

        if len(plz) != 5:
            return False
        if not fuel or not api_key or radius <= 0:
            return False
        return True

    def key_green(self):
        config.plugins.spritpreisechecker.plz.value = self._sanitize_plz(config.plugins.spritpreisechecker.plz.value)
        config.plugins.spritpreisechecker.street.value = (config.plugins.spritpreisechecker.street.value or "").strip()
        config.plugins.spritpreisechecker.house_number.value = (config.plugins.spritpreisechecker.house_number.value or "").strip()

        if not self._is_valid():
            self.session.open(MessageBox, _("Please fill all settings") + " (PLZ: 5 Ziffern)", MessageBox.TYPE_ERROR, timeout=5)
            return

        for entry in self["config"].list:
            entry[1].save()
        config.plugins.spritpreisechecker.save()
        try:
            configfile.save()
        except Exception:
            pass

        self.session.open(MessageBox, _("Settings saved"), MessageBox.TYPE_INFO, timeout=3)

        if self.open_main_on_save:
            self.session.open(SpritpreiseCheckerMainScreen, self.app)
        self.close()

    def key_red(self):
        for entry in self["config"].list:
            try:
                entry[1].cancel()
            except Exception:
                pass
        self.close()

    def key_cancel(self):
        self.key_red()


class SpritpreiseCheckerInfoScreen(Screen):
    skin = """
        <screen name="SpritpreiseCheckerInfoScreen" position="center,90" size="1000,620" title="Spritpreise-Checker Info">
            <widget source="title" render="Label" position="20,10" size="960,40" font="Regular;34" />
            <widget name="body" position="20,55" size="690,520" font="Regular;24" scrollbarMode="showOnDemand" />
            <widget name="qr" position="740,100" size="240,240" alphatest="blend" />
            <widget source="support" render="Label" position="20,560" size="960,24" font="Regular;20" foregroundColor="#666666" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,585" size="220,30" alphatest="on" />
            <widget source="key_red" render="Label" position="20,585" size="220,30" font="Regular;24" halign="center" valign="center" transparent="1" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = StaticText(_("Information"))
        self["key_red"] = StaticText(_("Close"))
        self["support"] = StaticText("Buy me a coffee: https://buymeacoffee.com/madoe21")
        self["body"] = ScrollLabel(self._build_info_text())
        self["qr"] = Pixmap()
        self.onLayoutFinish.append(self._load_qr_png)

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "cancel": self.close,
                "ok": self.close,
                "red": self.close,
                "up": self["body"].pageUp,
                "down": self["body"].pageDown,
                "left": self["body"].pageUp,
                "right": self["body"].pageDown,
            },
            -1,
        )

    def _build_info_text(self):
        lines = [
            "Spritpreise-Checker",
            "",
            _("Data source") + ": Tankerkoenig API (https://creativecommons.tankerkoenig.de)",
            "Karten: OpenStreetMap (https://www.openstreetmap.org)",
            "Buy me a coffee: https://buymeacoffee.com/madoe21",
            "GitHub: https://github.com/madoe21/enigma2-spritpreise-checker",
            "",
            "Hinweis: Wenn die API keine Daten liefert, werden gespeicherte Daten genutzt.",
        ]
        return "\n".join(lines)

    def _load_qr_png(self):
        candidate_paths = [
            resolveFilename(SCOPE_PLUGINS, "Extensions/SpritpreiseChecker/res/qr_buymeacoffee.png"),
            os.path.join(os.path.dirname(__file__), "res", "qr_buymeacoffee.png"),
        ]
        for path in candidate_paths:
            if os.path.exists(path):
                try:
                    self["qr"].instance.setPixmapFromFile(path)
                    return
                except Exception:
                    pass
