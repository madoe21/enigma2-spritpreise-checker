# Enigma2 SpritpreiseChecker Plugin

[![Built with aiflow](https://img.shields.io/badge/built%20with-aiflow-6b46c1)](https://github.com/cyber93de/aiflow)

Enigma2 plugin to display fuel prices using the Tankerkoenig API.

## Features

- Main screen with scrollable fuel-price table
- Main menu actions: close, refresh, sort by price, sort by distance, settings, info
- Settings for fuel type, ZIP code (PLZ), optional street + house number, radius and API key
- More precise distance when optional street and house number are set
- "Updated" timestamp in main screen
- Cache fallback if API returns no data (5-minute limit friendly)
- `make ipk` and `make install` with `opkg install --force-reinstall`
- Optional `.env` import into `/etc/enigma2/settings` during `make install`

## Translations

- German translations are maintained in `src/SpritpreiseChecker/locale/de/LC_MESSAGES/SpritpreiseChecker.po`
- During build, `make` compiles `.po` to `.mo` when `msgfmt` is available
- `_DE_FALLBACK` in code is kept as runtime fallback only

## Build

```sh
make ipk
```

Generated package name:

- `enigma2-plugin-extensions-spritpreise-checker_1.0.0_all.ipk`

## Install on box

1. Copy `.env.example` to `.env`
2. Fill at least `BOX_HOST`, `BOX_USER`, `BOX_PORT`
3. Optional: set `PLZ`, `STREET`, `HOUSE_NUMBER`, `RADIUS`, `FUEL_TYPE` to preload plugin settings
4. API key remains `TANKERKOENIG_API_KEY`

```sh
make install
```

## .env example

```env
BOX_HOST=192.168.1.4
BOX_USER=root
BOX_PORT=22

TANKERKOENIG_API_KEY=your_key
PLZ=10115
STREET=Geranienstr.
HOUSE_NUMBER=31
RADIUS=5
FUEL_TYPE=diesel
```

## Fuel type options

Valid values for `FUEL_TYPE`:

- `diesel`
- `e5`
- `e10`

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Found a bug or have a suggestion for improvement? Please create an issue or pull request.

I appreciate everyone who supports me and the project! For any requests and suggestions, feel free to provide feedback.

<p>
  <a href="https://www.buymeacoffee.com/madoe21">
    <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" height="50" alt="Buy Me a Coffee">
  </a>

  <a href="https://ko-fi.com/madoe21">
    <img src="https://storage.ko-fi.com/cdn/kofi3.png?v=3" height="50" alt="Ko-fi">
  </a>

  <a href="https://paypal.me/MartinD809">
    <img src="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_111x69.jpg" height="50" alt="PayPal">
  </a>
</p>

---

## Built with aiflow

This project was built with support from **[aiflow](https://cyber93de.github.io/aiflow/)** — *built with aiflow*.
