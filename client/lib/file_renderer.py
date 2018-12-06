#!/bin/python3

import os
import hashlib
import logging
import ntpath
import tempfile
import shutil
import sys
import json

logger = logging.getLogger(__name__)
fh = logging.FileHandler('client/.data/client.log')
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)

TEMP_DIR = 'client/.data/'

class FileRenderer():
    '''
        Class to handle creating segments and determining which to send
    '''

    def __init__(self):
        ''' Create FileRenderer object '''
        self.segment_size = None


    def process_file(self, file_obj, server_segments):
        ''' Main entrypoint for class, much like the interface of the class
            returns segments to send
        '''
        if not self.segment_size:
            logger.error("Segment size not set. Cannot process file (%s)", file_obj['filename'])

        segments_to_send = []
        # Copy file to temp location under client/.data/
        try:
            temp_path = os.path.join(TEMP_DIR, ntpath.basename(tempfile.mktemp()))
            shutil.copy2(file_obj['full_path'], temp_path)
            # Read entire file by segment size chunks, create segments and
            filesize = os.path.getsize(temp_path)
            bytes_left = filesize
            idx = 0
            skip_count = 0
            server_len = len(server_segments) if server_segments else 0
            with open(temp_path, 'rb') as temp_file:
                while bytes_left > 0:
                    read_size = self.segment_size
                    if read_size > bytes_left:
                        read_size = bytes_left
                    content_bytes = temp_file.read(self.segment_size)
                    content = content_bytes.decode('utf-8')
                    # NOTE: We must take sha of the encoded content (bytes)
                    seg_sha = hashlib.sha256(content_bytes).hexdigest()
                    # If segment sha and idx match, effectively same stuff in same place
                    # within file on server, skip this segment.
                    if idx >= server_len or server_segments[idx][0] != seg_sha:
                        seg = {'sha': seg_sha,
                               'filename': file_obj['filename'], 'content': content,
                               'index': idx}
                        segments_to_send.append(seg)
                    else:
                        skip_count += 1

                    idx += 1
                    bytes_left -= read_size
        except Exception as file_error:
            logger.error("Failed to process file (%s). Error:\n%s", str(file_obj), str(file_error))
            return None
        logger.debug("Number of segments skipped for file (%s): (%d)", file_obj['filename'], skip_count)

        return segments_to_send
