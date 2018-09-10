# jsonify(Flask url shortener, Flask image/files with API)
### A Flask url shortener also Image/Files hosting with simple interface and json! (Also a nice API)

Based on: https://github.com/richyvk/flask-url-shortener
Redesigned for python3 and changed html to my version

### Upload files (Need authorization, default: (admin, admin))
```py
from requests import post

# Open files
data = open('file.ext', 'rb') # Will auto-detect image and move it to another folder

#r = post('http://localhost', files={"files": data}, auth=('admin', 'admin')) # With automated filename
#r = post('http://localhost', files={"files": data}, data={"filename": "myfile.ext"}, auth=('admin', 'admin')) # With custom defined filename

print(r.text)
```

### Make short url using POST request
```py
from requests import post

# Change localhost to anything you set
r = post('localhost', data={'url': 'https://that.one/long/ass/url'}
print(r.text)
```

### Delete Short Link (Need authorization, default: (admin, admin))
```py
from requests import delete

# Change localhost to anything you set
r = delete('localhost', data={'short_url': 'https://myhost.tld/abcdf'}, auth=('admin', 'admin'))
print(r.text)
```

# Flask url shortener

A simple URL shortener like tinyurl that I'm working on. Buoilt with Python and using the [Flask](http://flask.pocoo.org/docs/0.10/) webapp microframework.

Currently uses a pickled list of (url,unique_hash) tuples to sort previously shortened URL data.

May move to database for the storage at some point, but wanted it to start as simple as possible.