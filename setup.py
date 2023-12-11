from importlib.metadata import entry_points
from setuptools import setup, find_packages

VERSION = "0.3.1"

with open('README.md', 'rt') as file:
    description = file.read()

setup(
    name='runit-server',
    version=VERSION,
    author='Amos Amissah',
    author_email='theonlyamos@gmail.com',
    description='Backend for python-runit',
    long_description=description,
    long_description_content_type = "text/markdown",
    packages=find_packages(),
    include_package_data=True,
    install_requires=['requests','python-dotenv', 'python-runit', 
                      'odbms', 'fastapi', 'python-multipart',
                      'python-jose[cryptography]', 'passlib', 'docker',
                      'aiofiles', 'pydantic', 'pydantic[email]',
                      'jinja2', 'PyGithub', 'itsdangerous'],
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
        'Programming Language :: Python :: 3.12',
    ],
    entry_points={
        'console_scripts': [
            'runit-server=runit_server.cli:main',
        ],
    }
)
