
DATA_FILENAME = 'data.json'
USER_FILENAME = 'registered_ids'
DB_FILENAME = 'database.db'


def migrate_1():
    import json
    from utils import readPickle
    transactions = {}
    for name, lst in readPickle(getdata=True).items(): # type: ignore
        transactions[name]=[]
        for entry in lst:
            r=entry.dict
            r['time']=r['time'].timestamp()
            transactions[name].append(r)
    
    with open(USER_FILENAME) as f:
        user_data=[{'server':'jabber', 'identifier': ln.replace(' ', '@')} for ln in f.read().strip().splitlines() if ln and not ln.startswith('#')]
    
    print("Dumped {} transactions and {} users.".format(sum([len(record) for record in transactions]), user_data))
    with open(DATA_FILENAME, 'w') as f:
        json.dump({'transactions': transactions, 'users': user_data}, f, indent=4)


def migrate_2(drop_all=True):
    import json
    from datetime import datetime
    from database import SynapsisDB, User, Transaction
    
    db=SynapsisDB(DB_FILENAME)
    
    def startswith_any(s, matchers):
        for m in matchers:
            if s.startswith(m):
                return True
        return False
    
    # Migrate transactions
    with open(DATA_FILENAME) as f:
        data=json.load(f)
        transactions = data['transactions']
        users = data['users']
    print("Loaded {} transactions and {} users.".format(len(transactions), len(users)))
    transactions=[e for lst in transactions.values() for e in lst] # flatten
    for e in transactions:
        e['time']=datetime.fromtimestamp(e['time'])
        e['refID']=e.get('refID', '?') or '?'
        if startswith_any(e['refID'], ['8', '9']):
            e['executor']='linkaja'
        elif startswith_any(e['refID'], ['RANDOM', 'GUI']):
            e['executor']='digipos'
        elif startswith_any(e['refID'], ['0']):
            e['executor']='mitra_tokopedia'
        else:
            e['executor']=None
    # trying to recover the executor
    for i,e in enumerate(transactions):
        a,b=None,None
        if e['executor']==None:
            if i>0:
                a=transactions[i-1]['executor']
            if i+1<len(transactions):
                b=transactions[i+1]['executor']
            
            if a==b:
                e['executor'] = a
            elif a is not None and b is None:
                e['executor'] = a
            elif a is None and b is not None:
                e['executor'] = b
            else:
                e['executor'] = ''
    for e in transactions:
        e['automator'] = e.pop('executor')
    db.drop_table(Transaction) if drop_all else None
    db.create_table(Transaction)
    print("Inserting {} transactions".format(len(transactions)))
    db.insert_many([Transaction(**e) for e in transactions])
    
    # Migrate users
    db.drop_table(User) if drop_all else None
    db.create_table(User)
    print("Inserting {} users".format(len(users)))
    db.insert_many([User(**data) for data in users])
    # Blocks until CursorProxy has finished inserting and can get data.
    print("Waiting for CursorProxy to finish...")
    list(User.get(User.id==1))
    print("CursorProxy finished processing.")


if __name__ == '__main__':
    DB_FILENAME='test.db'
    TRANSACTIONS_DATA_FILENAME='tests/data.json'
    migrate_2()
