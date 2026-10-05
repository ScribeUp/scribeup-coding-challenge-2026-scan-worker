PYTHON ?= python
FAKES_PORT ?= 8899
PARTNERS_URL ?= http://127.0.0.1:$(FAKES_PORT)
export PARTNERS_URL

.PHONY: setup reset scan-all worker test fakes stop-fakes

setup:
	$(PYTHON) -m pip install -r requirements.txt
	$(MAKE) fakes
	$(PYTHON) manage.py migrate
	$(PYTHON) manage.py seed

reset: fakes
	$(PYTHON) manage.py reset_db

scan-all: fakes
	$(PYTHON) manage.py scan_all

worker: fakes
	$(PYTHON) manage.py run_worker

test:
	$(PYTHON) manage.py test scans

# The fake bank and enrichment vendor, running in the background.
fakes:
	@if curl -sf $(PARTNERS_URL)/healthz > /dev/null 2>&1; then \
		echo "Fake partners running at $(PARTNERS_URL)"; \
	else \
		FAKES_PORT=$(FAKES_PORT) nohup bin/fakes > logs/fakes.log 2>&1 & echo $$! > logs/fakes.pid; \
		for i in 1 2 3 4 5 6 7 8 9 10; do curl -sf $(PARTNERS_URL)/healthz > /dev/null 2>&1 && break; sleep 0.3; done; \
		curl -sf $(PARTNERS_URL)/healthz > /dev/null 2>&1 || { echo "Fake partners didn't start, see logs/fakes.log"; exit 1; }; \
		echo "Started fake partners at $(PARTNERS_URL) (logs/fakes.log; stop with make stop-fakes)"; \
	fi

stop-fakes:
	@if [ -f logs/fakes.pid ]; then kill $$(cat logs/fakes.pid) 2>/dev/null; rm -f logs/fakes.pid; echo "Stopped fake partners"; \
	else echo "No fake partners started by make"; fi
