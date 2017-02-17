from setuptools import setup

setup(name='revex',
      version='0.0.0',
      description='Reversable regular expressions',
      url='http://github.com/lucaswiman/revex',
      author='Lucas Wiman   ',
      author_email='lucas.wiman@gmail.com',
      license='Apache 2.0',
      packages=['revex'],
      install_requires=['parsimonious', 'networkx', 'six'],
      long_description='foo',
      zip_safe=False)
