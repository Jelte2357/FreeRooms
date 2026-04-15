import Free2Room
from datetime import datetime as dt, date as date_type
from icalendar import Component, Calendar, Event
from zoneinfo import ZoneInfo
from rich.pretty import pprint

# FreeRooms Type: dict[      date_type       , dict[str, dict[ str , list[ str ]]]]
# Example:            {datetime.date(15, 4, 2026): {"10:45": {"overlap": ["AZ 413", "AZ 414"], "Calendar1": ["AZ 413"]"}}}

def bold_capital(text: str) -> str:
    return f"<b>{text.capitalize()}</b>"

def cal_find_freerooms(json_filename: str, use_replacements: bool = False) -> tuple[dict[date_type, dict[str, dict[str, list[str]]]], list[dict[str, str]]]:
    all_rooms, replacements, remove_list, timeslots, links, link_replacements, timezone = Free2Room.get_room_json_data(json_filename)
    if use_replacements:
        links = link_replacements
    
    all_calendars: dict[str, Component] = {
        link_name: Free2Room.get_link(link_url)
        for link_name, link_url in links.items()
    }
    
    all_dates: dict[str, dict[date_type, dict[str, set[str]]]] = {
        link_name: Free2Room.cal_find_rooms(cal, timezone, timeslots, replacements)
        for link_name, cal in all_calendars.items()
    }
            
    all_free_rooms: dict[str, dict[date_type, dict[str, set[str]]]] = {
        link_name: Free2Room.find_freerooms_from_rooms(dates, all_rooms, remove_list)
        for link_name, dates in all_dates.items()
    }
    
    free_rooms_dict = Free2Room.freerooms_operator(all_free_rooms)
    free_rooms_dict = Free2Room.sort_freerooms(free_rooms_dict)
    
    return free_rooms_dict, timeslots

def freerooms_to_ics(free_rooms_dict: dict[date_type, dict[str, dict[str, list[str]]]], timeslots: list[dict[str, str]]) -> Calendar:
    cal = Calendar()
    cal.add('prodid', '-//Free Rooms//Free Rooms Calendar//EN')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'Free Rooms')
    cal.add('x-wr-caldesc', 'Available rooms schedule')
    
    for date, times in free_rooms_dict.items():
        for timeslot in timeslots:
            event = Event()
            event.add('summary', f"Free Rooms at {timeslot['start']}")
            event.add('dtstart', dt.combine(date, dt.strptime(timeslot['start'], "%H:%M").time()))
            event.add('dtend', dt.combine(date, dt.strptime(timeslot['end'], "%H:%M").time()))
            
            free_rooms = times.get(timeslot['start'], {})
            description = ""

            if free_rooms:
                if "overlap" in free_rooms:
                    description += f"{bold_capital('overlap')}:\n" + "\n".join(free_rooms["overlap"]) + "\n\n"
                
                for calendar_name, rooms in free_rooms.items():
                    if calendar_name != "overlap" and rooms:
                        description += f"{bold_capital(calendar_name)}:\n" + "\n".join(rooms) + "\n\n"
            
            event.add('description', description.strip())
            
            cal.add_component(event)
    
    return cal

if __name__ == "__main__":
    date = dt.now().date()
    time = "12:45"

    ret = cal_find_freerooms("Rooms.json", use_replacements=False)
    cal = freerooms_to_ics(*ret)
    # with open("FreeRooms.ics", "wb") as f:
    #     f.write(cal.to_ical())
    # pprint(ret[0][date][time], expand_all=True)