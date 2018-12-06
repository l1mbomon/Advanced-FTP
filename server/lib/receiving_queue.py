#!/bin/python3

import os
import logging
import time
import gevent
from gevent import queue, monkey, lock
from server_socket import ServerSocket
import server_db

monkey.patch_all()
logger = logging.getLogger(__name__)
fh = logging.FileHandler('server/.data/server.log')
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)

class ReceivingQueue():
    ''' Class to receiving queue process '''

    def __init__(self, segment_size, server_dir, port_max):
        ''' Create ReceivingQueue object '''
        self.threads = {}
        # gevent provides a synchronized queue (locking is handled)
        self.host_queues = {}
        self.socket_mgr = ServerSocket()
        self.segment_size = segment_size
        self.base_dir = server_dir
        self.max_num_ports_per_host = port_max

    def add(self, segments, host):
        ''' A list of segments to the sending queue'''
        for sgmt in segments:
            self.host_queues[host].put(sgmt)

    def can_receive(self, hostname, filename):
        ''' Determine if the load is not too much to allow receiving from another client
        '''
        return self.socket_mgr.can_receive(hostname=hostname, filename=filename)

    def init_receive(self, hostname, segment_size, num_segments, filename):
        ''' Get ports for client and return. Initiate separate thread
            which will connect with client and create more threads to
            handle the file transfer. Will all close upon completion, no
            joining necessary.
        '''
        max_ports = self.max_num_ports_per_host
        # If load is over 50%, only allocate half max num of ports
        if self.socket_mgr.check_load():
            max_ports = (self.max_num_ports_per_host + 1) / 2
        port_list = self.socket_mgr.allocate_ports(hostname, filename, maxAllocated=max_ports)
        if self.socket_mgr.host_listen(hostname, filename):
            gevent.spawn(self.run_receive, hostname, segment_size, num_segments, filename)
        else:
            port_list = []
        return port_list

    def run_receive(self, hostname, segment_size, num_segments, filename):
        ''' The main thread which will manage the file transfer with a client
            Block waiting to accept client connection after listening on ports.
            One connected, start reading & applying
        '''
        logger.debug("Starting receive thread. Accept connection from client: %s, for file: %s",
                     hostname, filename)
        # initialize host queue if not already done so
        qLock = lock.RLock()
        qLock.acquire()
        if not self.host_queues.get(hostname):
            self.host_queues[hostname] = queue.Queue()
        qLock.release()
        self.receive(hostname, segment_size, num_segments, filename)
        return

    def receive(self, hostname, segment_size, num_segments, filename):
        ''' Iterate continuously Reading segments from client using Socket manager.
            Will create another separate thread to apply segments to file system as they
            are added to the queue.

            One "apply" thread is created per file transaction and terminated once the
            segments have all been read (after a timeout and sleep). This wait should be
            enough for final segments to be written.  However, the queue will not
            expected to be empty as other file transfers may be running.

            **Though there's one apply thread per file transfer, each apply thread may
            write segments from any of the files being currently transfered.

            THREAD function
        '''
        # start thread
        fs_apply_thread = gevent.spawn(self.apply, hostname)
        i = 0
        Stime= time.time()
        while i < num_segments:
            # Read from client
            segments = self.socket_mgr.read(hostname, segment_size, filename)
            for seg in segments:
                self.host_queues[hostname].put(seg)
                i += 1
            time.sleep(3)
        duration=time.time()-Stime
        duration = "{0:.2f}s".format(duration)
        server_db.add_record(hostname, filename, duration, segment_size, self.max_num_ports_per_host)
        logger.debug("Finished receiving all segments for host/file: %s/%s", hostname, filename)
        # Kill thread
        while self.host_queues[hostname].qsize():
            time.sleep(3)
        fs_apply_thread.kill()
        self.socket_mgr.disconnect(hostname, filename)
        logger.debug("Finished applying all segments for host/file: %s/%s", hostname, filename)

    def apply(self, hostname):
        ''' Iterate continuously looking to segments in queue to write to FS

            THREAD function
        '''
        logger.debug("Starting apply thread")
        while True:
            if self.host_queues[hostname].qsize():
                # Get next segment in queue to Write to FS
                new_segment = self.host_queues[hostname].get()
                idx = new_segment['index']
                fname = new_segment['filename']
                logger.debug("Applying next segment, file (%s) - index (%d)", fname, idx)
                # Poll DB for file
                file_obj = server_db.get_file(hostname, new_segment['filename'])
                if file_obj:
                    # File already exists
                    with open(file_obj[2], 'r+') as existing_file:
                        existing_file.seek(self.segment_size * idx)
                        existing_file.write(new_segment['content'])
                    if server_db.get_segment(hostname, fname, idx):
                        # Update existing segment at index for file
                        server_db.update_segment(hostname, fname, idx, new_segment['sha'])
                    else:
                        # Add new segment
                        server_db.add_segment(hostname, fname, idx, new_segment['sha'])
                else:
                    # Check directories exist
                    fullpath = "{}/{}_dir/{}".format(self.base_dir, hostname, fname)
                    i = len(self.base_dir)
                    while i < fullpath.rfind('/'):
                        if not os.path.exists(fullpath[:fullpath.find('/', i)]):
                            os.mkdir(fullpath[:fullpath.find('/', i)])
                        i = fullpath.find('/', i) + 1
                    # Will always need to add new segment and file
                    with open(fullpath, 'w+') as new_file:
                        new_file.seek(self.segment_size * idx)
                        new_file.write(new_segment['content'])
                    server_db.add_file(hostname, fname, fullpath)
                    server_db.add_segment(hostname, fname, idx, new_segment['sha'])
            else:
                time.sleep(3)
