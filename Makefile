.PHONY: run
run: locales
	python3 runner.py

.PHONY: locales
locales:
	echo "Generating locales"
	python3 -m langpy compile
	echo "Finished generating locales"