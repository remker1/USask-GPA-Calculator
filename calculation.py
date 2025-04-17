from courses import Course
import re
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog, messagebox
import os

# This script reads a PDF containing course information, parses the data to create Course objects,
# and provides a GUI to display, modify, and calculate weighted averages of grades for those courses.

def read_pdf(file_path):
    """Reads a PDF file and extracts text from it."""
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()  # Extract text from each page
    return text

def parse_courses(text):
    """Parses the extracted text to find courses and their details."""
    # Regex pattern to match course details
    course_pattern = re.compile(
        r'(?P<subject>[A-Z]{2,4})\s+(?P<code>\d{3}|[A-Z]+)\s+.*?(Campus|Site)\s+(?P<level>UG|GR)\s+(?P<title>.*?)\s+(?P<grade>\d{1,3}|TR|W)\s+(?P<credit_hours>\d\.\d{3})',
        re.DOTALL
    )

    courses = []
    for match in course_pattern.finditer(text):  # Find all matches in the text
        label = f"{match.group('subject')}{match.group('code')}"
        raw_location = match.group(0)
        # Determine location based on the presence of 'Off-campus'
        location = "Off-campus Site" if "Off-campus" in raw_location else "USask - Main Campus"
        level = match.group("level")
        title = " ".join(match.group("title").split())  # Normalize title spacing
        grade = match.group("grade")
        credit_hours = float(match.group("credit_hours"))

        # Create a Course object and add it to the list
        course = Course(
            label=label,
            location=location,
            level=level,
            title=title,
            grade=grade,
            credit_hours=credit_hours
        )
        courses.append(course)

    return courses

def deduplicate_courses(courses):
    """Removes duplicate courses, keeping the latest occurrence."""
    unique = {}
    for course in courses:
        key = course.label
        unique[key] = course  # Replace if exists; keeps latest occurrence
    return list(unique.values())

def calculate_weighted_average(courses):
    """Calculates the total credits, weighted sum of grades, and average grade."""
    total_credits = 0.0
    weighted_sum = 0.0
    for course in courses:
        try:
            grade = float(course.grade)  # Attempt to convert grade to float
            total_credits += course.credit_hours
            weighted_sum += grade * course.credit_hours
        except ValueError:
            continue  # Skip if grade is not numeric (e.g., TR or W)
    average = weighted_sum / total_credits if total_credits > 0 else 0  # Avoid division by zero
    return total_credits, weighted_sum, average

def check_updated_average(courses):
    """Prompts the user to enter a new grade for a specific course and updates the average."""
    user_input = input("\nEnter a course label and new grade separated by a comma (or press Enter to skip): ").strip()
    if not user_input:
        return  # Exit if no input

    try:
        label, new_grade = [part.strip() for part in user_input.split(",")]
        updated_courses = []
        found = False
        for course in courses:
            if course.label == label:
                # Create a new Course object with the updated grade
                updated_course = Course(
                    label=course.label,
                    location=course.location,
                    level=course.level,
                    title=course.title,
                    grade=new_grade,
                    credit_hours=course.credit_hours
                )
                updated_courses.append(updated_course)
                found = True
            else:
                updated_courses.append(course)  # Keep the original course

        if not found:
            print(f"Course '{label}' not found.")  # Notify if course not found
            return

        # Calculate the new totals and averages
        total_credits, weighted_sum, average = calculate_weighted_average(updated_courses)
        print(f"\nUpdated Total Credits: {total_credits}")
        print(f"Updated Weighted Grade Sum: {weighted_sum}")
        print(f"Updated Average Grade: {average:.2f}")

    except ValueError:
        print("Invalid input. Please enter in the format: CMPT214, 85")

