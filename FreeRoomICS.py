import Free2Room
from datetime import datetime as dt, date as date_type
from rich.pretty import pprint

def cal_find_freerooms(json_filename: str, use_replacements: bool = False):
    all_rooms, replacements, remove_list, timeslots, links, link_replacements, timezone = Free2Room.get_room_json_data(json_filename)
    if use_replacements:
        links = link_replacements
    
    all_calendars = {
        link_name: Free2Room.get_link(link_url)
        for link_name, link_url in links.items()
    }
    
    all_dates: dict[str, dict[date_type, dict[str, set]]] = {
        link_name: Free2Room.cal_find_rooms(cal, timezone, timeslots, replacements)
        for link_name, cal in all_calendars.items()
    }
            
    all_free_rooms: dict[str, dict[date_type, dict[str, set]]] = {
        link_name: Free2Room.find_freerooms_from_rooms(dates, all_rooms, remove_list)
        for link_name, dates in all_dates.items()
    }
    
    free_rooms_dict = Free2Room.freerooms_operator(all_free_rooms)
    free_rooms_dict = Free2Room.sort_freerooms(free_rooms_dict)
    
    return free_rooms_dict

date = dt.now().date()
time = "14:45"

ret = cal_find_freerooms("Rooms.json", use_replacements=False)
pprint(ret[date][time], expand_all=True)