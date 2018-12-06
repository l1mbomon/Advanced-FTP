#!/bin/python3

import os
import pathlib
import logging
import time
import client_db

logger = logging.getLogger(__name__)
fh = logging.FileHandler('client/.data/client.log')
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)

class ClientWatcher():
    ''' Class to contain tool which will determine which configured files have changed

      CONVENTION FOR FILE NAME is set here.
      The top level directory (configured by client) will be ignored. Filename will
      start relative to that. This sets a consistent format for what a "filename" means,
      so a filename on the server is the same as one the client.

      However, the client will need to know the full path of the file to actually read the
      data. That will be included with the filename as full_path
      Example:
        client-config:
            dir1: /home/wpmoore2/docs/ncsu

        file changed: ['/home/wpmoore2/docs/ncsu/sample.txt',
                       '/home/wpmoore2/docs/ncsu/hw/hw1.tex']

        List returned would be:
            [
                {'filename': 'sample.txt', 'full_path': '/home/wpmoore2/docs/ncsu/sample.txt'},
                {'filename': 'hw/hw1.tex', 'full_path': '/home/wpmoore2/docs/ncsu/hw/hw1.tex'}
            ]
    '''

    def __init__(self, dir_map):
        ''' Constructor for ClientWatcher
          store directories to watch
        '''
        self.dir_map = dir_map

    def sleep(self):
        ''' Sleep based on the directory with the least
          amount of time until being checked
        '''
        min_time = min([self.dir_map[key]['counter'] for key in self.dir_map])
        logger.debug("Sleep for %ds", min_time)
        time.sleep(min_time)
        # Decrease counters
        for key in self.dir_map:
            self.dir_map[key]['counter'] -= min_time


    def check_fs(self):
        ''' Determine which files have changed based on DB, then update DB.
          Return list of file names changed.
        '''
        # Check directories based on which ones have a counter set to zero or less
        # Reset each expired counter to the corresponding 'interval'
        files_to_send = []
        dir_to_check = []
        for key in self.dir_map:
            if self.dir_map[key]['counter'] <= 0:
                dir_to_check.append(key)
                # Reset counter
                self.dir_map[key]['counter'] = self.dir_map[key]['interval']

        for directory in dir_to_check:
            logger.debug("Checking directory: (%s)", directory)
            for dName, sdName, fList in os.walk(directory):
                for filename in fList:
                    next_file_path = os.path.join(dName, filename)
                    cur_time = str(pathlib.Path(next_file_path).stat().st_mtime)
                    cur_time = cur_time[cur_time.index('.') + 1:]
                    file_obj = client_db.get_file(next_file_path)
                    # File exists - compare timestamps
                    if file_obj:
                        if file_obj[1] != cur_time:
                            # File updated
                            # Update entry in db
                            client_db.update_file(next_file_path, cur_time)
                            next_filename = next_file_path.replace(directory, '')
                            if next_filename[0] == '/':
                                next_filename = next_filename[1:]
                            next_file_obj = {'filename': next_filename,
                                             'full_path': next_file_path}
                            # Add file to send
                            files_to_send.append(next_file_obj)
                        else:
                            # File not changed
                            continue
                    else:
                        # File doesn't exist - always send
                        # Add to db
                        client_db.add_file(next_file_path, cur_time)
                        next_filename = next_file_path.replace(directory, '')
                        if next_filename[0] == '/':
                            next_filename = next_filename[1:]
                        next_file_obj = {'filename': next_filename,
                                         'full_path': next_file_path}
                        # Add file to send
                        files_to_send.append(next_file_obj)

        return files_to_send
