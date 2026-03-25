"""Sphinx configuration for revex documentation."""
import os
import sys

sys.path.insert(0, os.path.abspath('..'))

project = 'revex'
copyright = '2024, Lucas Wiman'
author = 'Lucas Wiman'
release = '0.1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.graphviz',
    'sphinx_autodoc_typehints',
]

templates_path = ['_templates']
exclude_patterns = ['_build']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

autodoc_member_order = 'bysource'
graphviz_output_format = 'svg'
