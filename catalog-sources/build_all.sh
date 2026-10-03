#!/bin/sh
set -e
python3 migrate.py && python3 build_i18n.py && python3 tools/validate.py catalog
for l in en fr; do python3 tools/make_doc.py catalog $l catalog/catalog.$l.md; python3 tools/merge.py catalog $l catalog/catalog.$l.json; done
