import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.autoreload

import logging
logging.basicConfig(filename='/var/log/apache2/resale.log', level=logging.DEBUG)

from resalepost import ResalePostHandler, ResalePostViewHandler
from resalepost import ResalePostImageHandler

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        # TODO: promotional home page
        self.write("Hello, world")

class AuthHandler(tornado.web.RequestHandler):
    # TODO: authentication
    pass

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/auth", AuthHandler),
    (r"/post", ResalePostHandler),
    # TODO: app should send image straight to S3 or some CDN, not to API
    (r"/post/image", ResalePostImageHandler),
    (r"/post/(\S+)", ResalePostViewHandler),
])

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8001)
    print 'listening on port 8001'
    logging.info('logger up')
    # TODO: don't autoreload in production
#    tornado.autoreload.start() 
    tornado.ioloop.IOLoop.instance().start()
