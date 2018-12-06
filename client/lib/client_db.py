#!/bin/python3

'''
    File to contain functions for statically working with DB.

    Cost of getting SQLite DB Connection is cheap, we will avoid
    having to maintain an open connection in program.
'''


import sqlite3
import logging

DB_URL = 'client/.data/client.db'
logger = logging.getLogger(__name__)
fh = logging.FileHandler('client/.data/client.log')
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
        logger.error("Error getting DB. Error: %s", str(err))

    return conn

def start(forceCreate=False):
    '''
        Will ensure DB has been created,
        will create tables if own hostname is not found.

        RETURNS:    True if the db is ready to use
    '''
    if not forceCreate and get_file('db_check'):
        logger.info("DB has already been initialized, reusing")
    else:
        logger.info("Creating new DB")
        initilize_db()


################################
#   GENERIC WRAPPER FUNCITONS
################################

def execute(sql_cmd, params_obj):
    ''' Add a host to the client users table '''
    c = get_db()
    conn = c.cursor()
    try:
        conn.execute(sql_cmd, params_obj)
    except Exception as error:
        print(str(error))
        logger.error("Failed to fetch all from query:\n %s\nParams: %s",
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
        conn.execute(sql_cmd, params_obj)
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

def get_file(filename):
    ''' Get file object based on filename '''
    params = (filename,)
    sql = 'SELECT * FROM files WHERE file_path=?'
    return fetch_one(sql, params)


#########################
#   ADD FUNCITONS
#########################

def add_file(filename, last_modified):
    ''' Add a file to the client files table '''
    params = (filename, last_modified,)
    sql = 'INSERT INTO files(file_path, last_modified) values (?, ?)'
    execute(sql, params)

def update_file(filename, last_modified):
    ''' Update existing file in the client files table '''
    params = (last_modified, filename,)
    sql = 'UPDATE files SET last_modified=? WHERE file_path=?'
    execute(sql, params)

def initilize_db():
    ''' Create tables, and set initial information as needed '''
    c = get_db()
    conn = c.cursor()
    # Remove any tables left over
    conn.execute('DROP TABLE IF EXISTS files')

    # Files Table
    conn.execute('''CREATE TABLE files (file_path text PRIMARY KEY, last_modified text)''')
    # Add client as initial user (will help determine if we need to re-create db later)
    db_check = ("db_check", "default",)
    conn.execute('''INSERT INTO files(file_path, last_modified) values (?, ?)''', db_check)

    conn.close()
    c.commit()
    c.close()
