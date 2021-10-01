import qbittorrentapi
import logging
import yaml
from pathlib import Path
from os import environ
import time

logging.basicConfig(level="INFO")

cfg = {}
config_file = Path("config.yml")
if config_file.is_file():
    with open("config.yml", "r") as yamlfile:
        yamlcfg = yaml.load(yamlfile, Loader=yaml.BaseLoader)
    cfg['host'] = yamlcfg['host']
    cfg['port'] = int(yamlcfg['port'])
    cfg['username'] = yamlcfg['username']
    cfg['password'] = yamlcfg['password']
    cfg['tracker_whitelist'] = yamlcfg['tracker_whitelist']
    cfg['testing_mode'] = yamlcfg['testing_mode']
    cfg['retry_seconds'] = int(yamlcfg['retry_seconds'])

if environ.get('QBITT_HOST') is not None:
    cfg['host'] = environ.get('QBITT_HOST')
if environ.get('QBITT_PORT') is not None:
    cfg['port'] = int(environ.get('QBITT_PORT'))
if environ.get('QBITT_USERNAME') is not None:
    cfg['username'] = environ.get('QBITT_USERNAME')
if environ.get('QBITT_PASSWORD') is not None:
    cfg['password'] = environ.get('QBITT_PASSWORD')
if environ.get('QBITT_TRACKER_WHITELIST') is not None:
    cfg['tracker_whitelist_csv'] = environ.get('QBITT_TRACKER_WHITELIST')
if environ.get('QBITT_TESTING_MODE') is not None:
    cfg['testing_mode'] = environ.get('QBITT_TESTING_MODE')
if environ.get('QBITT_RETRY_SECONDS') is not None:
    cfg['retry_seconds'] = int(environ.get('QBITT_RETRY_SECONDS'))

if 'tracker_whitelist_csv' in cfg:
    items = cfg['tracker_whitelist_csv'].split(',')
    cfg['tracker_whitelist'] = None
    cfg['tracker_whitelist'] = []
    for item in items:
        cfg['tracker_whitelist'].append(item)


qbitt_client = qbittorrentapi.Client(
    host=cfg['host'],
    port=cfg['port'],
    username=cfg['username'],
    password=cfg['password']
    )

relogin = False

while True:
    if relogin or not qbitt_client.is_logged_in:
        try:
            qbitt_client.auth_log_in()
            logging.info(f'qBittorrent: {qbitt_client.app.version}')
            logging.info(f'qBittorrent Web API: {qbitt_client.app.web_api_version}')
            relogin = False
        except Exception as e:
            if qbittorrentapi.LoginFailed: logging.error(e)
            time.sleep(cfg['retry_seconds'])
            pass
    
    if qbitt_client.is_logged_in:
        try:
            torrents = qbitt_client.torrents_info()
            for torrent in torrents:
                whitelisted = False
                for tracker_entry in torrent.trackers:
                    if any(wl_entry in tracker_entry['url'] for wl_entry in cfg['tracker_whitelist']):
                        whitelisted = True
                if torrent.state_enum.is_complete and not whitelisted:
                    if not torrent.state_enum.is_paused:
                        logging.info(f'Pausing {torrent.name}')
                        qbitt_client.torrents_pause(torrent_hashes=[torrent.info.hash])
                if not torrent.state_enum.is_complete:
                    logging.info(f'{torrent.name} is still downloading')
            time.sleep(cfg['retry_seconds'])
        except Exception as e:
            if qbittorrentapi.LoginFailed: logging.error(e)
            relogin = True
            pass
        
