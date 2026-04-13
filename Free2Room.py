from icalendar import Calendar, Component, Event, vText
from zoneinfo import ZoneInfo
import json
import requests
from datetime import datetime as dt

with open("LINK.txt", "r") as f:
    students, rooms = f.read().rstrip("\n").split("\n\n")
    
# students, rooms = "http://127.0.0.1:8000/TimeEdit.ics", "http://127.0.0.1:8000/TimeEdit2.ics"

request_students = requests.get(students)
cal_students = Calendar.from_ical(request_students.content.decode("utf-8"))

request_rooms = requests.get(rooms)
cal_rooms = Calendar.from_ical(request_rooms.content.decode("utf-8"))

with open("Rooms.json", "r") as f:
    rooms = json.load(f)
    
all_rooms = set(rooms["all_rooms"])
replacements = rooms["replacements"]
all_rooms = set(replacements.get(room, room) for room in all_rooms)
remove_list = set(rooms["remove_list"])
timeslots = rooms["timeslots"]

AMS = ZoneInfo("Europe/Amsterdam")

def to_amsterdam_time(naive_dt: dt) -> dt:
    if naive_dt.tzinfo is None:
        naive_dt = naive_dt.replace(tzinfo=ZoneInfo("UTC"))
    
    return naive_dt.astimezone(AMS)

def parse_time(time_str: str):
    return dt.strptime(time_str, "%H:%M").time()

def cal_find_rooms(cal: Component):
    dates = {}

    for component in cal.walk():
        if isinstance(component, Event):
            date: dt = component.get("dtstart").dt.date()
            if date.weekday() < 5:  # Only consider weekdays
                if date not in dates:
                    dates[date] = dict()
                
                start_time = to_amsterdam_time(component.get("dtstart").dt).time()
                end_time = to_amsterdam_time(component.get("dtend").dt).time()

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

def find_freerooms_from_rooms(dates):
    for date, times in dates.items():
        for time_slot, occupied_rooms in times.items():
            # if date == dt.strptime("2026-04-10", "%Y-%m-%d").date() and time_slot == "10:45":
            #     print(f"Occupied rooms before replacements and removals: {occupied_rooms}")
            # date_str = dt.strftime(date, "%Y-%m-%d")
            free_rooms = all_rooms - occupied_rooms
            free_rooms = free_rooms - remove_list
            dates[date][time_slot] = sorted(free_rooms, key=sort_rooms)
    return dates

dates_students = cal_find_rooms(cal_students)
dates_rooms    = cal_find_rooms(cal_rooms)

freerooms_students = find_freerooms_from_rooms(dates_students)
freerooms_rooms    = find_freerooms_from_rooms(dates_rooms)

def freerooms_operator(freerooms_students, freerooms_rooms):
    """For each date and timeslot, find what is uniquely free in students, uniquely free in rooms, and what the overlap is."""
    output = {}
    
    for date in set(freerooms_students.keys()) | set(freerooms_rooms.keys()):
        for time_slot in set(freerooms_students.get(date, {}).keys()) | set(freerooms_rooms.get(date, {}).keys()):
            free_students_set = set(freerooms_students.get(date, {}).get(time_slot, []))
            free_rooms_set = set(freerooms_rooms.get(date, {}).get(time_slot, []))
            
            unique_free_students = free_students_set - free_rooms_set
            unique_free_rooms = free_rooms_set - free_students_set
            overlap_free = free_students_set & free_rooms_set
            
            output.setdefault(date, {})[time_slot] = {
                "unique_free_students": sorted(unique_free_students, key=sort_rooms),
                "unique_free_rooms": sorted(unique_free_rooms, key=sort_rooms),
                "overlap_free": sorted(overlap_free, key=sort_rooms),
            }
            
    return output

dates = freerooms_operator(freerooms_students, freerooms_rooms)


from rich.pretty import pprint
date_str, time_str = "2026-04-13", "12:45"
pprint(dates[dt.strptime(date_str, "%Y-%m-%d").date()][time_str], expand_all=True)

# from functools import reduce
# from operator import and_, or_


# pprint(list(sorted(list(reduce(or_, list(map(set, dates[dt.strptime("2026-04-10", "%Y-%m-%d").date()].values())))))), expand_all=True)