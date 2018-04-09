db = {
    'charles': { 'name': 'hieunc', 'password': '123'},
}

def memory_authenticate(name, password):
    if(db.has_key(name) and (db[name]['password'] == password)):
        return db[name]
    return None

def full_public(name,password):
    return dict(name=name, password=password)

authenticate=full_public
