# python
import logging

# libraries
import tornado.web
import twilio

# local
from db import resale_db
import resale_settings

class ResaleTwilioRequestHandler(tornado.web.RequestHandler):
    def post(self):
        """
        Receive a Twilio request, return a TwiML response
        """
        from_phone_number = self.get_argument('From')
        to_phone_number = self.get_argument('To')
        call_status = self.get_argument('CallStatus')
        logging.info('Receiving call from %s to %s, status %s' % (
            repr(from_phone_number), repr(to_phone_number), repr(call_status)
        ))
        
        if call_status == 'ringing':
            response = twilio.Response()
            # Current-time number for testing call redirection
            response.append(twilio.Dial("2027621401", timeLimit=45))
            logging.info('Responding:\n%s\n', response)
            self.write(str(response))
