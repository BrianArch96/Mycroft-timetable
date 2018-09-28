# TODO: Add an appropriate license to your skill before publishing.  See
# the LICENSE file for more information.

# Below is the list of outside modules you'll be using in your skill.
# They might be built-in to Python, from mycroft-core or from external
# libraries.  If you use an external library, be sure to include it
# in the requirements.txt file so the library is installed properly
# when the skill gets installed later by a user.

import re
import calendar
import datetime

from .Webscraping import webscrape
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import getLogger

logger = getLogger(__name__)

LECTURE_TIME_LIMIT = 540
last_position = 7
INITIAL_LESSON = 0

# Each skill is contained within its own class, which inherits base methods
# from the MycroftSkill class.  You extend this class as shown below.

class TimetableSkill(MycroftSkill):

    # The constructor of the skill, which calls MycroftSkill's constructor
    def __init__(self):
        logger.info('init is working')
        super(TimetableSkill, self).__init__(name="TimetableSkill")
        self.timetable = self._lookup(self.settings.get("student_id"))

    @intent_handler(IntentBuilder("").require("Module_details").require("module_id"))
    def handle_module_details(self, message):
        module_id = message.data.get("module_id")
        self._handle_module_detail_request(module_id)

    @intent_handler(IntentBuilder("").require("Next_lesson"))
    def handle_next_lesson(self, message):
        self._handle_next_lesson()

    @intent_handler(IntentBuilder("").require("First_lesson").require("day"))
    def handle_first_lesson_req(self, message):
        day = message.data.get("day")
        self._handle_first_les(day)

    @intent_handler(IntentBuilder("").require("Next_lesson_location"))
    def handle_next_lesson_location(self, message):
        print("hello")
        self._handle_next_lesson_location()

    @intent_handler(IntentBuilder("").require("Position").require("pos")
    .require("Class").require("day"))
    def handle_query_class(self, message):
        pos = message.data.get("pos")
        day = message.data.get("day")
        self._handle_query(pos, day)

    @intent_handler(IntentBuilder("").require("Request").require("id"))
    def handle_intent(self, message):
        id = message.data.get("id")
        self.speak_dialog("searching", {"query":id})
        tt =  self._lookup(id)
        if not tt:
            self.speak_dialog("invalid_id")
        else:
            self.settings["student_id"] = id
            self.speak_dialog("successful_change")
            self.timetable =  tt
    
    def _handle_module_detail_request(self, module_id):
        module_details = webscrape.get_module_details(module_id)
        if not module_details:
            self.speak_dialog("no entry found")
            return
        self.speak_dialog("module_details_ans", {"id": module_id, "name": module_details.name,"lecturer": module_details.lecturer})


    def _lookup(self, student_id):
        try:
            timetable = webscrape.simple_get(student_id)
            if not timetable:
                self.speak_dialog("no entry found")
                return
        except:
            self.speak_dialog("no entry found")
        return timetable

    def assertDay(self, chosen_day):
        days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
        for day in days_of_week:
            if chosen_day == day:
                return days_of_week.index(day)
        self.speak_dialog("invalid_argument")
        return None
                    
    def assertPosition(self, chosen_pos):
        valid_position = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "last"]
        for position in valid_position:
            if chosen_pos == position:
                return valid_position.index(position)
        self.speak_dialog("invalid_argument")
        return None

    def _handle_query(self, position, day):
        week_index = self.assertDay(day)
        # NEED TO FIGURE OUT RETURNS FOR INVALID DAYS AND POSITIONS.
        # IF I RETURN INDEX 0 AND THEN CHECK FOR 0, IT WILL SEE IT AS AN ERROR AND RETURN. NEED FIX
        lecture_index = self.assertPosition(position)

        day = self.timetable.days[week_index]

        if not day:
            self.speak_dialog("no_lecture")
            return None

        if lecture_index == last_position:
            lecture_index = len(day)-1 

        if len(day) < (lecture_index+1):
            self.speak_dialog("no_lecture")
            return None

        self.speak_dialog("lecture_info", {"module": day[lecture_index].module,
            "s_time": day[lecture_index].startTime, "location": day[lecture_index].location})

    def _handle_first_les(self, req_day):
        week_index = self.assertDay(req_day)
        day = self.timetable.days[week_index]
        
        self.speak_dialog("first_lec_ans", {"day": req_day, "time": day[INITIAL_LESSON].startTime})

    def _get_current_time(self):
        now = datetime.datetime.now()
        cur_time = str(now)
        cur = cur_time.split(":")
        cur_time = cur[0] + ":" +  cur[1]
        cur_time = cur_time.split(" ")
        cur_time = cur_time[1]
        current_time = datetime.datetime.strptime(cur_time, "%H:%M")
        current_time = current_time.strftime("%H:%M")
        return current_time

    def _get_next_lesson(self):
        current_day = datetime.date.today()
        current_weekday = calendar.day_name[current_day.weekday()].lower()

        week_index = self.assertDay(current_weekday)

        day = self.timetable.days[week_index]
        current_time = self._get_current_time()
        next_lesson = None
        time_dif = None
        for lesson in day:
            time_dif = self._subtract_times(lesson.startTime, current_time)
            if time_dif:
                next_lesson = lesson
                break
        return next_lesson

    def _handle_next_lesson_location(self):
        next_lesson = self._get_next_lesson()

        if not next_lesson:
            self.speak_dialog("no_more_lessons")
            return
        
        self.speak_dialog("next_lesson_location", {"location": next_lesson.location})

    def _handle_next_lesson(self):
        next_lesson = self._get_next_lesson()

        if not next_lesson:
            self.speak_dialog("no_more_lessons")
            return
        next_lesson.startTime = datetime.datetime.strptime(next_lesson.startTime, "%H:%M")
        next_lesson.startTime = datetime.datetime.strftime(next_lesson.startTime, "%I:%M %p")
        self.speak_dialog("next_lesson", {"module": next_lesson.module, "startTime": next_lesson.startTime})
                
    def _subtract_times(self, time1, time2):
        timeA = datetime.datetime.strptime(time1, "%H:%M")
        timeB = datetime.datetime.strptime(time2, "%H:%M")
        newTime = timeA - timeB
       
       #THIS CHECK HAS TO BE DONE OR ELSE THE TIME WILL LAPSE AROUND TO THE NEXT DAY
       #Does not return negatives

        if (newTime.seconds/60 > LECTURE_TIME_LIMIT):
            return None

        return newTime.seconds/60

# The "create_skill()" method is used to create an instance of the skill.
# Note that it's outside the class itself.
def create_skill():
    return TimetableSkill()
