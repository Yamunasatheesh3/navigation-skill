import urllib.request
import json
import requests
from googleapiclient import googlemaps
from os.path import dirname, join
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

LOGGER = getLogger(__name__)
api_key = 'AIzaSyBp25k9LqhGDh4nAIHeFnhu045jrWPnWkg'

class GoogleMapsClient(object):
     def __init__(self, api_key=None):     
        self.gmaps = googlemaps.Client(key=api_key)
        LOGGER.debug("Connected to Google API: %s" % self.gmaps)

     def duration(self, **duration_arg):
        LOGGER.debug('Google API - Duration')
        response = self.gmaps.directions(**duration_arg)[0]
        LOGGER.debug("API Response: %s" % json.dumps(response))
        legs = response['legs'][0]
        duration_norm = int(legs['duration']['value']/60)
        if legs['duration_in_trasit']:
            duration_transit = int(legs['duration_in_transit']['value']/60)
        else:
            duration_transit = duration_norm
        transit_time = duration_transit - duration_norm
        route_summ = routes['summary']
        return duration_norm, duration_transit, transit_time, route_summ
    
    def distance(self, **dist_arg):
        LOGGER.debug('Google API - Distance Matrix')
        response = self.gmaps.distance_matrix(**dist_arg)
        LOGGER.debug("API Response: %s" % json.dumps(response))
        rows = response['rows']
        element = rows[0]['elements'][0]
        duration_norm = int(element['duration']['value']/60)
        if 'duration_in_transit' in element.keys():
            duration_transit = int(element['duration_in_transit']['value']/60)
        else:
            duration_transit = duration_norm
        transit_time = duration_transit - duration_norm
        return duration_norm, duration_transit, transit_time
    
