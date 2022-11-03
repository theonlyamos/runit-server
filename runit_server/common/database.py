#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2022-08-06 17:37:00
# @Author  : Amos Amissah (theonlyamos@gmail.com)
# @Link    : link
# @Version : 1.0.0

from typing import Type
from .mongodb import MongoDB
from .mysql import MysqlDB

class Database():
    db: Type[MysqlDB]|Type[MongoDB]|None = None
    dbms: str|None = None

    @staticmethod
    def initialize(dbsettings: dict, app=None):
        Database.dbms = dbsettings['dbms']
        if dbsettings['dbms'] == 'mongodb':
            MongoDB.initialize(app, dbsettings['dbhost'], 
                dbsettings['dbport'],
                dbsettings['dbname'])
            Database.db = MongoDB
            
        elif dbsettings['dbms'] == 'mysql':
            MysqlDB.initialize(dbsettings['dbhost'], 
                dbsettings['dbport'],
                dbsettings['dbname'],
                dbsettings['dbusername'],
                dbsettings['dbpassword'])
            Database.db = MysqlDB
    
    @staticmethod
    def setup():
        if Database.dbms == 'mysql':
            print('[-!-] Creating Database Tables')

            print('[~] Creating users table')
            Database.db.query('''
            CREATE TABLE IF NOT EXISTS users
            (
            id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name varchar(50) not null,
            email varchar(100) not null,
            password varchar(500) not null,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            ''')

            print('[~] Creating projects table')
            Database.db.query('''
            CREATE TABLE IF NOT EXISTS projects
            (
            id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name varchar(50) not null,
            user_id int(11) not null,
            version varchar(10) null,
            description text(500) null,
            homepage varchar(50) null,
            language varchar(50) not null,
            start_file varchar(50) not null,
            author varchar(200) null,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            ''')
            
            print('[~] Creating functions table')
            Database.db.query('''
            CREATE TABLE IF NOT EXISTS functions
            (
            id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name varchar(50) not null,
            filename varchar(100) not null,
            user_id int(11) not null,
            language varchar(50) not null,
            description text(500) null,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            ''')

            print('[~] Creating roles table')
            Database.db.query('''
            CREATE TABLE IF NOT EXISTS roles
            (
            id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name varchar(50) not null,
            permission_ids text(2000) null,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            ''')

            print('[~] Creating permissions table')
            Database.db.query('''
            CREATE TABLE IF NOT EXISTS permissions
            (
            id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name varchar(50) not null,
            description text(500) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            ''')

            print('[~] Creating permissions table')
            Database.db.query('''
            CREATE TABLE IF NOT EXISTS permissions
            (
            id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name varchar(50) not null,
            description text(500) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            ''')

            print('[~] Creating activities table')
            Database.db.query('''
            CREATE TABLE IF NOT EXISTS activities
            (
            id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name varchar(50) not null,
            user_role enum('user','admin') default 'user',
            user_id varchar(11) not null,
            table_name varchar(100) NOT NULL,
            affected_row int(11) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            ''')
            print('[#] Tables created!')

            print('[~] Creating administrators table')
            Database.db.query('''
            CREATE TABLE IF NOT EXISTS admins
            (
            id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
            name varchar(50) not null,
            username varchar(100) not null,
            password varchar(500) not null,
            role_id int(11) not null,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            ''')
