# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:
#
# Copyright (c) 2013, Battelle Memorial Institute
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are those
# of the authors and should not be interpreted as representing official policies,
# either expressed or implied, of the FreeBSD Project.
#

# This material was prepared as an account of work sponsored by an
# agency of the United States Government.  Neither the United States
# Government nor the United States Department of Energy, nor Battelle,
# nor any of their employees, nor any jurisdiction or organization
# that has cooperated in the development of these materials, makes
# any warranty, express or implied, or assumes any legal liability
# or responsibility for the accuracy, completeness, or usefulness or
# any information, apparatus, product, software, or process disclosed,
# or represents that its use would not infringe privately owned rights.
#
# Reference herein to any specific commercial product, process, or
# service by trade name, trademark, manufacturer, or otherwise does
# not necessarily constitute or imply its endorsement, recommendation,
# r favoring by the United States Government or any agency thereof,
# or Battelle Memorial Institute. The views and opinions of authors
# expressed herein do not necessarily state or reflect those of the
# United States Government or any agency thereof.
#
# PACIFIC NORTHWEST NATIONAL LABORATORY
# operated by BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
# under Contract DE-AC05-76RL01830

#}}}


import datetime
import logging
import sys
import uuid
import sqlite3

from volttron.platform.agent.base_historian import BaseHistorianAgent
from volttron.platform.agent import utils, matching
from volttron.platform.messaging import topics, headers as headers_mod
from zmq.utils import jsonapi
import settings
import os, os.path
import errno


utils.setup_logging()
_log = logging.getLogger(__name__)
from pprint import pprint


def SQLiteHistorianAgent(config_path, **kwargs):

    config = utils.load_config(config_path)

    class Agent(BaseHistorianAgent):
        '''This is a simple example of a historian agent that writes stuff 
        to a SQLite database. It is designed to test some of the functionality
        of the BaseHistorianAgent.
        '''
        
        def publish_to_historian(self, to_publish_list):
            #self.report_all_published()
            c = self.conn.cursor()
            print 'Publish info'
            for x in to_publish_list:
                ts = x['timestamp']
                topic = x['topic']
                value = x['value']
                
                topic_id = self.topics.get(topic)
                
                if topic_id is None:
                    c.execute('''INSERT INTO topics values (?,?)''', (None, topic))
                    c.execute('''SELECT last_insert_rowid()''')
                    row = c.fetchone()
                    topic_id = row[0]
                    self.topics[topic] = topic_id
                
                c.execute('''INSERT OR REPLACE INTO data values(?, ?, ?)''', 
                          (ts,topic_id,jsonapi.dumps(value)))
                
                pprint(x)
            print 'count:', len(to_publish_list)
            
            self.conn.commit()
            c.close()     
            
            self.report_all_published()       
        
        def historian_setup(self):
            self.topics={}
            db_path = os.path.expanduser(config.db)
            db_dir  = os.path.dirname(db_path)
            
            try:
                os.makedirs(db_dir)
            except OSError as exc:
                if exc.errno != errno.EEXIST or not os.path.isdir(db_dir):
                    raise

            self.conn = sqlite3.connect(db_path, 
                                         detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        
            
            self.conn.execute('''CREATE TABLE IF NOT EXISTS data 
                                (ts timestamp NOT NULL,
                                 topic_id INTEGER NOT NULL, 
                                 value_string TEXT NOT NULL, 
                                 UNIQUE(ts, topic_id))''')
            
            self.conn.execute('''CREATE INDEX IF NOT EXISTS data_idx
                                ON data (ts ASC)''')

            self.conn.execute('''CREATE TABLE IF NOT EXISTS topics 
                                (topic_id INTEGER PRIMARY KEY, 
                                 topic_name TEXT NOT NULL,
                                 UNIQUE(topic_name))''')
            
            c = self.conn.cursor()
            c.execute("SELECT * FROM topics")
            for row in c:
                self.topics[row[1]] = row[0]
        
            c.close()
            self.conn.commit()
        
    Agent.__name__ = 'SQLiteHistorianAgent'
    return Agent(**kwargs)
            
    
    
def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    try:
        utils.default_main(SQLiteHistorianAgent,
                           description='Historian agent that saves a history to a sqlite db.',
                           argv=argv)
    except Exception as e:
        print e
        _log.exception('unhandled exception')


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
