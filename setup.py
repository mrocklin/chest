#!/usr/bin/env python

from os.path import exists
from setuptools import setup
import chest

setup(name='chest',
      version=chest.__version__,
      description='Simple on-disk dictionary',
      url='http://github.com/mrocklin/chest/',
      author='https://raw.github.com/mrocklin/chest/master/AUTHORS.md',
      maintainer='Matthew Rocklin',
      maintainer_email='mrocklin@gmail.com',
      license='BSD',
      keywords='dictionary out-of-core',
      install_requires=list(open('requirements.txt').read().strip()
                            .split('\n')),
      packages=['chest'],
      long_description=(open('README.rst').read() if exists('README.rst')
                        else ''),
      zip_safe=False)
