from dataclasses import dataclass, field
from typing import Sequence, Union

try:
    from .logger import Logger
    logger = Logger(__name__).get()
except ImportError:
    from logger import Logger
    logger = print


@dataclass
class ProxySettings():
    use_proxy_server: bool = False
    proxy_server_type: str = 'DefaultProxy'
    proxy_excluded_urls: Union[str, Sequence[str]] = field(default_factory=list)
    proxy_no_proxy_urls: Union[str, Sequence[str]] = field(default_factory=list)
    proxy_address: str = '192.168.178.1'
    proxy_port: int = 5423


def create_proxy_command_line_arguments(settings: ProxySettings,
                                        os_proxies: dict):
    """Returns the proxy arguments for the viewer.
    >>> t = create_proxy_command_line_arguments  # Do circumvent line length

    No matter what arguments are given, as long as use_proxy_server=False
    command line must always be --no-proxy-server with bypass localhost

    >>> t(ProxySettings(), None)
    ['--no-proxy-server', '--proxy-bypass-list', 'localhost']
    >>> t(ProxySettings(), {'http': 'proxy_address'})
    ['--no-proxy-server', '--proxy-bypass-list', 'localhost']

    If a proxy_server is used, and proxy_server_type is DefaultProxy, and
    there is a proxies list is given. The command line is --proxy-server
    and proxy address comes from the list, with https as preferred address
    >>> t(ProxySettings(use_proxy_server=True), {'http': 'http_proxy_address'})
    ['--proxy-server', 'http_proxy_address', '--proxy-bypass-list', 'localhost']

    >>> t(ProxySettings(use_proxy_server=True), {'https': 'https_proxy_address'})
    ['--proxy-server', 'https_proxy_address', '--proxy-bypass-list', 'localhost']

    >>> t(ProxySettings(use_proxy_server=True), {'http': 'http_proxy_address', 'https': 'https_proxy_address'})
    ['--proxy-server', 'https_proxy_address', '--proxy-bypass-list', 'localhost']

    >>> t(ProxySettings(use_proxy_server=True), {'ftp': 'ftp_proxy_address', 'http': 'http_proxy_address'})
    ['--proxy-server', 'http_proxy_address', '--proxy-bypass-list', 'localhost']

    If a proxy_server is used, and proxy_server_type is DefaultProxy, and
    there is no proxies list given, then there is a problem. Let CEF try to
    get the proxy server and command line is --proxy-auto-detect
    >>> t(ProxySettings(use_proxy_server=True), {})
    ['--proxy-auto-detect', '--proxy-bypass-list', 'localhost']

    If a proxy_server is used, and proxy_server_type is not DefaultProxy, proxy
    list is not taken into account, proxy_address and proxy_port is used.
    Command line is --proxy-server
    >>> t(ProxySettings(use_proxy_server=True, proxy_server_type='A'), {})
    ['--proxy-server', '192.168.178.1:5423', '--proxy-bypass-list', 'localhost']

    >>> t(ProxySettings(use_proxy_server=True, proxy_server_type='A', proxy_address='127.0.0.1'), {})
    ['--proxy-server', '127.0.0.1:5423', '--proxy-bypass-list', 'localhost']

    >>> t(ProxySettings(use_proxy_server=True, proxy_server_type='A', proxy_address='127.0.0.1', proxy_port=1234), {})
    ['--proxy-server', '127.0.0.1:1234', '--proxy-bypass-list', 'localhost']

    """
    cmd_line_args = []
    _settings = settings  # settings.getInstance().settings
#     import urllib.request
#     proxies = urllib.request.getproxies()
    proxies = os_proxies

    if not _settings.use_proxy_server:
        cmd_line_args.append("--no-proxy-server")
    else:
        proxy_server_type = _settings.proxy_server_type
        if proxy_server_type == "DefaultProxy" and not proxies:
            # Normally a list of proxies is given. However
            # on rare occasions urllib can not get the settings
            # List is only used for DefaultProxy, for other server types,
            # the proxy params are in the QGIS settings
            cmd_line_args.append("--proxy-auto-detect")
        else:
            proxy = _create_proxy_url(settings, proxies)
            if proxy is None or len(proxy) == 0:
                cmd_line_args.append("--proxy-auto-detect")
            else:
                cmd_line_args.append("--proxy-server")
                cmd_line_args.append(proxy)

    excluded_urls = _settings.proxy_excluded_urls
    no_proxy_urls = _settings.proxy_no_proxy_urls

    cmd_line_args.append("--proxy-bypass-list")
    bypassed_urls = "localhost"  # Always bypass localhost
    if excluded_urls or no_proxy_urls:
        proxy_bypassed = _create_proxy_bypass_list(excluded_urls,
                                                   no_proxy_urls)
        if proxy_bypassed:
            bypassed_urls += ";" + proxy_bypassed

    cmd_line_args.append(bypassed_urls)

    return cmd_line_args


def _create_proxy_url(settings: ProxySettings, proxies):
    proxy = ''
    if settings.proxy_server_type == "DefaultProxy":
        # chromium defaults to using windows proxy settings
        # but we need to at least bypass localhost
        # proxy = ";".join([p + "=" + proxies[p] for p in proxies])
        if "https" in proxies:
            proxy = proxies["https"]
        elif "http" in proxies:
            proxy = proxies["http"]
        elif list(proxies.values()):
            # Fallback, hope it is a valid proxy
            proxylist = list(proxies.values())
            if len(proxylist) > 0:
                proxy = list(proxies.values())[0]
            else:
                logger.error("No valid proxy found.")
        else:
            logger.error("No valid proxy found.")

        proxy = proxy.split(r"//")[-1]
    else:
        # FtpCachingProxy is probably better transformed to no proxy
        # (StreetSmart does not use FTP)
        # see https://doc.qt.io/qt-5/qnetworkproxy.html
        # proxy_type = {"HttpProxy": "http", "HttpCachingProxy": "http",
        #              "FtpCachingProxy": "http", "Socks5Proxy":
        #              "socks5"}

        # Http MUST NOT be added to the proxy url. If it is added, the viewer
        # will not show any images. The initialization of the api does succeed.
        proxy_type = {"Socks5Proxy": "socks5"}
        proxy_server_type = settings.proxy_server_type
        proxy_host = settings.proxy_address
        proxy_port = settings.proxy_port

        proxy_scheme = proxy_type.get(proxy_server_type, "")
        if proxy_scheme:
            proxy_scheme = "{}://".format(proxy_scheme)
        if proxy_port:
            proxy_port = ":{}".format(proxy_port)
        proxy = "{}{}{}".format(proxy_scheme, proxy_host, proxy_port)

    return proxy


# @log(print_args=True, print_return=True)
def _create_proxy_bypass_list(excluded: Union[str, Sequence[str]],
                              noproxy: Union[str, Sequence[str]]):
    if excluded is not None:
        if isinstance(excluded, str):
            first = excluded
        else:
            print(excluded)
            logger.info('Excluded')
            logger.info(type(excluded))
            logger.info(excluded)
            first = ";".join(excluded)
    else:
        first = None

    if noproxy is not None:
        if isinstance(noproxy, str):
            second = noproxy
        else:
            print(noproxy)
            logger.info('NoProxy')
            logger.info(noproxy)
            second = ";".join(noproxy)
    else:
        second = None

    if first and second:
        return first + ";" + second
    elif first:
        return first
    elif second:
        return second
    else:
        return None
