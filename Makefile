.PHONY: setup verify run demo figures notebook clean
setup:            ## install dependencies
	pip install -r requirements.txt
demo:             ## run the engine end-to-end on synthetic data (no licensed data)
	python reproduce.py --demo
verify:           ## print headline numbers from results/
	python reproduce.py --verify
run:              ## recompute from the shipped caches + redraw figures (after editing operators)
	python reproduce.py --run
figures:          ## regenerate data figures from results/ (fig3 needs licensed caches)
	python figures/build_figures.py all
notebook:         ## launch the pipeline walkthrough notebook
	jupyter lab notebooks/pipeline_walkthrough.ipynb
clean:
	rm -rf data/synthetic/demo __pycache__ */__pycache__
