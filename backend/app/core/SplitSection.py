import pandas as pd
import json
from typing import Dict, List, Any
from collections import defaultdict

from ProcessData import *


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
        print(f"Error: 'crs_cde' column not found in {excel_file}. Cannot identify target section.")
        return
    
    df_courses['crs_cde'] = df_courses['crs_cde'].apply(lambda x: ' '.join(str(x).split()).strip() if pd.notna(x) else '')
    
    return df_courses, schedule


def getStudentsInSection(df_courses: pd.DataFrame, target_course_code: str) -> pd.DataFrame:
    """
    Returns a DataFrame of students in the specified course section.
    """
    students_in_section = df_courses[df_courses['crs_cde'] == target_course_code]

    if students_in_section.empty:
        print(f"No students found in section '{target_course_code}'. Please check the course code.")
    
    original_student_ids = students_in_section['modified_id'].unique()
    return original_student_ids


def getAvailability(df_courses: pd.DataFrame, schedule: Dict[str, Any], 
                    target_course_code: str) -> Dict[str, List[str]]:
    """
    Returns a dictionary mapping student IDs to their busy time slots.
    """
    try:
        original_student_ids = getStudentsInSection(df_courses, target_course_code)
        print(f"Found {len(original_student_ids)} students in original section '{target_course_code}'.")
    except ValueError as e:
        print(f"Error getting students in section '{target_course_code}': {e}")
        return
    
    all_slots = getAllSlots(schedule)
    
    student_busy_slots: Dict[str, List[str]] = {}
    for student_id in original_student_ids:
        student_courses = df_courses[df_courses['modified_id'] == student_id]
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
    try:
        student_available_slots = getAvailability(df_courses, schedule, target_course_code)
    except Exception as e:
        print(f"Error getting student availability: {e}")
        return

    potential_new_sections: Dict[str, List[str]] = defaultdict(list)
    for student_id, available_slots in student_available_slots.items():
        for slot in available_slots:
            if slot:
                potential_new_sections[slot].append(student_id)

    if not potential_new_sections:
        print(f"No common free slots found for any students in section '{target_course_code}'.")
        return

    sorted_potential_sections = sorted(
        potential_new_sections.items(),
        key=lambda item: len(item[1]),
        reverse=True
    )

    return sorted_potential_sections


def proposeSection(excel_file: str, schedule_json: str, target_course_code: str, target_split_size: int = 20) -> None:
    """
    Proposes a new section for the specified course based on alternative sections.
    """
    print(f"\nAttempting to split section: {target_course_code}")

    try:
        df_courses, schedule = readData(excel_file, schedule_json)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading data: {e}")
        return
    
    try:
        potential_sections = findNewSection(df_courses, schedule, target_course_code)
    except Exception as e:
        print(f"Error finding new section: {e}")
        return

    found_suitable_split = False
    for slot, students in potential_sections:
        num_students = len(students)
        print(f"Slot '{slot}': {num_students} students available.")
        
        if num_students >= target_split_size or (not found_suitable_split and slot == potential_sections[0][0]):
            found_suitable_split = True
        
    print(f"\nProposed New Section for {target_course_code}:\n\nMove up to {num_students} students to a new section at Slot {slot}.\n\nStudent IDs available to move:")
    for student_id in students:
        print(f"    - {student_id}")

    if not found_suitable_split:
        print(f"\nCould not find a single slot to accommodate {target_split_size} students.")
        if potential_sections:
            best_slot_info = potential_sections[0]
            best_slot_code = best_slot_info[0]
            best_slot_students = best_slot_info[1]
            print(f"The best possible option found is to move {len(best_slot_students)} students to **Slot {best_slot_code}**.")
            print("Student IDs for this best option:")
            for student_id in best_slot_students:
                print(f"  - {student_id}")
        else:
            print("No students could be moved to any new section without conflicts.")


# '''
# USAGE BLUEPRINT -- IMPLEMENT IN FASTAPI
# '''
if __name__ == "__main__":
    # Path to the data directory
    data_dir = "../../data"
    # Path to the Excel file with course registrations
    registrations = f'{data_dir}/FA25_registrations.xlsx'
    # Path to a JSON file with the schedule blocks
    schedule = f'{data_dir}/FA25_blocks.json'

    # # Target course section to split
    # course = "COLL 210 01"
    
    # find_new_section_time(
    #     target_course_code=course,
    #     excel_file=registrations,
    #     schedule_json=schedule,
    #     target_split_size=20
    # )

    running = True
    while running:
        course = str(input("Enter course (or q to quit): "))
        if course.lower() == 'q':
            running = False
            continue
        try:
            proposeSection(
                excel_file=registrations,
                schedule_json=schedule,
                target_course_code=course,
                target_split_size=20
            )
        except Exception as e:
            print(f"An error occurred while processing the course '{course}': {e}")
            continue