def on_double_click(event):
    """Handles the double-click event on the course tree to edit grades."""
    selected_item = tree.focus()  # Get the currently selected item
    if not selected_item:
        return  # Exit if no item is selected
    values = tree.item(selected_item, "values")  # Get the values of the selected item
    if not values:
        return  # Exit if no values are found

    label = values[0]  # Get the course label

    # Prompt for new grade
    new_grade = simpledialog.askstring("Edit Grade", f"Enter new grade for {label}:")

    if new_grade:
        for i, course in enumerate(unique_courses):
            if course.label == label:
                try:
                    float(new_grade)  # Validate grade is numeric or accepted format
                    course.grade = new_grade  # Update the course grade
                    # Update the tree view with the new values
                    tree.item(selected_item, values=(course.label, course.title, course.grade, course.credit_hours))
                    total_credits, weighted_sum, average = calculate_weighted_average(unique_courses)
                    # Update the summary frame with new totals
                    for widget in summary_frame.winfo_children():
                        widget.destroy()
                    tk.Label(summary_frame, text=f"Total Credits: {total_credits}").pack()
                    tk.Label(summary_frame, text=f"Weighted Grade Sum: {weighted_sum}").pack()
                    tk.Label(summary_frame, text=f"Average Grade: {average:.2f}").pack()
                except ValueError:
                    tk.messagebox.showerror("Invalid Grade", "Please enter a valid numeric grade or allowed value.")
                break

