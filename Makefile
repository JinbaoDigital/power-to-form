.PHONY: setup verify audit figures run demo archive-verify clean
setup:            ## install dependencies (--verify needs none of them)
	pip install -r requirements.txt
verify:           ## reconcile EVERY published number from the frozen artefacts (48 checks, no data)
	python reproduce.py --verify
audit:            ## the 34 pinned checks; 24 run here, 10 need the viewers/screenshots (VALIDATION.md)
	cd engine && python verify_cake_nr10.py
figures:          ## rebuild the two figures that need no licensed data (Fig. 1 and Fig. 5)
	cd engine && python figs_nr10_schematic.py f6 && python figs_nr10.py f3
run:              ## recompute the artefacts (needs the licensed caches; see README)
	python reproduce.py --run
demo:             ## run the engine end-to-end on a synthetic district (no licensed data)
	python reproduce.py --demo
archive-verify:   ## the previous generation: the five-district package, still runnable
	python archive_v5_5district/reproduce.py --verify
clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__ archive_v5_5district/data/synthetic/demo
