from setuptools import setup, find_packages

import yatat

with open('README.md', 'r', encoding='utf-8') as README:
    long_description = README.read()

setup(
    name='Yatat',
    description='Yet another twitter archive tool',
    long_description=long_description,
    version=yatat.__version__,
    author='Sascha Schlindwein',
    author_email='yatat-dev@schlind.org',
    url='https://github.com/schlind/Yatat',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'License :: Public Domain',
        'Topic :: Artistic Software',
        'Topic :: Internet',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Unix',
    ],
    zip_safe=True,
    keywords='twitter archive browser tweet keep delete',
    py_modules=['yatat', 'yatat_test'],
    python_requires='>=3.7, <4',
    install_requires=['karlsruher>=2.0b16'],
    entry_points={
        'console_scripts': ['yatat=yatat:main']
    },
    project_urls={
        'Source': 'https://github.com/schlind/Yatat',
    },
)
