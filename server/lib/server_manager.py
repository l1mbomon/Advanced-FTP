#!/bin/python3

import os
import logging
import yaml
import server_db
from receiving_queue import ReceivingQueue

logger = logging.getLogger('server-manager')
fh = logging.FileHandler('server/.data/server.log')
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
DEFAULT_CONFIG_PATH = 'etc/default_config.yaml'
DIVIDER = '--------------------------------------'


class ServerManager():
    ''' Class to manager server process '''

    def __init__(self, config_path=None):
        ''' Create ServerManager object '''

        if not config_path:
            config_path = DEFAULT_CONFIG_PATH
        logger.info("%s\nLoading configuration: %s", DIVIDER, config_path)
        with open(config_path, 'r') as config_file:
            config = yaml.load(config_file)
            self.client_data_dir = "{}/{}".format(os.getcwd(),
                                                  config['server_config']['client_data_dir'])
            self.segment_size = config['server_config']['segment_size']

            # Print config
            logger.debug("\tClient Data Directory: %s", self.client_data_dir)
            logger.debug("\tSegment Size: %s", self.segment_size)
            port_max = config['server_config']['max_num_ports_per_host']
            logger.debug("\tMax Ports Per Host/File: %d", port_max)
            logger.debug("End configuration\n%s", DIVIDER)
            self.receiving_queue = ReceivingQueue(self.segment_size, self.client_data_dir,
                                                  port_max)


    def start(self):
        ''' Start DB '''
        server_db.start()

    def register(self, hostname):
        ''' Register client with server '''
        try:
            # Allocate space based on hostname. DB enforces hostname to be unique
            directory = "{}_dir".format(hostname)
            if server_db.get_host(hostname):
                logger.info("Client already registered: %s", str(hostname))
            else:
                logger.info("Registering new client: %s", str(hostname))
                # As host to DB
                server_db.add_host(hostname, directory)
            # Server could be ported to new host. DB has client data, but must create directory
            # Need to clear entries for this host in files&segments tables
            if not os.path.isdir(self.client_data_dir + directory):
                logger.info("Allocating new directory: (%s) for client: (%s)",
                            self.client_data_dir + directory, hostname)
                os.mkdir(self.client_data_dir + directory)
        except Exception as error:
            logger.error("Failed to register with server. Error: %s", str(error))
            return None

        # Tell client segment size
        return self.segment_size

    def get_file_segments(self, filename, hostname):
        ''' Get ordered list of file segments stored for a particular file.
            If file doesn't exist return empty list.
            None will indicate error.
        '''
        return server_db.get_file_segments(filename=filename, hostname=hostname)

    def can_receive(self, hostname, filename):
        ''' Determine if the load is not too much to allow receiving from another client '''
        return self.receiving_queue.can_receive(hostname=hostname, filename=filename)

    def init_receive(self, hostname, segment_size, num_segments, filename):
        ''' Listen for client connections '''
        port_list = self.receiving_queue.init_receive(hostname, segment_size, num_segments, filename)
        return port_list
