ifneq (,$(wildcard .env))
include .env
endif

PLUGIN_NAME = SpritpreiseChecker
PACKAGE_NAME = enigma2-plugin-extensions-spritpreise-checker
VERSION := $(shell cat VERSION 2>/dev/null | tr -d '[:space:]')

BUILD_DIR = build
IPK_WORK_DIR = $(BUILD_DIR)/ipk
DATA_STAGING = $(IPK_WORK_DIR)/data
CONTROL_STAGING = $(IPK_WORK_DIR)/control

PLUGIN_PATH = usr/lib/enigma2/python/Plugins/Extensions/$(PLUGIN_NAME)
OUTPUT_IPK = $(BUILD_DIR)/$(PACKAGE_NAME)_$(VERSION)_all.ipk

DOS2UNIX_BIN := $(shell command -v dos2unix 2>/dev/null)
MSGFMT_BIN := $(shell command -v msgfmt 2>/dev/null)

BOX_HOST ?=
BOX_USER ?=
BOX_PORT ?=22

ENV_API_KEY = $(strip $(TANKERKOENIG_API_KEY))
ENV_PLZ = $(strip $(PLZ))
ENV_STREET = $(strip $(STREET))
ENV_HOUSE_NUMBER = $(strip $(HOUSE_NUMBER))
ENV_RADIUS = $(strip $(RADIUS))
ENV_FUEL_TYPE = $(strip $(FUEL_TYPE))

.PHONY: all build clean normalize compile-locales prepare ipk install copy-settings check-settings print-env apply restart deploy

all: ipk

clean:
	rm -rf $(BUILD_DIR)

normalize:
ifneq ($(DOS2UNIX_BIN),)
	find src control -type f -exec dos2unix {} \;
endif

compile-locales:
ifneq ($(MSGFMT_BIN),)
	@for lang in de en it es; do \
		po=src/$(PLUGIN_NAME)/locale/$$lang/LC_MESSAGES/$(PLUGIN_NAME).po; \
		mo=src/$(PLUGIN_NAME)/locale/$$lang/LC_MESSAGES/$(PLUGIN_NAME).mo; \
		if [ -f "$$po" ]; then \
			$(MSGFMT_BIN) -o "$$mo" "$$po"; \
		fi; \
	done
else
	@echo "msgfmt not found - skipping locale compilation"
endif

prepare: normalize compile-locales
	mkdir -p $(DATA_STAGING)/$(PLUGIN_PATH)
	mkdir -p $(CONTROL_STAGING)
	cp -r src/$(PLUGIN_NAME)/* $(DATA_STAGING)/$(PLUGIN_PATH)/
	cp control/control $(CONTROL_STAGING)/
	sed -i 's/^Version:.*/Version: $(VERSION)/' $(CONTROL_STAGING)/control
	cp control/postinst $(CONTROL_STAGING)/
	cp control/prerm $(CONTROL_STAGING)/
	chmod 755 $(CONTROL_STAGING)/postinst $(CONTROL_STAGING)/prerm

ipk: clean prepare
	cd $(IPK_WORK_DIR) && \
	tar -czf data.tar.gz -C data . && \
	tar -czf control.tar.gz -C control . && \
	echo "2.0" > debian-binary && \
	ar r $(PACKAGE_NAME)_$(VERSION)_all.ipk debian-binary control.tar.gz data.tar.gz
	mv $(IPK_WORK_DIR)/$(PACKAGE_NAME)_$(VERSION)_all.ipk $(OUTPUT_IPK)

install: ipk
	@test -n "$(BOX_HOST)" && test -n "$(BOX_PORT)" && test -n "$(BOX_USER)"
	scp -P $(BOX_PORT) $(OUTPUT_IPK) $(BOX_USER)@$(BOX_HOST):/tmp/
	ssh -p $(BOX_PORT) $(BOX_USER)@$(BOX_HOST) "opkg install --force-reinstall /tmp/$(PACKAGE_NAME)_$(VERSION)_all.ipk"

