from setuptools import setup, find_packages

f = open('README.md', mode='r', encoding='utf-8')
long_description = f.read()
f.close()

setup(
    name='logger_pro',
    version='2.0.1',
    packages=find_packages(),
    url='https://github.com/zedzhen/logger_pro',
    license='MIT License',
    license_files='LICENSE',
    author='Ярыкин Евгений',
    author_email='',
    description='Логирование работы программы',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=[
        'dill>=0.3.4',
    ],
    python_requires='>=3.8',
)
