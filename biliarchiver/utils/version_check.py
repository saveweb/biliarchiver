import requests

from biliarchiver.exception import VersionOutdatedError

def get_latest_version(pypi_project: str):
    '''Returns the latest version of pypi_project.'''
    project_url_pypi = f'https://pypi.org/pypi/{pypi_project}/json'
    
    try:
        response = requests.get(project_url_pypi, timeout=5, headers={'Accept': 'application/json', 'Accept-Encoding': 'gzip'})
    except requests.exceptions.Timeout or requests.exceptions.ConnectionError:
        print(f'Warning: Could not get latest version of {pypi_project} from pypi.org. (Timeout)')
        return None
    if response.status_code == 200:
        data = response.json()
        latest_version: str = data['info']['version']
        return latest_version
    else:
        print(f'Warning: Could not get latest version of {pypi_project}. HTTP status_code: {response.status_code}')
        return None

def check_outdated_version(pypi_project: str, self_version: str, raise_error: bool = True):
    latest_version = get_latest_version(pypi_project)
    if latest_version is None:
        return
    elif latest_version != self_version:
        print('=' * 47)
        print(f'Warning: You are using an outdated version of {pypi_project} ({self_version}).')
        print(f'         The latest version is {latest_version}.')
        print(f'         You can update {pypi_project} with "pip3 install --upgrade {pypi_project}".')
        print('=' * 47, end='\n\n')
        if raise_error:
            raise VersionOutdatedError(version=self_version)
    else: # latest_version == self_version
        print(f'You are using the latest version of {pypi_project}.')
