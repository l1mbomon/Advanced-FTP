#!/bin/python3

import sys
import json
import time
import socket
import logging
from threading import Lock

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
fh = logging.FileHandler('client/.data/client.log')
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)

class ClientSocket():
    ''' Class to store ClientSocket object.
        A wrapper around the TCP socket API
    '''

    def __init__(self, server_address):
        ''' Constructor, store global ports in use '''
        self.client_map = {}
        self.server = server_address
        self.num_currently_sending = 0

    def connect(self, filename, ports):
        ''' Set ports for sending a particular file

            PARAMETERS: filename - name of file associated with ports
        '''
        if self.client_map.get(filename):
            logger.debug("Ports already set for filename: %s", filename)
            return

        self.client_map[filename] = {'ports': ports, 'sockets': []}
        for port in ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.debug("Server connection: %s:%d", self.server, port)
            self.client_map[filename]['sockets'].append(s)

    def disconnect(self):
        ''' Closes all connections for all files '''
        for file_name in self.client_map:
            for s in self.client_map[file_name]['sockets']:
                s.close()
        self.client_map = {}

    def send(self, segment):
        ''' Send a single segment to the server '''
        cur_socket = None
        cur_port = None
        lock = Lock()
        # Segment removed from queue but not sent, mark as still sending
        lock.acquire()
        self.num_currently_sending += 1
        lock.release()
        # Lock client_map to get one socket
        while not cur_socket:
            try:
                lock.acquire()
                cur_socket = self.client_map[segment['filename']]['sockets'].pop()
                cur_port = self.client_map[segment['filename']]['ports'].pop()
                lock.release()
            except IndexError:
                lock.release()
                # All sockets in use wait
                logger.debug("All sockets in use, wait...")
                time.sleep(3)

        data = json.dumps(segment).encode('utf-8')
        logger.debug("Sending (%db) segment on port (%d):\n%s", sys.getsizeof(data),
                     cur_port, str(segment))
        cur_socket.sendto(data, (self.server, cur_port))
        time.sleep(1)
        # Add socket back for re-use
        lock.acquire()
        self.client_map[segment['filename']]['sockets'].append(cur_socket)
        self.client_map[segment['filename']]['ports'].append(cur_port)
        self.num_currently_sending -= 1
        lock.release()
        return