if __name__ == "__main__":
    def find_pdf_file():
        """Searches the current directory for a PDF file."""
        for file in os.listdir():
            if file.lower().endswith(".pdf"):
                return file  # Return the first PDF file found
        return None

    pdf_file = find_pdf_file()  # Attempt to find a PDF file
    if not pdf_file:
        print("No PDF file found in the current directory.")
        exit()

    pdf_text = read_pdf(pdf_file)  # Read the PDF file
    courses = parse_courses(pdf_text)  # Parse the courses from the text
    unique_courses = deduplicate_courses(courses)  # Remove duplicates
    original_courses = {course.label: Course(**course.to_dict()) for course in unique_courses}  # Store original courses
    total_credits, weighted_sum, average = calculate_weighted_average(unique_courses)  # Calculate initial totals

    root = tk.Tk()  # Create the main application window
    root.title("Course Transcript Summary")

    instruction_label = tk.Label(root, text="Double-click to modify the grades to see an estimate")
    instruction_label.pack(pady=5)  # Instruction label

    # Create a treeview to display course information
    tree = ttk.Treeview(root, columns=("Label", "Title", "Grade", "Credits"), show="headings")
    tree.heading("Label", text="Course")
    tree.heading("Title", text="Title")
    tree.heading("Grade", text="Grade")
    tree.heading("Credits", text="Credits")
    tree.column("Label", anchor="center")
    tree.column("Title", anchor="center")
    tree.column("Grade", anchor="center")
    tree.column("Credits", anchor="center")

    for course in unique_courses:
        tree.insert("", "end", values=(course.label, course.title, course.grade, course.credit_hours))  # Insert courses into tree

    tree.pack(fill="both", expand=True)  # Pack treeview to fill the window
    tree.bind("<Double-1>", on_double_click)  # Bind double-click event to the on_double_click function

    summary_frame = tk.Frame(root)  # Frame to display summary information
    summary_frame.pack(pady=10)

    tk.Label(summary_frame, text=f"Total Credits: {total_credits}").pack()  # Total credits label
    tk.Label(summary_frame, text=f"Weighted Grade Sum: {weighted_sum}").pack()  # Weighted grade sum label
    tk.Label(summary_frame, text=f"Average Grade: {average:.2f}").pack()  # Average grade label

    def restore_grades():
        """Restores the original grades of the courses."""
        global unique_courses
        unique_courses = [Course(**original_courses[label].to_dict()) for label in original_courses]  # Restore original courses

        # Clear and repopulate the tree
        for item in tree.get_children():
            tree.delete(item)  # Remove existing items from the tree
        for course in unique_courses:
            tree.insert("", "end", values=(course.label, course.title, course.grade, course.credit_hours))  # Insert restored courses

        # Update summary with restored grades
        total_credits, weighted_sum, average = calculate_weighted_average(unique_courses)
        for widget in summary_frame.winfo_children():
            widget.destroy()  # Clear existing summary labels
        tk.Label(summary_frame, text=f"Total Credits: {total_credits}").pack()  # Update total credits
        tk.Label(summary_frame, text=f"Weighted Grade Sum: {weighted_sum}").pack()  # Update weighted grade sum
        tk.Label(summary_frame, text=f"Average Grade: {average:.2f}").pack()  # Update average grade

    restore_btn = tk.Button(root, text="Restore Original Grades", command=restore_grades)
    restore_btn.pack(pady=5)  # Button to restore original grades

    def add_course():
        """Prompts the user to add a new course."""
        user_input = simpledialog.askstring("Add Course", "Enter course in format: LABEL,GRADE,CREDITS\nExample: CMPT499,85,3")
        if not user_input:
            return  # Exit if no input
        try:
            label, grade, credit_str = [part.strip() for part in user_input.split(",")]
            float_grade = float(grade)  # Validate grade as float
            credit_hours = float(credit_str)  # Validate credits as float
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter the course in the correct format: LABEL,GRADE,CREDITS")
            return  # Exit if input is invalid

        # Create a new Course object with temporary values
        new_course = Course(
            label=label,
            location="Temporary Estimate",
            level="Temporary Estimate",
            title="Temporary Estimate",
            grade=grade,
            credit_hours=credit_hours
        )
        unique_courses.append(new_course)  # Add new course to the list
        tree.insert("", "end", values=(new_course.label, new_course.title, new_course.grade, new_course.credit_hours))  # Insert into tree

        # Update summary with new totals
        total_credits, weighted_sum, average = calculate_weighted_average(unique_courses)
        for widget in summary_frame.winfo_children():
            widget.destroy()  # Clear existing summary labels
        tk.Label(summary_frame, text=f"Total Credits: {total_credits}").pack()  # Update total credits
        tk.Label(summary_frame, text=f"Weighted Grade Sum: {weighted_sum}").pack()  # Update weighted grade sum
        tk.Label(summary_frame, text=f"Average Grade: {average:.2f}").pack()  # Update average grade

    add_btn = tk.Button(root, text="Add New Course", command=add_course)
    add_btn.pack(pady=5)  # Button to add a new course

    def delete_course():
        """Deletes the selected course from the list and updates the UI."""
        selected_item = tree.focus()  # Get the currently selected item
        if not selected_item:
            messagebox.showinfo("Delete Course", "Please select a course to delete.")
            return  # Exit if no item is selected
        values = tree.item(selected_item, "values")  # Get the values of the selected item
        if not values:
            return  # Exit if no values are found
        label = values[0]  # Get the course label

        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {label}?")
        if confirm:
            # Remove from list
            for i, course in enumerate(unique_courses):
                if course.label == label:
                    del unique_courses[i]  # Delete the course from the list
                    break
            # Remove from tree
            tree.delete(selected_item)  # Delete the course from the tree

            # Update summary
            total_credits, weighted_sum, average = calculate_weighted_average(unique_courses)
            for widget in summary_frame.winfo_children():
                widget.destroy()  # Clear existing summary labels
            tk.Label(summary_frame, text=f"Total Credits: {total_credits}").pack()  # Update total credits
            tk.Label(summary_frame, text=f"Weighted Grade Sum: {weighted_sum}").pack()  # Update weighted grade sum
            tk.Label(summary_frame, text=f"Average Grade: {average:.2f}").pack()  # Update average grade

    delete_btn = tk.Button(root, text="Delete Selected Course", command=delete_course)
    delete_btn.pack(pady=5)  # Button to delete the selected course

    root.mainloop()  # Start the GUI event loop