# python
import logging
import re
import os
import urlparse

# libraries
import simplejson
import tornado.web
from pymongo.objectid import ObjectId

# local
from resaledecorators import chain, jsonio
from json_validate import *
from db import resale_db, post_with_short_code_or_404
import resale_settings

# TODO: better image_url pattern
image_url_pat = re.compile(r'http://\S+\.(jpe?g|png)')
price_pat = re.compile(r'\d*(\.\d{0,2})?')

_post_structure = {
    'title': str,
    'price': price_pat,
    'image_url': image_url_pat,
    'posted_to_twitter': bool,
    'posted_to_facebook': bool,
    'location':{ 'lat': float, 'long': float },
    'short_code': optional(str),
    'phone_number': optional(str),
    'email_address': optional(str),
}

# Sample post for testing
#{"price": "17", "image_url": "http://foo.com/foo.png", "location": {"lat": 421.0, "long": 11.9}, "title": "from_console"}

class ResalePostHandler(tornado.web.RequestHandler):
    @chain(jsonio, json_validate(_post_structure))
    def post(self, json):
        logging.debug('post: %s' % json)
        assert 'short_code' not in json, (
            "Posts should be modified with HTTP PUT, not POST"
        )
        
        # short_code is just one row with the current largest serial number
        short_code = str(int(resale_db.eval("""
            db.runCommand({
                findAndModify: 'short_code',
                upsert: true,
                update: { $inc: { short_code: 1 } },
                query: { short_code : { $gt :  -1 } },
                new: true
            })
        """)['value']['short_code']))
        
        logging.debug('short_code: %s' % short_code)
        json['short_code'] = short_code
        resale_db.post.ensure_index('short_code', unique=True)
        
        json['url'] = urlparse.urljoin(
            'http://%s' % resale_settings.hostname,
            self.reverse_url('view_post', short_code)
        )
        
        # TODO: client can insert whatever it wants in JSON and we'll insert it
        # into DB. Wouldn't it be cool if json_validate also had function to
        # make a JSON obj that *only* has required or optional elements?
        resale_db.post.save(json)
        if '_id' in json: del json['_id']
        return { 'result': 'OK', 'post': json }

# TODO: app should send image straight to S3 or some CDN, not to API
class ResalePostImageHandler(tornado.web.RequestHandler):
    def post(self):
        imagepath = 'static'
        if not os.path.exists(imagepath): os.makedirs(imagepath)
        oid = ObjectId()
        # TODO: in (near-impossible) case of collision, append another OID to path
        path = os.path.join(imagepath, '%s.jpg' % oid)
        f = file(path, 'w+')
        # TODO: non-blocking IO?
        f.write(self.request.body)
        logging.info("Saved image to %s" % repr(path))
        rv = simplejson.dumps({
            'result': 'OK',
            'image_url':'http://%s/static/%s.jpg' % (resale_settings.hostname, oid),
        })
        self.write(rv)

class ResalePostSearchHandler(tornado.web.RequestHandler):
    @chain(jsonio)
    def get(self, json):
        """
        Search posts using CGI arguments, e.g.:
        http://resaleapp.com/api/post/search?lat=37&long=-122&query=couch
        """
        # Ensure Mongo uses a geospatial index on location, then search for
        # nearby posts with titles containing the query string.  PyMongo doesn't
        # support '2d' indexes, so use Javascript to ensure the index.
        resale_db.eval('db.post.ensureIndex( { location : "2d", title: 1 } )')
        find_terms = { 'location': { '$near':
            [ float(self.get_argument('lat')), float(self.get_argument('long')) ]
        } }
        
        # Matching on title is optional
        if self.get_argument('query', None):
            find_terms['title'] = re.compile(
                r'.*%s.*' % re.escape(
                    self.get_argument('query'),
                ), re.I
            )
        
        # TODO: Has Mongo already sorted results by proximity to lat and long?
        search_results = resale_db.post.find(find_terms).limit(20)
        return { 'result': 'OK', 'posts': list(search_results) }

class ResaleTemplateContext(dict):
    """
    Like a dictionary, but ignores non-string keys
    """
    def __init__(self, a_dict):
        for k, v in a_dict.items():
            if isinstance(k, (str, unicode)):
                self[str(k)] = v

class ResalePostViewHandler(tornado.web.RequestHandler):
    def get(self, short_code):
        post = post_with_short_code_or_404(short_code)
        self.render("templates/PostView.html", **ResaleTemplateContext(post))
