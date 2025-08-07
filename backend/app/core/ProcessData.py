import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any


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
        print(f"Error parsing time: {e}")
        return False

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
        print(f"Error: '{file_path}' was not found.")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred during data cleaning: {e}")
        return pd.DataFrame()


def processSchedule(excel_file: str, json_file: str, output_csv: str):
    """
    Processes student schedules and writes busy and available slots to an output CSV.
    """
    df = cleanExcel(excel_file)
    if df.empty:
        print("Error: Data cleaning failed or file was empty.")
        return

    try:
        with open(json_file, 'r') as file:
            schedule = json.load(file)
    except FileNotFoundError:
        print(f"Error: {json_file} not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: {json_file} is not a valid JSON file.")
        return
    
    required_columns = ['M', 'T', 'W', 'R', 'F', 'begin_time', 'end_time']
    for col in required_columns:
        if col not in df.columns:
            df[col] = ''
    
    all_slots = getAllSlots(schedule)
    
    grouped = df.groupby('modified_id')
    
    output_records = []
    for student_id, courses in grouped:
        busy_slots = getBusySlots(courses, schedule)
        available_slots = [slot for slot in all_slots if slot not in busy_slots]

        output_records.append({
            'modified_id': student_id,
            'busy_slots': '-'.join(busy_slots),
            'available_slots': '-'.join(available_slots)
        })

    output_df = pd.DataFrame(output_records)
    output_df.to_csv(output_csv, index=False)


'''
USAGE BLUEPRINT -- IMPLEMENT IN FASTAPI
'''
if __name__ == "__main__":
    print("Processing...")

    # Path to the data directory
    data_dir = "../../data"

    # Path to the Excel file with course registrations
    registrations = f'{data_dir}/FA25_registrations.xlsx'
    # Path to a JSON file with the schedule blocks
    schedule = f'{data_dir}/FA25_blocks.json'
    # Path to save output CSV file with busy and available slots
    availability = f'{data_dir}/FA25_student_availability.csv'

    processSchedule(registrations, schedule, availability)
    print(f"Output written to {availability}")