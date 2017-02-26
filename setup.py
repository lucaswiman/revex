import os, sys
from setuptools import setup
import sys


with open(os.path.join(os.path.dirname(__file__), 'README.rst'), 'r') as f:
      long_description = f.read()

install_requires = ['parsimonious', 'networkx', 'six']
if sys.version_info < (3, 5):
    install_requires.append('typing')


setup(
    name='revex',
    version='0.0.1',
    description='Reversable regular expressions',
    url='http://github.com/lucaswiman/revex',
    author='Lucas Wiman   ',
    author_email='lucas.wiman@gmail.com',
    license='Apache 2.0',
    packages=['revex'],
    install_requires=install_requires,
    long_description='foo',
    zip_safe=True,
    classifiers=[
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: Apache Software License',
        'Development Status :: 3 - Alpha',
    ],
)
