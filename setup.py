from distutils.core import setup

from setuptools import find_packages

import ibeam

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    parsed_requirements = f.read().splitlines()

pakages_found = find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests", "examples", "docs", "out", "dist"])

print(f'Found packages: {pakages_found}')

setup(
    name='ibeam',
    packages=pakages_found,
    version=ibeam.__version__,
    license='Apache-2.0',
    description='IBeam is an authentication and maintenance tool used for the Interactive Brokers Client Portal Web API Gateway.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Voy Zan',
    author_email='voy1982@yahoo.co.uk',
    url='https://github.com/Voyz/ibeam',
    keywords=['interactive brokers', 'algo trading',
              'algorithmic trading', 'data flow', 'quant', 'trading'],
    install_requires=parsed_requirements,
    classifiers=[
        'Development Status :: 4 - Beta',
        # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3.7',
    ],
)
