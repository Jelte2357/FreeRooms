from icalendar import Calendar, Component, Event, vText
from zoneinfo import ZoneInfo
import json
import requests
from datetime import datetime as dt, date as date_type

def get_link(link_url: str) -> Component:
    response = requests.get(link_url)
    if response.ok:
        return Calendar.from_ical(response.content.decode("utf-8"))
    else:
        raise Exception(f"Failed to fetch calendar from {link_url}. Status code: {response.status_code}")
    
def get_room_json_data(json_filename: str = "Rooms.json") -> tuple[set, dict, set, list, dict, dict, ZoneInfo]:
    with open(json_filename, "r") as f:
        data = json.load(f)
    
    if not all(key in data for key in ["all_rooms", "replacements", "remove_list", "timeslots", "links", "link_replacements", "timezone"]):
        raise Exception("JSON data is missing required keys.")
    
    all_rooms = set(data["all_rooms"])
    replacements = data["replacements"]
    all_rooms = set(replacements.get(room, room) for room in all_rooms)
    remove_list = set(data["remove_list"])
    timeslots = data["timeslots"]
    links = data["links"]
    link_replacements = data["link_replacements"]
    timezone = ZoneInfo(data["timezone"])
    
    return all_rooms, replacements, remove_list, timeslots, links, link_replacements, timezone

def to_timezone(naive_dt: dt, timezone: ZoneInfo) -> dt:
    if naive_dt.tzinfo is None:
        naive_dt = naive_dt.replace(tzinfo=ZoneInfo("UTC"))
    
    return naive_dt.astimezone(timezone)

def parse_time(time_str: str):
    return dt.strptime(time_str, "%H:%M").time()

def cal_find_rooms(cal: Component, timezone: ZoneInfo, timeslots: list[dict[str, str]], replacements: dict[str, str]) -> dict[date_type, dict[str, set[str]]]:
    dates = {}

    for component in cal.walk():
        if not isinstance(component, Event):
            continue
        
        date: date_type = component.get("dtstart").dt.date()
        if not date.weekday() < 5:  # Only consider weekdays
            continue
        if date not in dates:
            dates[date] = dict()
        
        start_time = to_timezone(component.get("dtstart").dt, timezone).time()
        end_time = to_timezone(component.get("dtend").dt, timezone).time()

        for time_slot in timeslots:
            slot_start = parse_time(time_slot["start"])
            slot_end = parse_time(time_slot["end"])
            
            # Check if ANY point of the event falls within the timeslot.
            if start_time < slot_end and end_time > slot_start:
                if time_slot["start"] not in dates[date]:
                    dates[date][time_slot["start"]] = set()
                
                if component.get("LOCATION"):
                    loc = str(component["LOCATION"]).replace("Locatie(s): ", "").replace("Locatie: ", "").strip()
                    locs = [replacements.get(loc.strip(), loc.strip()) for loc in loc.split(", ")]
                    dates[date][time_slot["start"]].update(locs)
                    # if date == dt.strptime("2026-04-10", "%Y-%m-%d").date() and time_slot["start"] == "10:45" and "AZ 413" in locs:
                    #     print(f"Event: {component.get('SUMMARY')}, Location(s): {locs}")
    return dates

def sort_rooms(room):
    return room.split()[0], int(room.split()[1]) if len(room.split()) > 1 and room.split()[1].isdigit() else float('inf')

def find_freerooms_from_rooms(dates: dict[date_type, dict[str, set[str]]], all_rooms: set[str], remove_list: set[str]) -> dict[date_type, dict[str, set[str]]]:
    for date, times in dates.items():
        for time_slot, occupied_rooms in times.items():
            free_rooms = all_rooms - occupied_rooms
            free_rooms = free_rooms - remove_list
            dates[date][time_slot] = set(sorted(free_rooms, key=sort_rooms))
    return dates

def freerooms_operator(room_dicts: dict[str, dict[date_type, dict[str, set[str]]]]) -> dict[date_type, dict[str, dict[str, set[str]]]]:
    """For each date and timeslot, find what is uniquely free per calendar and what the overlap is."""
    """Output should be like:
    {
        date (dt: 10-04-2026): {
            timeslot (10:45): {
                "calendar1_name": set of rooms free in calendar 1 but not in ANY other calendar,
                "calendar2_name": set of rooms free in calendar 2 but not in ANY other calendar,
                ...
                "overlap": set of rooms free in ALL calendars
            },
    }
    """
    
    output = {}
    for cal_name, dates in room_dicts.items():
        for date, times in dates.items():
            if date not in output:
                output[date] = {}
            for time_slot, free_rooms in times.items():
                if time_slot not in output[date]:
                    output[date][time_slot] = {}
                    
                if "overlap" not in output[date][time_slot]:
                    output[date][time_slot]["overlap"] = set(free_rooms)
                else:
                    output[date][time_slot]["overlap"] &= free_rooms
                
                output[date][time_slot][cal_name] = set(free_rooms)
                for other_cal_name, other_dates in room_dicts.items():
                    if other_cal_name == cal_name:
                        continue
                    other_free_rooms = other_dates.get(date, {}).get(time_slot, set())
                    output[date][time_slot][cal_name] -= other_free_rooms
    return output

def sort_freerooms(free_rooms_dict: dict[date_type, dict[str, dict[str, set[str]]]]) -> dict[date_type, dict[str, dict[str, list[str]]]]:
    sorted_dict = {}
    for date, times in free_rooms_dict.items():
        sorted_dict[date] = {}
        for time_slot, cal_data in times.items():
            sorted_dict[date][time_slot] = {}
            for cal_name, rooms in cal_data.items():
                sorted_dict[date][time_slot][cal_name] = sorted(rooms, key=sort_rooms)
    return sorted_dict