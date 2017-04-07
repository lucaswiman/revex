from setuptools import setup
import sys

install_requires = ['parsimonious', 'networkx', 'six', 'numpy']
if sys.version < (3, 5):
    install_requires.append('typing')

setup(name='revex',
      version='0.0.0',
      description='Reversable regular expressions',
      url='http://github.com/lucaswiman/revex',
      author='Lucas Wiman   ',
      author_email='lucas.wiman@gmail.com',
      license='Apache 2.0',
      packages=['revex'],
      install_requires=install_requires,
      long_description='foo',
      zip_safe=False)
