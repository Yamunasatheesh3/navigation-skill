from mycroft import MycroftSkill, intent_file_handler


class Navigation(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('navigation.intent')
    def handle_navigation(self, message):
        self.speak_dialog('navigation')


def create_skill():
    return Navigation()

