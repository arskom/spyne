
all: pres.pdf

pres.pdf: pres.tex get_utc_time.pdf
	pdflatex pres.tex
	pdflatex pres.tex
	pdflatex pres.tex

get_utc_time.pdf: get_utc_time.svg
	inkscape --file=get_utc_time.svg --export-pdf get_utc_time.pdf
