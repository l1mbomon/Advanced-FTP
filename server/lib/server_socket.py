#!/bin/python3

import json
import socket
import logging
from threading import Lock

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
fh = logging.FileHandler('server/.data/server.log')
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)

START_PORT = 10000
MAX_PORT = 30000
DEFAULT_MAX_ALLOCATED = 1
MAX_ACTIVE_CONNECTIONS = 5
SHA256_DIGEST_SIZE = 32

class ServerSocket():
    ''' Class to store ServerSocket object.
        A wrapper around the TCP socket API
    '''

    def __init__(self):
        ''' Constructor, store global ports in use '''
        self.client_map = {}
        self.open_sockets = 0
        self.used_ports = []

    def can_receive(self, hostname, filename):
        ''' Is load too much? AND host/file isn't already in recieving session '''
        return self.open_sockets < MAX_ACTIVE_CONNECTIONS and \
               not self.client_map.get(hostname, {}).get(filename, None)

    def check_load(self):
        ''' Return True if number of open connections is greater than
            half the capacity
        '''
        return self.open_sockets > (MAX_ACTIVE_CONNECTIONS / 2)

    def allocate_ports(self, hostname, filename, maxAllocated=DEFAULT_MAX_ALLOCATED):
        ''' Register a host by allocating a new set of unused ports. '''
        lock = Lock()
        lock.acquire()
        # Add object for new host
        if not self.client_map.get(hostname):
            self.client_map[hostname] = {}

        if maxAllocated > (MAX_ACTIVE_CONNECTIONS - self.open_sockets):
            maxAllocated = MAX_ACTIVE_CONNECTIONS - self.open_sockets

        # Return one port for now
        port_list = []
        next_port = START_PORT
        ports_allocated = 0
        while next_port < MAX_PORT and ports_allocated < maxAllocated:
            if next_port not in self.used_ports:
                port_list.append(next_port)
                self.used_ports.append(next_port)
                ports_allocated += 1
            next_port += 1

        self.client_map[hostname][filename] = {'ports': port_list, 'sockets': []}
        lock.release()
        logger.debug("Allocated ports: %s", str(port_list))
        return port_list

    def host_listen(self, host, filename):
        ''' Listen on all ports allocated for a host

            PARAMETERS: host - hostname of ports to bind
            RETURNS:    True if bind success, False otherwise
        '''
        lock = Lock()
        lock.acquire()
        try:
            for port in self.client_map[host][filename]['ports']:
                serversocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                serversocket.bind((socket.gethostname(), port))
                serversocket.settimeout(0.5)
                # Allow 5 unaccepted connection before refusing
                self.open_sockets += 1
                self.client_map[host][filename]['sockets'].append(serversocket)
        except Exception as error:
            logger.error("Failed to bind to client (%s) ports (%s).\nError: %s",
                         host, self.client_map[host][filename]['ports'], str(error))
            lock.release()
            self.disconnect(host, filename)
            return False
        lock.release()
        return True

    # def host_connect(self, host, filename):
    #     ''' Connect on each port '''
    #     lock = Lock()
    #     lock.acquire()
    #     temp_socks = self.client_map[host][filename]['sockets']
    #     self.client_map[host][filename]['sockets'] = []
    #     try:
    #         for sock in temp_socks:
    #             conn, _addr = sock[0].accept()
    #             self.client_map[host][filename]['sockets'].append((sock[0], conn))
    #     except Exception as error:
    #         logger.error("Failed to accept client (%s) connection.\nError: %s",
    #                      host, str(error))
    #         lock.release()
    #         self.disconnect(host, filename)
    #         return False
    #     lock.release()
    #     return True


    def read(self, host, segment_size, filename):
        ''' Read on ports based on segment size '''
        segments = []
        for sock in self.client_map[host][filename]['sockets']:
            logger.debug("Recv (%db) client/file: %s/%s. On port: %d", segment_size, host, filename,
                         sock.getsockname()[1])
            new_segment = None
            try:
                raw_data, sender_addr = sock.recvfrom(segment_size, socket.MSG_DONTWAIT)
                raw_data = raw_data.decode('utf-8')
                new_segment = json.loads(raw_data)
                logger.debug("Segment (%db) received from client (%s) for file (%s) index (%d)",
                             segment_size, host, filename, new_segment['index'])
            except Exception:
                # particular socket may not be in current use
                continue
            segments.append(new_segment)
        return segments

    def disconnect(self, hostname, filename):
        ''' Close sockets for file trasaction. '''
        obj = self.client_map[hostname][filename]
        lock = Lock()
        lock.acquire()
        try:
            for port, sock in zip(obj['ports'], obj['sockets']):
                try:
                    logger.debug("Closing port: %d", port)
                    self.used_ports.remove(port)
                    self.open_sockets -= 1
                    sock[0].close()
                except Exception:
                    pass
        except Exception as error:
            logger.error("Error disconnecting: %s", str(error))
        # Clean in memory map
        self.client_map[hostname].pop(filename)
        if not self.client_map[hostname]:
            self.client_map.pop(hostname)
        lock.release()
