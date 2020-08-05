__author__ = "Cobbin"

from app import app, db

db.create_all()
app.run(debug=app.config['DEBUG'])
