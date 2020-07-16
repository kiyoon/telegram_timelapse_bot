# https://stackoverflow.com/questions/3764291/checking-network-connection

import socket

def is_internet(host="8.8.8.8", port=53, timeout=2):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        print(ex)
        return False


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)


def time_fmt(num, suffix=''):
    for unit, value in zip(['seconds','mins','hours','days'], [60, 60, 24, 30]):
        if abs(num) < value:
            return "%2.1f %s%s" % (num, unit, suffix)
        num /= value
    return "%.1f %s%s" % (num, 'months', suffix)
