import urllib.request
import json

from os.path import dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

class NavigationSkill(MycroftSkill):
    def __init__(self):
        super(NavigationSkill, self).__init__(name="NavigationSkill")
        
    def initialize(self):
        #self.load_data_files(dirname(__file__))
        
        where_are_you_intent = IntentBuilder("WhereAreYouIntent").require("WhereAreYouKeyword").build()
        self.register_intent(where_are_you_intent, self.handle_where_are_you_intent)
        where_do_you_want_to_go_intent = IntentBuilder("WhereDoYouWantToGo").require("WheredoYouWantToGo").build()
        self.register_intent(where_do_you_want_to_go, self.handle_where_do_you_want_to_go)
        
        
    def handle_intent(self, message):
        start='https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial'
        endpoint = start
        api_key = 'AIzaSyBp25k9LqhGDh4nAIHeFnhu045jrWPnWkg'
        origins = input('where are you?: ')
        destinations = input('where do you want to go?: ').replace(' ','+')
        
        nav_request = 'endpoint={}&origins={}&destinations={}&key={}'.format(endpoint,origins,destinations,api_key)
        
        request = endpoint + nav_request
        response = urllib.request.urlopen(request).read()
        directions = json.loads(response)
        #print(directions)
        self.speak_dialog("directions")
            
    def stop(self):
        pass

def create_skill():
    return NavigationSkill()
