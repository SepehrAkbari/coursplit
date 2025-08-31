import streamlit as st
import os
import uuid
from backend import readData, getCourses, proposeSections, proposeShifts, slotInfo, getCourseSlot, getStudentsInSection

UPLOAD_DIR = "uploads"
SCHEDULE_JSON = "const/FA25_blocks.json"
MIN_STUDENTS_DEFAULT = 5

os.makedirs(UPLOAD_DIR, exist_ok=True)

st.title("Course Splitter")
st.markdown("1. Upload the registration Excel file")
st.markdown("2. Select a course to split and set minimum capacity for new section")
st.markdown("3. View proposed slots based on student availability, and select one")
st.markdown("4. View students available to shift and download the proposal")

## UPLOADING 

uploaded_file = st.file_uploader("Upload registration excel file", type=["xlsx"])
if uploaded_file:
    temp_excel_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.xlsx")
    with open(temp_excel_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    
    st.session_state["excel_path"] = temp_excel_path
    st.success("File uploaded successfully!")

if "excel_path" in st.session_state and os.path.exists(SCHEDULE_JSON):
    try:
        @st.cache_data
        def load_data(excel_path, schedule_json):
            return readData(excel_path, schedule_json)
        
        df_courses, schedule = load_data(st.session_state["excel_path"], SCHEDULE_JSON)
        
        ## COURSE SELECTION

        courses = getCourses(df_courses)
        if courses:
            selected_course = st.selectbox("Select course", options=courses)
            if selected_course:
                min_students = st.number_input("Minimum capacity of new section", min_value=1, value=MIN_STUDENTS_DEFAULT)

                ## CURRENT INFO

                st.subheader("Course Info")
                current_slot = getCourseSlot(df_courses, schedule, selected_course)
                current_num_students = len(getStudentsInSection(df_courses, selected_course))
                st.write(f"**Selected course:** {selected_course}")
                st.write(f"**Slot:** {current_slot}")
                st.write(f"**Number of students:** {current_num_students}")

                ## AVAILABLE SLOTS
                
                suggested_slots = proposeSections(st.session_state["excel_path"], SCHEDULE_JSON, selected_course, min_students)
                if suggested_slots:
                    st.subheader("Available Slots")

                    slot_data = [
                        {
                            "Slot": f"Block {slot} ({slotInfo(slot, SCHEDULE_JSON)[0]} {slotInfo(slot, SCHEDULE_JSON)[1]})",
                            "Available Students": len(students)
                        }
                        for slot, students in suggested_slots.items()
                    ]
                    st.dataframe(slot_data, hide_index=True)
                    
                    ## SHIFTS

                    selected_slot = st.selectbox("Select new slot", options=list(suggested_slots.keys()))
                    if selected_slot:
                        students_to_shift = proposeShifts(suggested_slots, selected_slot)
                        if students_to_shift:
                            st.subheader(f"Students Available to Shift to Slot {selected_slot}")
                            
                            original_students = getStudentsInSection(df_courses, selected_course)
                            original_slot = getCourseSlot(df_courses, schedule, selected_course)
                            
                            remaining_students = [student for student in original_students if student not in students_to_shift]

                            st.write(f"**Remaining students in slot {original_slot} ({len(remaining_students)}):** {', '.join(remaining_students)}")
                            st.write(f"**Students to shift to new slot {selected_slot} ({len(students_to_shift)}):** {', '.join(students_to_shift)}")

                            text_content = ""
                            text_content += f"Course to Split: {selected_course}\n"
                            text_content += f"Original Course Slot: {original_slot}\n"
                            text_content += f"New Slot Added: {selected_slot}\n\n"
                            text_content += f"Students in Slot {original_slot} ({len(remaining_students)}):\n"
                            text_content += ", ".join(remaining_students) + "\n\n"
                            text_content += f"Students in Slot {selected_slot} ({len(students_to_shift)}):\n"
                            text_content += ", ".join(students_to_shift) + "\n"

                            st.download_button(
                                label="Download Proposal",
                                data=text_content,
                                file_name=f"{selected_course.replace(' ', '_')}_split_proposal.txt",
                                mime="text/plain"
                            )
                        else:
                            st.warning("No students available for this slot.")
                else:
                    st.warning("No proposed slots found with the given criteria.")
        else:
            st.error("No courses found in the uploaded file.")
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
else:
    if not os.path.exists(SCHEDULE_JSON):
        st.error("Schedule JSON file not found. Place 'FA25_blocks.json' in the project root.")