class NavigationSkill(MycroftSkill):
    def __init__(self):
        super(NavigationSkill, self).__init__(name="NavigationSkill")
        provider = self.settings.get('provider', 'google')
        LOGGER.debug("Configured Provider: %s" % provider)
        if provider == 'google':
            api_key = self.settings.get('api_key', None)
            self.maps = GoogleMapsClient(api_key)
            LOGGER.debug("Connected to Google API: %s" % self.maps)
        
        
    def initialize(self):
        self.load_data_files(dirname(__file__))
        self.load_vocab_files(join(dirname(__file__), 'vocab', self.lang))
        self.load_regex_files(join(dirname(__file__), 'regex', self.lang))
        self.__build_transit_now_intent()
        self.__build_transit_later_intent()
        self.__build_proximity_intent()
        
    def __build_transit_now_intent(self):
        intent = IntentBuilder("TransitNowIntent").require("TransitKeyword")\
            .require("Destination").optionally("Origin").build()
        self.register_intent(intent, self.handle_transit_now_intent)

    def __build_transit_later_intent(self):
        intent = IntentBuilder("TransitLaterIntent").require("TransitKeyword")\
            .require("Destination").optionally("Origin").build()
        self.register_intent(intent, self.handle_transit_later_intent)

    def __build_proximity_intent(self):
        intent = IntentBuilder("ProximityIntent").require("ProximityKeyword")\
            .require("Destination").optionally("Origin").build()
        self.register_intent(intent, self.handle_proximity_intent)
        
    def handle_transit_now_intent(self, message):
        try:
            LOGGER.debug("Config Data: %s" % self.config)
            depart_time_now = str(int(time()))
            self.request_drive_time(message, depart_time_now)
        except Exception as err:
            LOGGER.error("Error: {0}".format(err))

    def handle_transit_later_intent(self, message):
        try:
            depart_time_now = str(int(time()))
            self.request_drive_time(message, depart_time_now)
        except Exception as err:
            LOGGER.error("Error: {0}".format(err))

    def handle_proximity_intent(self, message):
        try:
            depart_time_now = str(int(time()))
            self.request_distance(message)
        except Exception as err:
            LOGGER.error("Error: {0}".format(err))
            
    def build_route(self, message):
        spoken_dest = self.get_response("FromLocation")
        spkn_origin = self.get_response("ToLocation")
        if spkn_origin is None:
            self.log.debug("No origin")
        if spoken_dest is None:
            self.log.debug("No destination")
        LOGGER.debug("Loading origin from profile...")
        try:
            origin_addr = message.data.get('spkn_origin', None)
        except KeyError:
            LOGGER.error("Falling back to home as origin.")
        LOGGER.debug("Origin Address: %s" % origin_addr)
        LOGGER.debug("Loading destination from profile...")
        try:
            dest_addr = message.data.get('spoken_dest', None)
        except KeyError:
            LOGGER.error("Destination not registered. Looking up Destination")
        LOGGER.debug("Destination Address: %s" % dest_addr)
        try:
            spoken_depart_time = message.data.get("Depart")
        except KeyError:
            spoken_depart_time = 'now'
        route_dict = {
            'origin': origin_addr,
            'destination': dest_addr,
            }
        LOGGER.debug("Route:: %s" % build_route_dict)
        return build_route_dict
    
    def request_drive_time(self, message, depart_time):
        route = self.build_route(message)
        self.speak_dialog("welcome")
        duration_arg = {
            'origin': route['origin'],
            'destination': route['destination'],
            'mode': 'driving',
            'units': self.dist_units
            }
        drive_details = self.maps.duration(**duration_arg)
        duration_norm = drive_details[0]
        duration_transit = drive_details[1]
        transit_time = drive_details[2]
        route_summ = drive_details[3]
        if transit_time >= 20:
            LOGGER.debug("Duration = Heavy")
            self.speak_dialog('duration.heavy',
                              data={'trip_time': duration_norm,
                                    'transit_time': transit_time})
        elif transit_time >= 5:
            LOGGER.debug("Duration = Delay")
            self.speak_dialog('duration.delay',
                              data={'trip_time': duration_norm,
                                    'transit_time': transit_time})
        else:
            LOGGER.debug("Duration = Clear")
            self.speak_dialog('duration.clear',
                              data={'trip_time': duration_norm})
        
   def request_drive_time_orig(self, message, depart_time, api_key):
        route = self.build_route(message)
        self.speak_dialog("welcome")
        orig_enc = self.__convert_address(route['origin'])
        dest_enc = self.__convert_address(route['destination'])
        api_root = 'https://maps.googleapis.com/maps/api/directions/json'
        api_params = '?origin=' + orig_enc +\
                     '&destination=' + dest_enc +\
                     '&departure_time=' + depart_time +\
                     '&traffic_model=best_guess' +\
                     '&waypoint=True' +\ 
                     '&key=' + api_key
        api_url = api_root + api_params
        LOGGER.debug("API Request: %s" % api_url)
        response = requests.get(api_url)

        if response.status_code == requests.codes.ok and \
                response.json()['status'] == "REQUEST_DENIED":
            LOGGER.error(response.json())
            self.speak_dialog('duration.error.api')

        elif response.status_code == requests.codes.ok:
            LOGGER.debug("API Response: %s" % response)
            routes = response.json()['routes'][0]
            legs = routes['legs'][0]
            midpoint = response.routes[0](legs['waypoint']/2)
            duration_norm = int(legs['duration']['value']/60)
            duration_transit = int(legs['duration_in_transit']['value']/60)
            transit_time = duration_transit - duration_norm
            if transit_time >= 20:
                LOGGER.debug("Duration = Heavy")
                self.speak_dialog('duration.heavy',
                                  data={'trip_time': duration_norm,
                                        'traffic_time': traffic_time})
            elif traffic_time >= 5:
                LOGGER.debug("Duration = Delay")
                self.speak_dialog('duration.delay',
                                  data={'trip_time': duration_norm,
                                        'traffic_time': traffic_time})
            else:
                LOGGER.debug("Duration = Clear")
                self.speak_dialog('duration.clear',
                                  data={'trip_time': duration_norm})

        else:
            LOGGER.error(response.json())   
               
    def request_distance(self, message):
        route = self.build_route(message)
        self.speak_dialog("welcome")
        dist_arg = {
            'origins': route['origin'],
            'destinations': route['destination'],
            'mode': 'driving',
            'units': self.dist_units
            }
        drive_details = self.maps.distance(**dist_arg)
        duration_norm = drive_details[0]
        duration_transit = drive_details[1]
        transit_time = drive_details[2]
        if transit_time >= 20:
            LOGGER.debug("Duration = Heavy")
            self.speak_dialog('distance.heavy',
                              data={'destination': route['dest_name'],
                                    'trip_time': duration_norm,
                                    'transit_time': transit_time,
                                    'origin': route['origin'],
                                    'midpoint': route['midpoint']})
        elif transit_time >= 5:
            LOGGER.debug("Duration = Delay")
            self.speak_dialog('distance.delay',
                              data={'destination': route['dest_name'],
                                    'trip_time': duration_norm,
                                    'transit_time': transit_time,
                                    'origin': route['origin'],
                                    'midpoint': route['midpoint']})
        else:
            LOGGER.debug("Duration = Clear")
            self.speak_dialog('distance.clear',
                              data={'destination': route['dest_name'],
                                    'trip_time': duration_norm,
                                    'origin': route['origin'],
                                    'midpoint': route['midpoint']})
                
    def __convert_address(self, address):
        address_converted = sub(' ', '+', address)
        return address_converted
    
    def stop(self):
        pass

def create_skill():
    return NavigationSkill()
