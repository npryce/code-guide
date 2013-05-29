#!/usr/bin/env python

from setuptools import setup
from setuptools.command.test import test as TestCommand
import sys
import os
import subprocess

def contents_of(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def version():
    git_cmd = ["git", "describe", "--always", "--tags", "--match", "*.*.*.*"]
    try:
        return str(subprocess.check_output(git_cmd), 'utf8').strip()
    except:
        return "snapshot"
    
class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_suite = True
        self.test_args = ["code_guide", '--duration=5']
        
    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(name='code-guide',
      version=version(),
      description='Turn example code into interactive HTML documentation',
      long_description=contents_of('README.md'),
      author='Nat Pryce',
      author_email='software@natpryce.com',
      url='http://natpryce.com',
      
      license="Apache 2.0. Bootstro is used under the MIT license.",
      
      classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License (GPL)',
        'License :: OSI Approved :: MIT',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Natural Language :: English',
        'Topic :: Software Development',
      ],
      
      provides=['code_guide'],
      packages=['code_guide'],
      scripts=['code-guide'],
      
      install_requires=["markdown==2.3.1", "pygments==1.6"],
      tests_require=['pytest==2.3.4', 'lxml'],

      cmdclass = {'test': PyTest}
)
