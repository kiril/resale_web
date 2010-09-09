# python
import logging
import md5
import datetime
import math
import re

# libraries
import tornado.web
import twilio
from pymongo.dbref import DBRef

# local
from db import resale_db, post_with_short_code_or_404
from resaledecorators import chain, jsonio
from json_validate import *
import resale_settings
import resale_time

class ResaleTwilioRequestHandler(tornado.web.RequestHandler):
    def strip_incoming_number(self, phone_number, non_decimal = re.compile(r'[^\d.]+')):
        """
        Twilio tells us about phone numbers formatted like
        "+17187539654" -- strip it to match what the user
        originally sent us
        """
        # strip +, then strip 1, then remove all non-numeric
        return non_decimal.sub('', phone_number.lstrip('+').lstrip('1'))
    
    def post(self):
        """
        Receive a Twilio request, return a TwiML response
        """
        from_phone_number = self.strip_incoming_number(
            self.get_argument('From')
        )
        
        to_phone_number = self.strip_incoming_number(
            self.get_argument('To')
        )
        
        buyer_phone_number_hash = md5.new(from_phone_number).hexdigest()
        call_status = self.get_argument('CallStatus')
        logging.info('Receiving call from %s to %s, hash %s, status %s' % (
            repr(from_phone_number), repr(to_phone_number), repr(buyer_phone_number_hash), repr(call_status)
        ))
        
        if call_status == 'ringing':
            resale_db.phone_map.ensure_index([('buyer_phone_number_hash', 1)])
            # TODO: also add some logging info to phone_map, see if we can do it in
            # one round trip to DB
            twilio_phone_number = resale_db.twilio_phone_number.find_one({
                'phone_number': to_phone_number,
            })
            
            phone_map = resale_db.phone_map.find_one({
                'buyer_phone_number_hash': buyer_phone_number_hash,
                'twilio_phone_number.$id': twilio_phone_number['_id'],
                'expires': { '$gt': resale_time.utcnow() },
            }, {
                'post': True,
            })
            
            post = resale_db.dereference(phone_map['post'])
            
            # TODO: if no phone_map, speak error message to user, or latest phone_map
            # is expired
            
            response = twilio.Response()
            # Current-time phone number for testing call redirection
            #response.append(twilio.Dial("2027621401", timeLimit=45))
            response.append(twilio.Dial(post['phone_number']))
            logging.info('Responding:\n%s\n', response)
            self.write(str(response))

class ResaleGetSellerPhoneNumberHandler(tornado.web.RequestHandler):
    # TODO: hash buyer phone number in Javascript before submitting
    @chain(jsonio, json_validate({'short_code': str, 'buyer_phone_number_hash': str}))
    def post(self, json):
        """
        Setup a Twilio phone number to receive calls from the buyer (who
        initiates this request) to the seller of this post.
        
        Returns: {'result': 'OK', 'seller_phone_number': '1234567890'}
        or: {'result': 'OK', 'wait_seconds': 30} if no number is available now
        """
        resale_db.twilio_phone_number.ensure_index([('create_date', 1)])
        resale_db.phone_map.ensure_index([('buyer_phone_number_hash', 1), ('expires', 1)])
        
        # Get the buyer's active phone_maps, which associate the buyer's phone
        # number with a Twilio phone number and a seller's phone number
        # TODO: deny this whole flow if seller didn't enter phone number -
        # prevent user from even clicking 'Call' in Javascript
        utcnow = resale_time.utcnow()
        buyer_phone_maps = list(resale_db.phone_map.find({
            'buyer_phone_number_hash': json['buyer_phone_number_hash'],
            'expires': { '$gt': utcnow },
        }, {
            'twilio_phone_number.$id': True,
            'expires': True,
        }).sort('expires', 1))
        
        logging.info('buyer_phone_maps: %s' % repr(list(buyer_phone_maps)))
        
        # Get oldest twilio phone number not in an active phone_map for this buyer
        active_twilio_phone_numbers = [phone_map['twilio_phone_number']['$id'] for phone_map in buyer_phone_maps]
        logging.info('active_twilio_phone_numbers: %s' % repr(active_twilio_phone_numbers))
        twilio_phone_numbers = list(resale_db.twilio_phone_number.find({
            '_id': { '$nin': [phone_map['twilio_phone_number']['$id'] for phone_map in buyer_phone_maps] },
        }).sort('create_date', 1).limit(1))
        
        logging.info('twilio_phone_numbers: %s' % repr(list(twilio_phone_numbers)))
        
        if len(twilio_phone_numbers):
            twilio_phone_number = twilio_phone_numbers[0]
            post = post_with_short_code_or_404(json['short_code'])
            resale_db.phone_map.insert({
                'post': DBRef('post', post['_id']),
                'buyer_phone_number_hash': json['buyer_phone_number_hash'],
                'twilio_phone_number': DBRef('twilio_phone_number', twilio_phone_number['_id']),
                'expires': utcnow + datetime.timedelta(seconds=resale_settings.phone_map_lifetime),
            })
            return {'result': 'OK', 'seller_phone_number': twilio_phone_number['phone_number']}
        else:
            # How long will user have to wait before a Twilio phone number becomes available?
            logging.info('first phone map expires: %s, now is: %s' % (
                buyer_phone_maps[0]['expires'].ctime(),
                utcnow.ctime()
            ))
            
            # Round up to nearest 10 seconds, plus 2 seconds fudge, for simplicity
            rounding_seconds = 10
            wait_seconds = int(math.ceil(
                ((resale_time.utc_cast(buyer_phone_maps[0]['expires']) - utcnow).total_seconds() + 2) / rounding_seconds
            ) * rounding_seconds)
            
            assert wait_seconds > 0, (
                "Buyer with phone number hash %s has negative wait_seconds %d" % (
                    repr(json['buyer_phone_number_hash']), wait_seconds
                )
            )
            
            return { 'result': 'OK', 'wait_seconds': wait_seconds }
