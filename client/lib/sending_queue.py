#!/bin/python3

import logging
import time
import gevent
from gevent import queue, monkey
from client_socket import ClientSocket

monkey.patch_all()
logger = logging.getLogger(__name__)
fh = logging.FileHandler('client/.data/client.log')
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)

class SendingQueue():
    ''' Class to sending queue process '''

    def __init__(self, server_address):
        ''' Create SendingQueue object '''
        self.threads = []
        # gevent provides a synchronized queue (locking is handled)
        self.queue = queue.Queue()
        self.socket_mgr = ClientSocket(server_address)

    def add(self, segments):
        ''' A list of segments to the sending queue'''
        for sgmt in segments:
            self.queue.put(sgmt)

    def send(self):
        ''' Iterate continuously looking to send entries in queue
        '''
        logger.debug("Started sending thread")
        while True:
            if self.queue.qsize():
                self.socket_mgr.send(self.queue.get())
                time.sleep(1) # send is non-blocking, don't over send
            else:
                time.sleep(3)

    def start_sending(self, filename, port_list, segments, num_threads):
        ''' Start a separate thread to begin sending
            from the send queue. Should be started before
            breaking up files. As segments are added to
            queue, it will send, until stop_sending is called.
        '''
        self.add(segments)
        self.socket_mgr.connect(filename, port_list)
        for i in range(num_threads):
            self.threads.append(gevent.spawn(self.send))
        return

    def complete_sending(self):
        ''' Join all threads created during this send process.
            This should be done between searching for new files
        '''
        # Wait till rest of send queue is empty
        # ASSUME no more is being added at this point
        logger.debug("Waiting for all segments to send before completing send")
        while self.queue.qsize():
            time.sleep(3)
        # Wait till sending finished
        while self.socket_mgr.num_currently_sending:
            logger.debug("Waiting for (%d) segments to finish sending",
                         self.socket_mgr.num_currently_sending)
            time.sleep(3)
        # Kill any threads created
        gevent.killall(self.threads, timeout=5)
        self.threads = []
        self.socket_mgr.disconnect()
