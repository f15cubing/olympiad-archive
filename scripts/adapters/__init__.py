"""Dataset adapters: map public datasets -> canonical import YAML.

Each adapter (see base.Adapter) turns a source dataset into the same canonical
per-competition-year YAML that scripts/import_problems.py consumes. Output is validated
against the importer's schema and KaTeX-checked, so an adapter can never emit something
the importer would reject.

LICENSING: verify each source's license before importing its content. Problem statements
are generally reproducible published facts, but always record a source_url, and do not
copy third-party solutions.
"""
