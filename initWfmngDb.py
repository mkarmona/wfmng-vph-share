from wfmng import db
db.drop_all() # optional, use it if you want to erase a previous database
db.create_all()
db.session.commit()
