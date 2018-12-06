#!/bin/python3

import sys
import time
import json
import socket
import logging
import yaml
import requests
from sending_queue import SendingQueue
from client_watcher import ClientWatcher
from file_renderer import FileRenderer
import client_db

DEFAULT_CONFIG_PATH = 'etc/default_config.yaml'
DIVIDER = '--------------------------------------'

logger = logging.getLogger(__name__)
fh = logging.FileHandler('client/.data/client.log')
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)

class ClientManager():
    ''' Class to manager client process '''

    def __init__(self, config_path):
        ''' Create ClientManager object '''
        # Handle config
        if not config_path:
            config_path = DEFAULT_CONFIG_PATH
        logger.info("%s\nLoading configuration: %s", DIVIDER, config_path)
        dir_map = {}
        with open(config_path, 'r') as config_file:
            config = yaml.load(config_file)
            self.server_url = config['client']['server_http_url']
            server_address = config['client']['server_socket_address']
            self.num_send_threads_per_file = config['client']['num_send_threads_per_file']
            # Store each directory to watch
            for dir_obj in config['client']['directories']:
                dir_map[dir_obj['full_path']] = {'interval': int(dir_obj['watch_interval']),
                                                 'counter': int(dir_obj['watch_interval'])}
            logger.debug("\tServer URL:  %s", self.server_url)
            logger.debug("\tServer Address:  %s", server_address)
            logger.debug("\tSend Threads Per File: %d", self.num_send_threads_per_file)
            logger.debug("\tDirectories:\n%s", str(dir_map))
            logger.debug("End configuration\n%s", DIVIDER)
            self.sendingQueue = SendingQueue(server_address)
        # Setup DB
        client_db.start()
        self.watcher = ClientWatcher(dir_map)
        self.file_renderer = FileRenderer()

    def register(self):
        ''' Register client with server '''
        endpoint = "{}/register?hostname={}".format(self.server_url, socket.gethostname())
        # Send request
        response = requests.get(endpoint)
        if response.status_code == 200:
            logger.info("Registered with server!")
            data = response.json()
            logger.info(str(data))
            self.file_renderer.segment_size = data['segment_size']
        else:
            logger.info("Failed to Register with server!")
            logger.info(str(response.text))


    def render_file(self, file_obj):
        ''' Decompose file and determine which segments to send.
            Add resulting segments to the sending queue
        '''
        # Get SHAS from server for file
        server_segments = []
        endpoint = '{}/segments?hostname={}&filename={}'.format(
              self.server_url, socket.gethostname(), file_obj['filename'])
        try:
            resp = requests.get(endpoint)
        except Exception as seg_error:
            logger.error("Failed to get segments from server. Error: %s", str(seg_error))
            return None
        # Evaluate return code
        if resp.status_code == 300:
            logger.debug("File does not exist on server")
            server_segments = []
        elif resp.status_code != 200:
            logger.error("Bad return code getting segments from server. Response: %s", resp.text)
            return None
        else:
            server_segments = resp.json()['segments']

        # Get break up file in segements, compare against server
        return self.file_renderer.process_file(file_obj, server_segments)

    def check_fs(self):
        ''' Check file system '''
        return self.watcher.check_fs()

    def init_send(self, file_obj):
        ''' Communicate with Server to determine if we can send.
            If not, wait. If so, store the ports returned, and
            send back the number of files we're sending.
            Start sending queue send thread
        '''
        segments_to_send = self.render_file(file_obj)
        if not segments_to_send:
            logger.debug("No segments to send for (%s), server is up to date", file_obj['filename'])
            return True

        # Check with server - start send by providing file info, get ports
        num_segments = len(segments_to_send)
        segment_size = sys.getsizeof(json.dumps(segments_to_send[0]).encode('utf-8'))
        port_list = None
        req_data = {'seg_size': segment_size, 'num_seg': num_segments,
                    'hostname': socket.gethostname(), 'filename': file_obj['filename']}
        endpoint = "{}/initSend".format(self.server_url)
        # Send request
        timeout = 180 # 3 minutes
        while timeout > 0:
            response = requests.post(endpoint, data=req_data)
            if response.status_code == 200:
                logger.info("Initiated sending of file (%s) server!", file_obj['filename'])
                data = response.json()
                logger.info(str(data))
                port_list = data['ports']
                break
            elif response.status_code == 503:
                logger.info("Server refused to recieve file (%s). Waiting...", file_obj['filename'])
                logger.info(str(response.text))
                time.sleep(5)
                timeout -= 5
            else:
                logger.info("Failed to send file (%s) to server!", file_obj['filename'])
                logger.info(str(response.text))
                return False


        # This is a non-blocking call
        # Connect to server, then start thread to send each segment
        self.sendingQueue.start_sending(file_obj['filename'], port_list, segments_to_send,
                                        self.num_send_threads_per_file)
        return True

    def complete_sending(self):
        ''' Close all connections and terminiate sending threads
            once all segments have been sent
        '''
        self.sendingQueue.complete_sending()

    def sleep(self):
        ''' Client Watcher manages directories, sleep until next one
            needs to be checked.
        '''
        self.watcher.sleep()
