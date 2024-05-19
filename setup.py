from setuptools import find_packages, setup

setup(
    name='sdkdemo',
    packages=find_packages(),
    version='0.1.0',
    description='Admyre Influencer Marketing SDK',
    author='Rishabh Saraswat',
    install_requires=[
        'pymongo',  # Assuming you're using pymongo
        'hikerapi',  # Placeholder for your custom dependency or any other required package
        'aiohttp'  # If you're making async HTTP requests, you'll need an async HTTP client like aiohttp
    ],
)
