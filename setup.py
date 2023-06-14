from importlib.metadata import entry_points
from setuptools import setup, find_packages

VERSION = '0.2.3'

with open('README.md', 'rt') as file:
    description = file.read()

setup(
    name='runit-server',
    version=VERSION,
    author='Amos Amissah',
    author_email='theonlyamos@gmail.com',
    description='Backend for python-runit',
    long_description=description,
    packages=find_packages(),
    include_package_data=True,
    install_requires=['requests','python-dotenv', 'python-runit', 
                      'odbms', 'flask','flask-jwt-extended', 
                      'flask-restful', 'waitress', 'passlib'],
    keywords='python3 runit server backend developer serverless architecture docker',
    project_urls={
        'Source': 'https://github.com/theonlyamos/runit-server/',
        'Tracker': 'https://github.com/theonlyamos/runit-server/issues',
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    entry_points={
        'console_scripts': [
            'runit-server=runit_server.cli:main',
        ],
    }
)
