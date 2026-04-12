# -*- coding: utf-8 -*-
from __future__ import absolute_import

import gettext

from Components.Language import language
from Tools.Directories import SCOPE_PLUGINS, resolveFilename

PLUGIN_DOMAIN = "SpritpreiseChecker"
PLUGIN_PATH = "Extensions/SpritpreiseChecker/locale"

_DE_FALLBACK = {
    "SpritpreiseChecker": "SpritpreiseChecker",
    "Spritpreise-Checker": "Spritpreise-Checker",
    "Fuel prices": "Spritpreise",
    "Price": "Preis",
    "Sort by": "Sortierung",
    "Price / liter": "Preis / Liter",
    "Distance": "Entfernung",
    "Sort by price per liter (ascending)": "Nach Preis/Liter aufsteigend",
    "Sort by distance (ascending)": "Nach Entfernung aufsteigend",
    "Price per liter (ascending)": "Preis/Liter (aufsteigend)",
    "Distance (ascending)": "Entfernung (aufsteigend)",
    "Settings": "Einstellungen",
    "Refresh": "Aktualisieren",
    "Information": "Information",
    "Close": "Schließen",
    "Save": "Speichern",
    "Cancel": "Abbrechen",
    "Station": "Tankstelle",
    "Distance": "Entfernung",
    "Updated": "Stand",
    "No entries available": "Keine Einträge verfügbar",
    "Fuel type": "Spritart",
    "ZIP code": "PLZ",
    "Street": "Straße",
    "House number": "Hausnummer",
    "Radius (km)": "Umkreis (km)",
    "Map zoom": "Karten-Zoom",
    "Sort": "Sortierung",
    "Station map": "Tankstellenkarte",
    "Loading map tiles...": "Kartenkacheln werden geladen...",
    "OK/Exit closes this map": "OK/Exit schließt diese Karte",
    "Map could not be loaded": "Karte konnte nicht geladen werden",
    "No coordinates available for this station": "Keine Koordinaten für diese Tankstelle verfügbar",
    "Select the fuel type to display in the list": "Wählen Sie die Spritart für die Liste",
    "Enter your 5-digit ZIP code": "Geben Sie hier Ihre 5-stellige PLZ ein",
    "Optional: street for more precise distance": "Optional: Straße für genauere Entfernung",
    "Optional: house number for more precise distance": "Optional: Hausnummer für genauere Entfernung",
    "Enter search radius in km (1-25)": "Geben Sie den Suchradius in km ein (1-25)",
    "Set map zoom level (12-19), higher means closer": "Setzen Sie den Karten-Zoom (12-19), höher ist näher",
    "Enter your Tankerkoenig API key here": "Tragen Sie hier Ihren Tankerkoenig API Key ein",
    "API key": "API Key",
    "Settings saved": "Einstellungen gespeichert",
    "Please fill all settings": "Bitte alle Einstellungen ausfüllen",
    "Using cached data": "Nutze zwischengespeicherte Daten",
    "Data source": "Datenquelle",
    "Back": "Zurück",
    "Main menu": "Hauptmenü",
}


def localeInit():
    gettext.bindtextdomain(PLUGIN_DOMAIN, resolveFilename(SCOPE_PLUGINS, PLUGIN_PATH))
    try:
        gettext.bind_textdomain_codeset(PLUGIN_DOMAIN, "UTF-8")
    except Exception:
        pass


def _(txt):
    translated = gettext.dgettext(PLUGIN_DOMAIN, txt)
    if translated != txt:
        return translated

    try:
        lang = language.getLanguage()[:2]
    except Exception:
        lang = "en"

    if lang == "de":
        return _DE_FALLBACK.get(txt, txt)
    return txt


localeInit()
try:
    language.addCallback(localeInit)
except Exception:
    pass
