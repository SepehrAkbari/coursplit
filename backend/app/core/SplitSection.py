import pandas as pd
import json
from typing import Dict, List, Any
from collections import defaultdict

from ProcessData import *

def find_new_section_time(
    target_course_code: str,
    excel_file: str,
    schedule_json: str,
    target_split_size: int = 20
) -> None:
    """
    Finds a suitable new time slot and a group of students from a single
    course section to move, aiming for a target split size.
    """
    print(f"Attempting to split section: {target_course_code}")

    df_courses = cleanExcel(excel_file)
    if df_courses.empty:
        print("Error: Could not load or clean course data from Excel file.")
        return

    try:
        with open(schedule_json, 'r') as file:
            schedule = json.load(file)
    except FileNotFoundError:
        print(f"Error: '{schedule_json}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: '{schedule_json}' is not a valid JSON.")
        return

    if 'crs_cde' not in df_courses.columns:
        print(f"Error: 'crs_cde' column not found in {excel_file}. Cannot identify target section.")
        return
    
    df_courses['crs_cde'] = df_courses['crs_cde'].apply(lambda x: ' '.join(str(x).split()).strip() if pd.notna(x) else '')

    students_in_target_section_df = df_courses[df_courses['crs_cde'] == target_course_code]
    
    if students_in_target_section_df.empty:
        print(f"No students found in section '{target_course_code}'. Please check the course code.")
        return

    original_student_ids = students_in_target_section_df['modified_id'].unique()
    print(f"Found {len(original_student_ids)} students in original section '{target_course_code}'.")

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
    
    found_suitable_split = False
    for slot, students in sorted_potential_sections:
        num_students = len(students)
        print(f"Slot '{slot}': {num_students} students available.")
        
        if num_students >= target_split_size or (not found_suitable_split and slot == sorted_potential_sections[0][0]):
            print(f"\n--- Proposed New Section for '{target_course_code}' ---")
            print(f"Move {num_students} students to a new section at **Slot {slot}**.")
            print("These students have no schedule conflicts with this new slot.")
            print("Student IDs to move:")
            for student_id in students:
                print(f"  - {student_id}")
            found_suitable_split = True
            break

    if not found_suitable_split:
        print(f"\nCould not find a single slot to accommodate {target_split_size} students.")
        if sorted_potential_sections:
            best_slot_info = sorted_potential_sections[0]
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

    # Target course section to split
    course = "COLL 210 01"
    
    find_new_section_time(
        target_course_code=course,
        excel_file=registrations,
        schedule_json=schedule,
        target_split_size=20
    )