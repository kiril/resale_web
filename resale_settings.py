import os

static_path = os.path.join(os.path.dirname(__file__), "static")

twilio_account_sid = 'AC77d6ed97261551ab0be0a70f0d942eb2'
twilio_auth_token = 'eab1aac8ede80a3480029445b193793e'

max_call_duration = 60 * 5 # 5 minutes, in seconds
phone_map_lifetime = 60 * 10 # 10 minutes, in seconds
