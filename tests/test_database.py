import unittest

import secrets
import os
import tempfile
from datetime import datetime

from database import SynapsisDB, Transaction, User


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db_name = tempfile.gettempdir()+secrets.token_hex(4)+'.test.db'
        self.db = SynapsisDB(self.db_name)
    
    def test_DB_Constraints(self):
        self.assertRaises(KeyError, self.db.insert, User())
        self.assertRaises(KeyError, self.db.insert, User(server=''))
        self.assertRaises(KeyError, self.db.insert, User(identifier=''))
        
        self.assertRaises(KeyError, self.db.insert, Transaction(number=''))
        self.assertRaises(KeyError, self.db.insert, Transaction(product_spec=''))
        self.assertRaises(KeyError, self.db.insert, Transaction(refID=''))
        self.assertRaises(KeyError, self.db.insert, Transaction(time=0))
        self.assertRaises(KeyError, self.db.insert, Transaction(number='', product_spec=''))
        self.assertRaises(KeyError, self.db.insert, Transaction(number='', time=''))
        self.assertRaises(KeyError, self.db.insert, Transaction(number='', product_spec='', time=''))
        self.assertRaises(KeyError, self.db.insert, Transaction(product_spec='', refID='', time=''))
    
    def test_DB_Behaviour(self):
        self.assertEqual(User.DB_MANAGER, self.db)
        # Inserts
        data = [
            User(server='test_server', identifier='user1@test.com'), # 0
            User(server='test_server', identifier='user2@test.com'), # 1
            Transaction(number='081081081081', product_spec='prod1', refID=secrets.token_hex(6), time=datetime.now()), # 2
            Transaction(number='081437574563', product_spec='prod2', refID=secrets.token_hex(6), time=datetime.now()), # 3
            Transaction(number='081123211111', product_spec='prod3', refID=secrets.token_hex(6), time=datetime.now().timestamp()), # 4
            Transaction(number='081111111111', product_spec='prod2', refID=secrets.token_hex(6), time=datetime.now().timestamp()), # 5
            Transaction(number='081222222222', product_spec='prod3', refID=secrets.token_hex(6), time=datetime.now()), # 6
            Transaction(number='081333333333', product_spec='prod2', refID=secrets.token_hex(6), time=datetime.now().timestamp()) # 7
        ]
        self.db.insert_many(data)
        
        # Counts
        self.assertEqual(list(User.get(User.server=='test_server')).__len__(), 2)
        self.assertEqual(list(Transaction.get(Transaction.product_spec=='prod1')).__len__(), 1)
        self.assertEqual(list(Transaction.get(Transaction.product_spec=='prod2')).__len__(), 3)
        self.assertEqual(list(Transaction.get(Transaction.product_spec=='prod3')).__len__(), 2)
        
        self.assertEqual(list(User.get(User.server=='test_server', limit=1))[0].identifier, 'user1@test.com')
        self.assertEqual(list(User.get(User.server=='test_server', limit=(1,1)))[0].identifier, 'user2@test.com')
        
        self.assertEqual(list(Transaction.get(Transaction.product_spec=='prod1'))[0].number, '081081081081')
        self.assertEqual(list(Transaction.get(Transaction.number=='081437574563'))[0].product_spec, 'prod2')
        self.assertEqual(list(Transaction.get(Transaction.number=='081123211111'))[0].product_spec, 'prod3')
        
        # can not to a to_dict comparison, because in data, the objects doesn't have ids and their data types haven't been converted yet.
        self.assertIn(data[4].number, [t.number for t in list(Transaction.get(Transaction.time<=data[6].time, Transaction.time>=data[3].time))])
        self.assertIn(data[5].number, [t.number for t in list(Transaction.get(Transaction.time<=data[6].time, Transaction.time>=data[3].time))])
    
    def tearDown(self):
        self.db.drop_model(Transaction)
        self.db.drop_model(User)
        self.db.connection.close()
        if hasattr(self.db.cursor, 'proxy_connection'):
            self.db.cursor.blocking_proxy('connection.close')
        os.remove(self.db_name)
