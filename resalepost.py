# python
import logging
import re
import os

# libraries
import simplejson
import tornado.web
from pymongo.objectid import ObjectId

# local
from resaledecorators import chain, jsonio
from json_validate import *
from db import resale_db

# TODO: better image_url pattern
image_url_pat = re.compile(r'http://\S+\.(jpe?g|png)')
price_pat = re.compile(r'\d*(\.\d{0,2})?')

_post_structure = {
    'title': str,
    'price': price_pat,
    'image_url': optional(image_url_pat),
    'location':{ 'lat': float, 'long': float },
    'short_code': optional(str),
}

# Sample post for testing
{"price": "17", "image_url": "http://foo.com/foo.png", "location": {"lat": 421.0, "long": 11.9}, "title": "from_console"}

class ResalePostHandler(tornado.web.RequestHandler):
    @chain(jsonio, json_validate(_post_structure))
    def post(self, json):
        logging.debug('post: %s' % json)
        assert 'short_code' not in json, (
            "Posts should be modified with HTTP PUT, not POST"
        )
        
        oid = resale_db.post.save(json)
        
        # TODO: shorter short_code, save short_code in Mongo, ensure short_code
        # isn't 'image' or another interfering string
        short_code = str(oid)
        json['url'] = 'http://localhost:8001/post/%s' % short_code
        json['short_code'] = short_code
        resale_db.post.save(json)
        if '_id' in json: del json['_id']
        return { 'result': 'OK', 'post': json }

class ResalePostViewHandler(tornado.web.RequestHandler):
    def get(self, short_code):
        resale_db.post.ensure_index([('short_code', 1)])
        post = resale_db.post.find_one({'short_code': short_code})
        self.write(str(post))

class ResalePostImageHandler(tornado.web.RequestHandler):
    def post(self):
        imagepath = 'images'
        if not os.path.exists(imagepath): os.makedirs(imagepath)
        oid = ObjectId()
        path = os.path.join(imagepath, '%s.jpg' % oid)
        f = file(path, 'w+')
        # TODO: non-blocking IO?
        f.write(self.request.body)
        logging.info("Saved image to %s" % repr(path))
        rv = simplejson.dumps({
            'result': 'OK',
            'image_url':'http://localhost/images/%s.jpg' % oid
        })
        self.write(rv)
