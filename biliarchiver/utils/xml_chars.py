from typing import Union

_xml_ILLEGAL_CHARS = []
_xml_ILLEGAL_CHARS.extend([bytes([i]).decode('ascii') for i in range(int('01', 16), int('08', 16)+1)])
_xml_ILLEGAL_CHARS.extend([bytes([i]).decode('ascii') for i in range(int('0b', 16), int('0c', 16)+1)])
_xml_ILLEGAL_CHARS.extend([bytes([i]).decode('ascii') for i in range(int('0e', 16), int('1f', 16)+1)])
_xml_ILLEGAL_CHARS.extend(['\x7f'])
# NOTE: The following are non-ASCII characters, which will not appear in string obj in Python.
# range(int('80', 16), int('84', 16)+1)])
# range(int('86', 16), int('9f', 16)+1)])
XML_ILLEGAL_CHARS = _xml_ILLEGAL_CHARS


def _legalize_str(s: str, print_info: bool=False):
    for c in XML_ILLEGAL_CHARS:
        hash_before = hash(s)
        s = s.replace(c, '')
        if print_info and hash(s) != hash_before:
            print(f"Removed XML illegal char \\x{ord(c):02x}")
    return s

def _legalize_list(l: list):
    for i, v in enumerate(l):
        if isinstance(v, str):
            l[i] = _legalize_str(v)
        elif isinstance(v, dict):
            l[i] = _legalize_dict(v)
        elif isinstance(v, list):
            l[i] = _legalize_list(v)
        else:
            pass
    return l

def _legalize_dict(d: dict):
    for k, v in d.items():
        if isinstance(v, str):
            d[k] = _legalize_str(v)
        elif isinstance(v, list):
            d[k] = _legalize_list(v)
        elif isinstance(v, dict):
            d[k] = _legalize_dict(v)
        else:
            pass
    return d

def xml_chars_legalize(obj: Union[dict, str, list]) -> Union[dict, str, list]:
    """ Remove XML illegal characters from a dict, list or str. """
    if isinstance(obj, str):
        return _legalize_str(obj)
    elif isinstance(obj, dict):
        return _legalize_dict(obj)
    elif isinstance(obj, list):
        return _legalize_list(obj)
    else:
        raise TypeError(f"Unexpected type: {type(obj)}")

def _test_xml_chars_legalize():
    _str = '\x0bA\x0cB\vC'
    _str_after = 'ABC'
    assert _legalize_str(_str) == _str_after
    _list = ['\x0bA', '\x0cB', 'C\v']
    _list_after = ['A', 'B', 'C']
    assert _legalize_list(_list) == _list_after
    _dict = {'A': '\x0bA', 'B': '\x0cB', 'C': 'C\v', 'list': _list}
    _dict_after = {'A': 'A', 'B': 'B', 'C': 'C', 'list': _list_after}
    assert _legalize_dict(_dict) == _dict_after
    _dict_in_list_in_dict_in_dict = {"dict": [{'A': '\x0bA', 'B': '\x0cB', 'C': 'C\v', 'list': _list, 'dict': _dict}]}
    _dict_balabala_after = {'dict': [{'A': 'A', 'B': 'B', 'C': 'C', 'list': _list_after, 'dict': _dict_after}]}
    assert _legalize_dict(_dict_in_list_in_dict_in_dict) == _dict_balabala_after

if __name__ == '__main__':
    # TODO: use pytest
    _test_xml_chars_legalize()