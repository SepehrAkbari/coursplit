import streamlit as st
import os
import uuid
from backend import readData, getCourses, proposeSections, proposeShifts, slotInfo, getCourseSlot, getStudentsInSection

UPLOAD_DIR = "uploads"
SCHEDULE_JSON = "const/FA25_blocks.json"
MIN_STUDENTS_DEFAULT = 5

if "schedule_path" not in st.session_state:
    st.session_state["schedule_path"] = SCHEDULE_JSON
if "show_json_upload" not in st.session_state:
    st.session_state["show_json_upload"] = False

@st.cache_data
def load_data(excel_path, schedule_path):
    return readData(excel_path, schedule_path)

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
    
    col1, col2 = st.columns([5, 1])
    col1.write(f"Using schedule reference: {os.path.basename(st.session_state['schedule_path'])}")
    col1.write("If you want to use a different schedule, press the upload button. Make sure the JSON format matches the expected structure.")
    if col2.button("Upload file"):
        st.session_state["show_json_upload"] = True

    if st.session_state["show_json_upload"]:
        json_upload = st.file_uploader("Upload custom schedule JSON", type=["json"])
        if json_upload:
            temp_json_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.json")
            with open(temp_json_path, "wb") as f:
                f.write(json_upload.getvalue())
            st.session_state["schedule_path"] = temp_json_path
            st.session_state["show_json_upload"] = False
            st.success("Custom schedule uploaded successfully!")
            st.cache_data.clear()
            st.rerun()

if "excel_path" in st.session_state and os.path.exists(st.session_state["schedule_path"]):
    try:
        @st.cache_data
        def load_data(excel_path, schedule_json):
            return readData(excel_path, schedule_json)
        
        df_courses, schedule = load_data(st.session_state["excel_path"], st.session_state["schedule_path"])
        
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
                
                suggested_slots = proposeSections(st.session_state["excel_path"], st.session_state["schedule_path"], selected_course, min_students)
                if suggested_slots:
                    st.subheader("Available Slots")

                    slot_data = [
                        {
                            "Slot": f"Block {slot} ({slotInfo(slot, st.session_state['schedule_path'])[0]} {slotInfo(slot, st.session_state['schedule_path'])[1]})",
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
                            st.subheader(f"Slot {selected_slot}'s proposed shifts")
                            
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
    if "excel_path" not in st.session_state:
        st.info("Please upload the Excel file to proceed.")
    elif not os.path.exists(st.session_state["schedule_path"]):
        st.error("Schedule JSON file not found. Please ensure it's available or upload a custom one.")