copy-settings:
	@test -n "$(BOX_HOST)" && test -n "$(BOX_PORT)" && test -n "$(BOX_USER)"
	@if [ -n "$(ENV_API_KEY)$(ENV_PLZ)$(ENV_STREET)$(ENV_HOUSE_NUMBER)$(ENV_RADIUS)$(ENV_FUEL_TYPE)" ]; then \
		ssh -p $(BOX_PORT) $(BOX_USER)@$(BOX_HOST) "set -e; \
		SETTINGS=/etc/enigma2/settings; TMP=/tmp/spritpreisechecker_settings.tmp; \
		touch \$$SETTINGS; \
		grep -v '^config.plugins.spritpreisechecker\\.' \$$SETTINGS > \$$TMP || true; \
		if [ -n '$(ENV_API_KEY)' ]; then echo 'config.plugins.spritpreisechecker.api_key=$(ENV_API_KEY)' >> \$$TMP; fi; \
		if echo '$(ENV_PLZ)' | grep -Eq '^[0-9]{5}$$'; then echo 'config.plugins.spritpreisechecker.plz=$(ENV_PLZ)' >> \$$TMP; fi; \
		if [ -n '$(ENV_STREET)' ]; then echo 'config.plugins.spritpreisechecker.street=$(ENV_STREET)' >> \$$TMP; fi; \
		if [ -n '$(ENV_HOUSE_NUMBER)' ]; then echo 'config.plugins.spritpreisechecker.house_number=$(ENV_HOUSE_NUMBER)' >> \$$TMP; fi; \
		if echo '$(ENV_RADIUS)' | grep -Eq '^[0-9]+$$'; then echo 'config.plugins.spritpreisechecker.radius=$(ENV_RADIUS)' >> \$$TMP; fi; \
		FUEL_TYPE=\$$(echo '$(ENV_FUEL_TYPE)' | tr '[:upper:]' '[:lower:]'); \
		if echo \$$FUEL_TYPE | grep -Eq '^(diesel|e5|e10)$$'; then echo config.plugins.spritpreisechecker.fuel_type=\$$FUEL_TYPE >> \$$TMP; fi; \
		cp \$$TMP \$$SETTINGS; rm -f \$$TMP; sync"; \
		echo "Applied .env plugin values to /etc/enigma2/settings"; \
	else \
		echo "No API/PLZ/STREET/HOUSE_NUMBER/RADIUS/FUEL_TYPE values in .env to apply"; \
	fi

print-env:
	@echo "BOX_HOST=$(BOX_HOST)"
	@echo "BOX_USER=$(BOX_USER)"
	@echo "BOX_PORT=$(BOX_PORT)"
	@echo "TANKERKOENIG_API_KEY length=$$(printf '%s' "$(ENV_API_KEY)" | wc -c)"
	@echo "PLZ=$(ENV_PLZ)"
	@echo "STREET=$(ENV_STREET)"
	@echo "HOUSE_NUMBER=$(ENV_HOUSE_NUMBER)"
	@echo "RADIUS=$(ENV_RADIUS)"
	@echo "FUEL_TYPE=$(ENV_FUEL_TYPE)"

check-settings:
	@test -n "$(BOX_HOST)" && test -n "$(BOX_PORT)" && test -n "$(BOX_USER)"
	@ssh -p $(BOX_PORT) $(BOX_USER)@$(BOX_HOST) "echo '--- /etc/enigma2/settings (spritpreisechecker) ---'; grep '^config.plugins.spritpreisechecker\\.' /etc/enigma2/settings || echo '(no entries)'"

build: ipk

deploy: install copy-settings apply

apply:
	@test -n "$(BOX_HOST)" && test -n "$(BOX_PORT)" && test -n "$(BOX_USER)"
	ssh -p $(BOX_PORT) $(BOX_USER)@$(BOX_HOST) \
	    "init 4 >/dev/null 2>&1 || killall -9 enigma2 >/dev/null 2>&1 || true; sleep 2; init 3 >/dev/null 2>&1 || true"

restart: apply
