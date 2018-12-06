#!/bin/python3
'''
    File to contain functions for statically working with DB.

    Cost of getting SQLite DB Connection is cheap, we will avoid
    having to maintain an open connection in program.
'''


import sqlite3
import logging

DB_URL = 'server/.data/server.db'
logger = logging.getLogger(__name__)
fh = logging.FileHandler('server/.data/server.log')
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)

def get_db():
    '''
        Get DB connection,
        will create DB if not already made.

        RETURNS:    DB connection handle for subsequent use
    '''
    conn = None
    try:
        conn = sqlite3.connect(DB_URL)
    except Exception as err:
        logger.error("Error getting DB. Error: " + str(err))

    return conn

def start(forceCreate=False):
    '''
        Will ensure DB has been created,
        will create tables if own hostname is not found.

        RETURNS:    True if the db is ready to use
    '''
    db_check = get_host('db-check')
    if not forceCreate and db_check and db_check[0] == 'db-check':
        logger.info("DB has already been initialized, reusing")
    else:
        logger.info("Creating new DB")
        initilize_db()


################################
#   GENERIC WRAPPER FUNCITONS
################################

def execute(sql_cmd, params_obj):
    ''' Add a host to the server users table '''
    c = get_db()
    conn = c.cursor()
    try:
        conn.execute(sql_cmd, params_obj)
    except Exception as error:
        logger.error(str(error))
        logger.error("Failed to execute:\n %s\nParams: %s",
                     str(sql_cmd), str(params_obj))
    conn.close()
    c.commit()
    c.close()

def fetch_one(sql_cmd, params_obj):
    '''
        Run arbitrary command then fetch one

        RETURNS:  False if command couldn't be executed
    '''
    c = get_db()
    conn = c.cursor()
    try:
        conn.execute(sql_cmd, params_obj)
        ret = conn.fetchone()
    except Exception as error:
        conn.close()
        c.close()
        logger.error(str(error))
        logger.error("Failed to fetch one from query:\n %s\nParams: %s",
                     str(sql_cmd), str(params_obj))
        return None

    conn.close()
    c.close()
    return ret

def fetch_all(sql_cmd, params_obj):
    '''
        Run arbitrary command then fetch all

        RETURNS:  False if command couldn't be executed
    '''
    c = get_db()
    conn = c.cursor()
    try:
        if params_obj:
            conn.execute(sql_cmd, params_obj)
        else:
            conn.execute(sql_cmd)
        ret = conn.fetchall()
    except Exception as error:
        conn.close()
        c.close()
        logger.error(str(error))
        logger.error("Failed to fetch all from query:\n %s\nParams: %s",
                     str(sql_cmd), str(params_obj))
        return None

    conn.close()
    c.close()
    return ret

#########################
#   GET FUNCITONS
#########################

def get_host(hostname):
    ''' Get a user object from DB by hostname '''
    host = (hostname,)
    sql = 'SELECT * FROM users WHERE hostname=?'
    return fetch_one(sql, host)

def get_file(hostname, filename):
    ''' Get file object based on filename '''
    params = (filename, hostname,)
    sql = 'SELECT * FROM files WHERE filename=? AND hostname=?'
    return fetch_one(sql, params)

def get_fileID(filename, hostname):
    ''' Mostly used internally, get fileID based on filename '''
    params = (filename, hostname,)
    sql = 'SELECT (fileID) FROM files WHERE filename=? AND hostname=?'
    ret = fetch_one(sql, params)
    if ret:
        return ret[0]
    else:
        return 0

def get_file_segments(filename, hostname):
    ''' Get file segments based on filename and host '''
    fileID = get_fileID(filename, hostname)
    params = (fileID,)
    sql = 'SELECT segmentSHA, segmentIdx FROM segments WHERE fileID=? ORDER BY segmentIdx ASC'
    return fetch_all(sql, params)

def get_segment(hostname, filename, index):
    ''' Get segment based on filename and host and index '''
    fileID = get_fileID(filename, hostname)
    params = (fileID, index,)
    sql = 'SELECT segmentSHA, segmentIdx FROM segments WHERE fileID=? AND segmentIdx=? ORDER BY segmentIdx ASC'
    return fetch_all(sql, params)

def get_records():
    ''' Get all analystical records '''
    sql = 'SELECT * FROM performance'
    return fetch_all(sql, None)



#########################
#   ADD FUNCITONS
#########################

def add_host(hostname, directory):
    ''' Add a host to the server users table '''
    host = (hostname, directory,)
    sql = 'INSERT INTO users(hostname, directory) values (?, ?)'
    execute(sql, host)

def add_file(hostname, filename, fullpath):
    ''' Add a file to the server files table '''
    params = (hostname, filename, fullpath,)
    sql = 'INSERT INTO files(hostname, filename, full_path) values (?, ?, ?)'
    execute(sql, params)

def add_segment(hostname, filename, idx, sha):
    ''' Add a file segment to the Segments table '''
    fileID = get_fileID(filename, hostname)
    params = (fileID, sha, idx,)
    sql = 'INSERT INTO segments(fileID, segmentSHA, segmentIdx) values (?, ?, ?)'
    execute(sql, params)

def update_segment(hostname, filename, idx, sha):
    ''' Add a file segment to the Segments table '''
    fileID = get_fileID(filename, hostname)
    params = (sha, fileID, idx,)
    sql = 'UPDATE segments SET segmentSHA=? WHERE fileID=? AND segmentIdx=?'
    execute(sql, params)

def add_record(hostname,filename, duration, seg_size, port_max):
    record = (hostname,filename, duration, seg_size, port_max,)
    sql ='INSERT INTO performance(hostname, filename, duration, seg_size, port_max) values (?,?,?,?,?)'
    execute(sql, record)

def initilize_db():
    ''' Create tables, and set initial information as needed '''
    c = get_db()
    conn = c.cursor()
    # Remove any tables left over
    conn.execute('DROP TABLE IF EXISTS users')
    conn.execute('DROP TABLE IF EXISTS files')
    conn.execute('DROP TABLE IF EXISTS segments')
    conn.execute('DROP TABLE IF EXISTS performance')

    # Users Table
    conn.execute('''CREATE TABLE users (hostname text PRIMARY KEY, directory text)''')
    # Files Table
    conn.execute('''CREATE TABLE files (fileID integer PRIMARY KEY, filename text, full_path text, hostname text,
                        FOREIGN KEY (hostname) REFERENCES users (hostname),
                        UNIQUE (filename, hostname))''')
    # File Segments Table
    conn.execute('''CREATE TABLE segments (fileID integer, segmentSHA text, segmentIdx integer,
                        FOREIGN KEY (fileID) REFERENCES files (fileID),
                        PRIMARY KEY (fileID, segmentIdx))''')
    conn.execute('''CREATE TABLE performance (hostname text, filename text, duration text,
                                              seg_size integer, port_max integer )''')

    # Add server as initial user (will help determine if we need to re-create db later)
    system_host = ('db-check', "default",)
    conn.execute('''INSERT INTO users(hostname, directory) values (?, ?)''', system_host)

    conn.close()
    c.commit()
    c.close()
