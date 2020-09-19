#!/usr/bin/env bash

# Convert svg files in the current directory to png images of the same size.

max_float() {
	python -c 'import sys; print(max(float(x) for x in sys.stdin.readlines()))'
}

>&2 echo -n 'Finding maximum width'
width="$(for file in *.svg; do
	inkscape -W "${file}"
	>&2 echo -n '.'
done | max_float)"
>&2 echo -e "\nWidth: ${width}"

>&2 echo -n 'Finding maximum height'
height="$(for file in *.svg; do
	inkscape -H "${file}"
	>&2 echo -n '.'
done | max_float)"
>&2 echo -e "\nHeight: ${height}"

for file in *.svg; do
	inkscape "--export-area=0:0:${width}:${height}" \
		--export-background="#ffffff" \
		--export-filename="$(sed 's/\.svg$/.png/' <<< "${file}")" \
		"${file}"
done
