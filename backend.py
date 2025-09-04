import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict


def parseTime(time_str: str) -> datetime.time:
    """
    Returns a time object given a string HH:MM:SS or HH:MM
    """
    if not isinstance(time_str, str):
        raise ValueError("Error parsing time: Input must be a string in HH:MM:SS or HH:MM format.")
    try:
        return datetime.strptime(time_str, '%H:%M:%S').time()
    except ValueError:
        try:
            return datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            raise ValueError("Error parsing time: Input must be a string in HH:MM:SS or HH:MM format.")
        

def courseOverlapSlot(course_row: pd.Series, slot: Dict[str, Any]) -> bool:
    """
    Checks if a course overlaps with a given time slot.
    """
    course_days = []
    if course_row.get('M', '').strip():
        course_days.append('Monday')
    if course_row.get('T', '').strip():
        course_days.append('Tuesday')
    if course_row.get('W', '').strip():
        course_days.append('Wednesday')
    if course_row.get('R', '').strip():
        course_days.append('Thursday')
    if course_row.get('F', '').strip():
        course_days.append('Friday')
        
    slot_days = slot['days']
    if not set(course_days).intersection(slot_days):
        return False
    
    try:
        course_start = parseTime(course_row['begin_time'])
        course_end = parseTime(course_row['end_time'])
        slot_start = parseTime(slot['start_time'])
        slot_end = parseTime(slot['end_time'])
    except Exception as e:
        raise ValueError(f"Error parsing time: {e}")

    if not all([course_start, course_end, slot_start, slot_end]):
        return False

    return course_start <= slot_end and course_end >= slot_start


