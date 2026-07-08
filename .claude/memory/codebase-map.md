# Codebase map (onboarding 2026-07-08)

**enigma2-spritpreise-checker** — Enigma2 (OpenATV 7.6) plugin: German fuel
prices (Tankerkönig API) for nearby stations on the TV. Python. ~1500 LOC.

## Layout
- `src/SpritpreiseChecker/plugin.py` (~257 LOC) — entry.
- `src/SpritpreiseChecker/api.py` (~127) — Tankerkönig REST client. **Data
  layer** (needs an API key — via config, keep out of source).
- `src/SpritpreiseChecker/screens.py` (~962) — enigma2 GUI (station list,
  config).
- `res/`, `control/`, `build/` (gitignored ipk).

## Conventions
- Enigma2 Py3; timeouts on all API calls (main reactor thread).
- Tankerkönig API key is user config — never hard-code.

## Kodi portability: **monolithic (data layer already separate)**
3 files import enigma2 (screens/plugin). `api.py` is a clean REST client. Port
= move `api.py` to `core/` (verify enigma2-free, take the API key + location as
params/config-adapter), add `platform/kodi/`. Target shape:
lotto/stocks/weather.