def getBusySlots(courses_df: pd.DataFrame, schedule: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """
    Returns a list of busy slots for a given student's courses.
    """
    busy_slots = set()
    for _, course in courses_df.iterrows():
        if course.get('begin_time') and course.get('end_time'):
            for slot in schedule['blocks']:
                if courseOverlapSlot(course, slot):
                    busy_slots.add(slot['slot'])
    return sorted(list(busy_slots))


def getAllSlots(schedule: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """
    Returns a sorted list of all slots in the schedule.
    """
    return sorted([slot['slot'] for slot in schedule['blocks']])

def getCourseSlot(df_courses: pd.DataFrame, schedule: Dict[str, Any], target_course_code: str) -> str:
    """
    Returns the slot for the given course code.
    """
    course_rows = df_courses[df_courses['crs_cde'] == target_course_code]
    if course_rows.empty:
        raise ValueError(f"No rows found for course '{target_course_code}'")
    
    course_row = course_rows.iloc[0]
    for block in schedule['blocks']:
        if courseOverlapSlot(course_row, block):
            return block['slot']
    
    raise ValueError(f"No overlapping slot found for course '{target_course_code}'")


def cleanExcel(file_path: str) -> pd.DataFrame:
    """
    Cleans and converts Excel data to a pandas DataFrame.
    """
    try:
        df = pd.read_excel(file_path, dtype=str)
        
        for column in df.columns:
            df[column] = df[column].apply(
                lambda x: ' '.join(str(x).split()).strip() if pd.notna(x) else ''
            )

        return df

    except FileNotFoundError:
        raise ValueError(f"Error: '{file_path}' was not found.")
    except Exception as e:
        raise ValueError(f"An unexpected error occurred during data cleaning: {e}")
        return pd.DataFrame()
    
    
def processSchedule(excel_file: str, json_file: str):
    """
    Processes student schedules and writes busy and available slots to an output CSV.
    """
    df = cleanExcel(excel_file)
    if df.empty:
        raise ValueError("Error: Data cleaning failed or file was empty.")

    try:
        with open(json_file, 'r') as file:
            schedule = json.load(file)
    except FileNotFoundError:
        raise ValueError(f"Error: {json_file} not found.")
    except json.JSONDecodeError:
        raise ValueError(f"Error: {json_file} is not a valid JSON file.")
    
    required_columns = ['M', 'T', 'W', 'R', 'F', 'begin_time', 'end_time']
    for col in required_columns:
        if col not in df.columns:
            df[col] = ''
    
    all_slots = getAllSlots(schedule)
    
    grouped = df.groupby('id')
    
    output_records = []
    for student_id, courses in grouped:
        busy_slots = getBusySlots(courses, schedule)
        available_slots = [slot for slot in all_slots if slot not in busy_slots]

        output_records.append({
            'id': student_id,
            'busy_slots': '-'.join(busy_slots),
            'available_slots': '-'.join(available_slots)
        })

    output_df = pd.DataFrame(output_records)
    # output_df.to_csv(output_csv, index=False)

    return output_df


def slotInfo(slot: str, json_file: str) -> List[Any]:
    """
    Returns the time and days information for a given slot.
    """
    try:
        with open(json_file, 'r') as file:
            schedule = json.load(file)
    except FileNotFoundError:
        raise ValueError(f"Error: {json_file} not found.")
    except json.JSONDecodeError:
        raise ValueError(f"Error: {json_file} is not a valid JSON file.")

    for block in schedule['blocks']:
        if block['slot'] == slot:
            days = ''.join([day[0] if day != "Thursday" else "R" for day in block['days']])
            time = f"{block['start_time']}-{block['end_time']}"
            return [days, time]


def readData(excel_file: str, schedule_json: str) -> pd.DataFrame:
    """
    Reads and returns cleaned course data and schedule from JSON file.
    """
    df_courses = cleanExcel(excel_file)
    if df_courses.empty:
        raise ValueError("Could not load or clean course data from Excel file.")
    
    try:
        with open(schedule_json, 'r') as file:
            schedule = json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"'{schedule_json}' not found.")
    except json.JSONDecodeError:
        raise ValueError(f"'{schedule_json}' is not a valid JSON.")
    
    if 'crs_cde' not in df_courses.columns:
        raise ValueError(f"Error: 'crs_cde' column not found in {excel_file}. Cannot identify target section.")

    df_courses['crs_cde'] = df_courses['crs_cde'].apply(lambda x: ' '.join(str(x).split()).strip() if pd.notna(x) else '')
    
    return df_courses, schedule


def getCourses(df_courses: pd.DataFrame) -> List[str]:
    """
    Returns offered courses with some registration.
    """
    if 'crs_cde' not in df_courses.columns:
        raise ValueError("The DataFrame must contain a 'crs_cde' column.")

    return sorted(df_courses['crs_cde'].unique().tolist())


def getStudentsInSection(df_courses: pd.DataFrame, target_course_code: str) -> pd.DataFrame:
    """
    Returns a DataFrame of students in the specified course section.
    """
    students_in_section = df_courses[df_courses['crs_cde'] == target_course_code]

    if students_in_section.empty:
        raise ValueError(f"No students found in section '{target_course_code}'. Please check the course code.")

    original_student_ids = students_in_section['id'].unique()
    return original_student_ids


def getAvailability(df_courses: pd.DataFrame, schedule: Dict[str, Any], 
                    target_course_code: str) -> Dict[str, List[str]]:
    """
    Returns a dictionary mapping student IDs to their busy time slots.
    """
    try:
        original_student_ids = getStudentsInSection(df_courses, target_course_code)
    except ValueError as e:
        raise ValueError(f"Error getting students in section '{target_course_code}': {e}")

    all_slots = getAllSlots(schedule)
    
    student_busy_slots: Dict[str, List[str]] = {}
    for student_id in original_student_ids:
        student_courses = df_courses[df_courses['id'] == student_id]
        student_busy_slots[student_id] = getBusySlots(student_courses, schedule)

    student_available_slots: Dict[str, List[str]] = {}
    for student_id, busy_slots in student_busy_slots.items():
        student_available_slots[student_id] = [
            slot for slot in all_slots if slot not in busy_slots
        ]

    return student_available_slots


def findNewSection(df_courses: pd.DataFrame, schedule: Dict[str, Any], target_course_code: str) -> List[tuple]:
    """
    Finds common potential section for students based on their availability.
    """
    all_slots = getAllSlots(schedule)

    try:
        student_available_slots = getAvailability(df_courses, schedule, target_course_code)
    except Exception as e:
        raise ValueError(f"Error getting student availability: {e}")

    potential_new_sections: Dict[str, List[str]] = defaultdict(list)
    for student_id, available_slots in student_available_slots.items():
        for slot in available_slots:
            if slot:
                potential_new_sections[slot].append(student_id)

    if not potential_new_sections:
        raise ValueError(f"No common free slots found for any students in section '{target_course_code}'.")

    sorted_potential_sections = sorted(
        potential_new_sections.items(),
        key=lambda item: len(item[1]),
        reverse=True
    )

    return sorted_potential_sections


def proposeSections(excel_file: str, schedule_json: str, target_course_code: str, min_students:int = 5):
    """
    Proposes new sections for a course based on student availability.
    """
    try:
        df_courses, schedule = readData(excel_file, schedule_json)
    except (FileNotFoundError, ValueError) as e:
        raise ValueError(f"Error reading data: {e}")

    try:
        potential_sections = findNewSection(df_courses, schedule, target_course_code)
    except Exception as e:
        raise ValueError(f"Error finding new section: {e}")

    suggested_slots = dict()
    for slot, students in potential_sections:
        if len(students) >= min_students:
            suggested_slots[slot] = students
    if not suggested_slots:
        raise ValueError(f"No slots found with at least {min_students} students available.")
    return suggested_slots


def proposeShifts(suggested_slots: dict, selected_slot: str):
    """
    Proposes students to shift for a given suggested slot.
    """
    for slot, students in suggested_slots.items():
        if slot == selected_slot:
            return students
    return []


if __name__ == "__main__":
    exit()