from courses import Course
import re
import fitz  # PyMuPDF
import os
import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QInputDialog,
)
from PySide6.QtCore import Qt

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
        if course.grade == "W":
            continue  # Skip withdrawal courses
        try:
            grade = float(course.grade)  # Attempt to convert grade to float
            total_credits += course.credit_hours
            weighted_sum += grade * course.credit_hours
        except ValueError:
            continue  # Skip if grade is not numeric (e.g., TR)
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

class MainWindow(QMainWindow):
    def __init__(self, courses, original_courses):
        super().__init__()
        self.setWindowTitle("Course Transcript Summary")

        self.courses = courses
        # original_courses is a dict: label -> Course
        self.original_courses = original_courses

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        instruction_label = QLabel("Double-click a grade to modify it to see an estimate")
        main_layout.addWidget(instruction_label)

        self.table = QTableWidget(len(self.courses), 4)
        self.table.setHorizontalHeaderLabels(["Course", "Title", "Grade", "Credits"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.cellDoubleClicked.connect(self.edit_grade)

        main_layout.addWidget(self.table)

        self.summary_label = QLabel()
        self.summary_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(self.summary_label)

        button_row = QHBoxLayout()
        self.restore_btn = QPushButton("Restore Original Grades")
        self.restore_btn.clicked.connect(self.restore_grades)
        button_row.addWidget(self.restore_btn)

        self.add_btn = QPushButton("Add New Course")
        self.add_btn.clicked.connect(self.add_course)
        button_row.addWidget(self.add_btn)

        self.delete_btn = QPushButton("Delete Selected Course")
        self.delete_btn.clicked.connect(self.delete_course)
        button_row.addWidget(self.delete_btn)

        main_layout.addLayout(button_row)

        self.populate_table()
        self.update_summary()

    def populate_table(self):
        self.table.setRowCount(len(self.courses))
        for row, course in enumerate(self.courses):
            label_item = QTableWidgetItem(course.label)
            title_item = QTableWidgetItem(course.title)
            grade_item = QTableWidgetItem(str(course.grade))
            credits_item = QTableWidgetItem(f"{course.credit_hours:.3f}")

            label_item.setFlags(label_item.flags() & ~Qt.ItemIsEditable)
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
            credits_item.setFlags(credits_item.flags() & ~Qt.ItemIsEditable)

            self.table.setItem(row, 0, label_item)
            self.table.setItem(row, 1, title_item)
            self.table.setItem(row, 2, grade_item)
            self.table.setItem(row, 3, credits_item)

        self.table.resizeColumnsToContents()

    def update_summary(self):
        total_credits, weighted_sum, average = calculate_weighted_average(self.courses)
        self.summary_label.setText(
            f"Total Credits: {total_credits:.3f}    "
            f"Weighted Grade Sum: {weighted_sum:.2f}    "
            f"Average Grade: {average:.2f}"
        )

    def find_course_by_label(self, label):
        for course in self.courses:
            if course.label == label:
                return course
        return None

    def edit_grade(self, row, column):
        # Only allow editing on the Grade column, but we still accept double-click on any column and prompt for grade
        label_item = self.table.item(row, 0)
        if label_item is None:
            return
        label = label_item.text()

        course = self.find_course_by_label(label)
        if course is None:
            return

        current_grade = str(course.grade)
        new_grade, ok = QInputDialog.getText(
            self,
            "Edit Grade",
            f"Enter new grade for {label}:",
            text=current_grade,
        )
        if not ok or not new_grade.strip():
            return

        new_grade = new_grade.strip()
        try:
            float(new_grade)
        except ValueError:
            QMessageBox.critical(self, "Invalid Grade", "Please enter a valid numeric grade.")
            return

        course.grade = new_grade
        # Update table
        self.table.item(row, 2).setText(str(course.grade))
        self.update_summary()

    def restore_grades(self):
        # Recreate courses list from original_courses dict
        self.courses = [Course(**self.original_courses[label].to_dict()) for label in self.original_courses]
        self.populate_table()
        self.update_summary()

    def add_course(self):
        text, ok = QInputDialog.getText(
            self,
            "Add Course",
            "Enter course in format: LABEL,GRADE,CREDITS\nExample: CMPT499,85,3",
        )
        if not ok or not text.strip():
            return

        user_input = text.strip()
        try:
            label, grade, credit_str = [part.strip() for part in user_input.split(",")]
            float_grade = float(grade)  # validate
            credit_hours = float(credit_str)
        except ValueError:
            QMessageBox.critical(
                self,
                "Invalid Input",
                "Please enter the course in the correct format: LABEL,GRADE,CREDITS",
            )
            return

        new_course = Course(
            label=label,
            location="Temporary Estimate",
            level="Temporary Estimate",
            title="Temporary Estimate",
            grade=grade,
            credit_hours=credit_hours,
        )
        self.courses.append(new_course)
        self.populate_table()
        self.update_summary()

    def delete_course(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Delete Course", "Please select a course to delete.")
            return

        label_item = self.table.item(row, 0)
        if label_item is None:
            return

        label = label_item.text()

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {label}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
            )
        if reply != QMessageBox.Yes:
            return

        # Remove from list
        self.courses = [course for course in self.courses if course.label != label]

        # Remove row from table
        self.table.removeRow(row)
        self.update_summary()

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
        sys.exit(1)

    pdf_text = read_pdf(pdf_file)  # Read the PDF file
    courses = parse_courses(pdf_text)  # Parse the courses from the text
    unique_courses = deduplicate_courses(courses)  # Remove duplicates

    # Store original courses as a dict of label -> Course
    original_courses = {course.label: Course(**course.to_dict()) for course in unique_courses}

    app = QApplication(sys.argv)
    window = MainWindow(unique_courses, original_courses)
    window.resize(900, 600)
    window.show()
    sys.exit(app.exec())
"""Course transcript parser and GPA estimator GUI.

This script:
- Scans the current directory for a transcript PDF.
- Extracts text from the PDF using PyMuPDF (fitz).
- Parses course entries and creates Course objects.
- Deduplicates courses that appear multiple times, keeping the latest one.
- Provides a Qt (PySide6) GUI to:
  - View all parsed courses.
  - Edit grades to estimate GPA changes.
  - Add temporary / hypothetical courses.
  - Delete courses.
  - Restore all original grades.

The main entry point is at the bottom of the file under the
`if __name__ == "__main__":` guard.
"""

from courses import Course
import re
import fitz  # PyMuPDF: provides PDF reading and text extraction
import os
import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QInputDialog,
)
from PySide6.QtCore import Qt


def read_pdf(file_path: str) -> str:
    """Read a PDF file and return its full text content as a single string.

    Parameters
    ----------
    file_path : str
        Path to the PDF transcript file.

    Returns
    -------
    str
        Concatenated text from all pages of the PDF.
    """
    text = ""

    # Open the PDF; fitz.Document is used as a context manager.
    with fitz.open(file_path) as doc:
        for page in doc:
            # `get_text()` extracts the visible text content from each page.
            text += page.get_text()

    return text


def parse_courses(text: str) -> list[Course]:
    """Parse raw transcript text and return a list of Course objects.

    This is tightly coupled to the transcript's layout and uses a regex to
    capture:
    - subject (e.g. CMPT)
    - code    (e.g. 214)
    - level   (UG/GR)
    - title   (course name)
    - grade   (numeric grade, TR, or W)
    - credit_hours (e.g. 3.000)

    Parameters
    ----------
    text : str
        Full transcript text extracted from the PDF.

    Returns
    -------
    list[Course]
        A list of parsed Course instances.
    """

    # Regex pattern to match each course line / block. This is based on the
    # USask transcript format and may need adjustments if the layout changes.
    course_pattern = re.compile(
        r"(?P<subject>[A-Z]{2,4})\s+"  # Subject code, e.g. CMPT
        r"(?P<code>\d{3}|[A-Z]+)\s+"   # Course number or letter code
        r".*?(Campus|Site)\s+"         # Campus / Site marker (non-capturing)
        r"(?P<level>UG|GR)\s+"         # Level: Undergraduate or Graduate
        r"(?P<title>.*?)\s+"           # Course title (lazy match)
        r"(?P<grade>\d{1,3}|TR|W)\s+" # Grade: numeric, TR, or W
        r"(?P<credit_hours>\d\.\d{3})", # Credit hours: 3.000, 1.500, etc.
        re.dotall,
    )

    courses: list[Course] = []

    # Iterate over every match of the course pattern in the transcript text.
    for match in course_pattern.finditer(text):
        # Create a compact label (e.g. CMPT214) used as a unique identifier.
        label = f"{match.group('subject')}{match.group('code')}"

        # `match.group(0)` returns the full matched text for this course.
        raw_location = match.group(0)

        # Determine location based on whether 'Off-campus' appears in the block.
        # This is a heuristic: if the transcript format changes, you may need
        # to adjust this logic.
        if "Off-campus" in raw_location:
            location = "Off-campus Site"
        else:
            location = "USask - Main Campus"

        level = match.group("level")

        # Normalize whitespace in the title by splitting and rejoining.
        title = " ".join(match.group("title").split())

        grade = match.group("grade")
        credit_hours = float(match.group("credit_hours"))

        # Create a Course object and append it to the list.
        course = Course(
            label=label,
            location=location,
            level=level,
            title=title,
            grade=grade,
            credit_hours=credit_hours,
        )
        courses.append(course)

    return courses


def deduplicate_courses(courses: list[Course]) -> list[Course]:
    """Remove duplicate courses based on the label, keeping the latest one.

    If the same course label appears multiple times in the transcript (e.g.
    repeat attempts), this function keeps only the last occurrence in the
    input list.

    Parameters
    ----------
    courses : list[Course]
        Courses in the original order returned by parsing.

    Returns
    -------
    list[Course]
        A list where each `label` appears at most once.
    """
    unique: dict[str, Course] = {}

    # We rely on the fact that later items overwrite earlier ones, so the
    # resulting dict keeps the last occurrence of each course label.
    for course in courses:
        key = course.label
        unique[key] = course

    return list(unique.values())


def calculate_weighted_average(courses: list[Course]) -> tuple[float, float, float]:
    """Calculate total credits, weighted grade sum, and average grade.

    Courses with grade "W" are ignored. Courses with non-numeric grades such
    as "TR" are also skipped because they do not contribute to numeric GPA.

    Parameters
    ----------
    courses : list[Course]
        List of courses to include in the calculation.

    Returns
    -------
    (float, float, float)
        (total_credits, weighted_sum, average), where `average` is 0 if
        `total_credits` is 0.
    """
    total_credits: float = 0.0
    weighted_sum: float = 0.0

    for course in courses:
        # Skip withdrawals entirely.
        if course.grade == "W":
            continue

        try:
            # Convert the grade to a float. This will fail for "TR" and other
            # non-numeric grades.
            grade_value = float(course.grade)
        except ValueError:
            # Non-numeric grade: ignore this course in GPA calculation.
            continue

        # At this point, we know the grade is numeric.
        total_credits += course.credit_hours
        weighted_sum += grade_value * course.credit_hours

    # Protect against division by zero when there are no valid credit courses.
    average = weighted_sum / total_credits if total_credits > 0 else 0.0
    return total_credits, weighted_sum, average


def check_updated_average(courses: list[Course]) -> None:
    """CLI helper to prompt for a new grade and recompute the average.

    This function is currently unused in the GUI, but is kept for
    command-line experiments.

    Parameters
    ----------
    courses : list[Course]
        Existing course list whose grades may be updated temporarily.
    """
    user_input = input(
        "\nEnter a course label and new grade separated by a comma "
        "(or press Enter to skip): "
    ).strip()

    # If the user just presses Enter, we do nothing.
    if not user_input:
        return

    try:
        # Expect input in the format: CMPT214, 85
        label, new_grade = [part.strip() for part in user_input.split(",")]

        updated_courses: list[Course] = []
        found = False

        for course in courses:
            if course.label == label:
                # Create a new Course object with the updated grade while
                # keeping all other fields the same.
                updated_course = Course(
                    label=course.label,
                    location=course.location,
                    level=course.level,
                    title=course.title,
                    grade=new_grade,
                    credit_hours=course.credit_hours,
                )
                updated_courses.append(updated_course)
                found = True
            else:
                updated_courses.append(course)

        if not found:
            print(f"Course '{label}' not found.")
            return

        total_credits, weighted_sum, average = calculate_weighted_average(
            updated_courses
        )
        print(f"\nUpdated Total Credits: {total_credits}")
        print(f"Updated Weighted Grade Sum: {weighted_sum}")
        print(f"Updated Average Grade: {average:.2f}")

    except ValueError:
        print("Invalid input. Please enter in the format: CMPT214, 85")


class MainWindow(QMainWindow):
    """Main application window for visualizing and editing course grades.

    The window shows:
    - A table of all courses (label, title, grade, credits).
    - A summary row with total credits, weighted sum, and average.
    - Buttons to restore original grades, add a new course, and delete the
      currently selected course.

    Double-clicking on a row opens a dialog to edit the grade for that course.
    """

    def __init__(self, courses: list[Course], original_courses: dict[str, Course]):
        super().__init__()
        self.setWindowTitle("Course Transcript Summary")

        # `courses` is the working list that the user can modify.
        self.courses: list[Course] = courses

        # `original_courses` is a mapping from label -> Course representing
        # the unmodified state from the transcript. Used to restore the table.
        self.original_courses: dict[str, Course] = original_courses

        # Set up the central widget and base vertical layout.
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # High-level instructions for the user.
        instruction_label = QLabel(
            "Double-click a grade to modify it and see an updated estimate."
        )
        main_layout.addWidget(instruction_label)

        # ------------------------------------------------------------------
        # Courses table
        # ------------------------------------------------------------------
        # 4 columns: Course label, Title, Grade, Credits
        self.table = QTableWidget(len(self.courses), 4)
        self.table.setHorizontalHeaderLabels(["Course", "Title", "Grade", "Credits"])

        # Make row-based selection feel more natural (click anywhere on row).
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        # Connect double-click on any cell to grade editing logic.
        self.table.cellDoubleClicked.connect(self.edit_grade)

        main_layout.addWidget(self.table)

        # Summary label: shows total credits, weighted sum, and average GPA.
        self.summary_label = QLabel()
        self.summary_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(self.summary_label)

        # ------------------------------------------------------------------
        # Buttons row
        # ------------------------------------------------------------------
        button_row = QHBoxLayout()

        self.restore_btn = QPushButton("Restore Original Grades")
        self.restore_btn.clicked.connect(self.restore_grades)
        button_row.addWidget(self.restore_btn)

        self.add_btn = QPushButton("Add New Course")
        self.add_btn.clicked.connect(self.add_course)
        button_row.addWidget(self.add_btn)

        self.delete_btn = QPushButton("Delete Selected Course")
        self.delete_btn.clicked.connect(self.delete_course)
        button_row.addWidget(self.delete_btn)

        main_layout.addLayout(button_row)

        # Populate the table with the initial course data and update summary.
        self.populate_table()
        self.update_summary()

    # ------------------------------------------------------------------
    # Table and summary helpers
    # ------------------------------------------------------------------
    def populate_table(self) -> None:
        """Fill the QTableWidget with the current list of courses.

        This is called after any operation that changes `self.courses`.
        """
        self.table.setRowCount(len(self.courses))

        for row, course in enumerate(self.courses):
            # Create table items for each column.
            label_item = QTableWidgetItem(course.label)
            title_item = QTableWidgetItem(course.title)
            grade_item = QTableWidgetItem(str(course.grade))
            credits_item = QTableWidgetItem(f"{course.credit_hours:.3f}")

            # Only grade cells are editable by the user directly via double-click.
            label_item.setFlags(label_item.flags() & ~Qt.ItemIsEditable)
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
            credits_item.setFlags(credits_item.flags() & ~Qt.ItemIsEditable)

            self.table.setItem(row, 0, label_item)
            self.table.setItem(row, 1, title_item)
            self.table.setItem(row, 2, grade_item)
            self.table.setItem(row, 3, credits_item)

        # Resize columns to fit their content for better readability.
        self.table.resizeColumnsToContents()

    def update_summary(self) -> None:
        """Recompute statistics and update the summary label text."""
        total_credits, weighted_sum, average = calculate_weighted_average(self.courses)

        # Format the summary string with 3 decimal places for credits and
        # 2 decimal places for the numeric sums.
        self.summary_label.setText(
            f"Total Credits: {total_credits:.3f}    "
            f"Weighted Grade Sum: {weighted_sum:.2f}    "
            f"Average Grade: {average:.2f}"
        )

    def find_course_by_label(self, label: str) -> Course | None:
        """Return the first course matching `label`, or None if not found."""
        for course in self.courses:
            if course.label == label:
                return course
        return None

    # ------------------------------------------------------------------
    # Grade editing and course operations
    # ------------------------------------------------------------------
    def edit_grade(self, row: int, column: int) -> None:
        """Prompt the user to edit the grade for the double-clicked course.

        The dialog appears when the user double-clicks any column in a row,
        but only the grade value is editable.
        """
        # Identify the course by its label (column 0).
        label_item = self.table.item(row, 0)
        if label_item is None:
            return

        label = label_item.text()
        course = self.find_course_by_label(label)
        if course is None:
            return

        current_grade = str(course.grade)

        # Ask the user for the new grade, pre-filled with the current one.
        new_grade, ok = QInputDialog.getText(
            self,
            "Edit Grade",
            f"Enter new grade for {label}:",
            text=current_grade,
        )
        if not ok or not new_grade.strip():
            # User cancelled or left the input empty.
            return

        new_grade = new_grade.strip()

        # Validate that the grade is numeric to keep calculations consistent.
        try:
            float(new_grade)
        except ValueError:
            QMessageBox.critical(self, "Invalid Grade", "Please enter a valid numeric grade.")
            return

        # Update the in-memory Course object.
        course.grade = new_grade

        # Reflect the new grade in the table cell.
        self.table.item(row, 2).setText(str(course.grade))

        # Recompute and display the updated summary statistics.
        self.update_summary()

    def restore_grades(self) -> None:
        """Restore all grades to their original transcript values.

        This reconstructs `self.courses` from `self.original_courses`.
        """
        # Recreate the list of Course objects by cloning the originals.
        self.courses = [
            Course(**self.original_courses[label].to_dict())
            for label in self.original_courses
        ]

        self.populate_table()
        self.update_summary()

    def add_course(self) -> None:
        """Prompt the user to add a new (temporary) course to the table.

        The new course is intended for "what-if" GPA scenarios and is
        labeled as a temporary estimate for location, level, and title.
        """
        text, ok = QInputDialog.getText(
            self,
            "Add Course",
            "Enter course in format: LABEL,GRADE,CREDITS\nExample: CMPT499,85,3",
        )
        if not ok or not text.strip():
            # User cancelled or provided an empty string.
            return

        user_input = text.strip()

        try:
            # Split input by comma and normalize whitespace around each part.
            label, grade, credit_str = [part.strip() for part in user_input.split(",")]

            # Validate that grade and credits are numeric.
            float_grade = float(grade)  # noqa: F841  # used only for validation
            credit_hours = float(credit_str)
        except ValueError:
            QMessageBox.critical(
                self,
                "Invalid Input",
                "Please enter the course in the correct format: LABEL,GRADE,CREDITS",
            )
            return

        # Create a new temporary Course object.
        new_course = Course(
            label=label,
            location="Temporary Estimate",
            level="Temporary Estimate",
            title="Temporary Estimate",
            grade=grade,
            credit_hours=credit_hours,
        )

        # Append to the working list and refresh the table and summary.
        self.courses.append(new_course)
        self.populate_table()
        self.update_summary()

    def delete_course(self) -> None:
        """Delete the currently selected course from the table and list."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Delete Course", "Please select a course to delete.")
            return

        label_item = self.table.item(row, 0)
        if label_item is None:
            return

        label = label_item.text()

        # Confirm with the user before deleting.
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {label}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
            )
        if reply != QMessageBox.Yes:
            return

        # Filter out the course with the matching label from the working list.
        self.courses = [course for course in self.courses if course.label != label]

        # Remove the corresponding row from the table and update the summary.
        self.table.removeRow(row)
        self.update_summary()


if __name__ == "__main__":
    # ------------------------------------------------------------------
    # Locate a transcript PDF in the current working directory.
    # ------------------------------------------------------------------
    def find_pdf_file() -> str | None:
        """Return the first PDF filename found in the current directory.

        If no PDF is found, returns None.
        """
        for file in os.listdir():
            # We only consider files ending with .pdf (case-insensitive).
            if file.lower().endswith(".pdf"):
                return file
        return None

    pdf_file = find_pdf_file()

    if not pdf_file:
        # No transcript file found: exit with an error message and non-zero code.
        print("No PDF file found in the current directory.")
        sys.exit(1)

    # Read and parse the PDF transcript.
    pdf_text = read_pdf(pdf_file)
    courses = parse_courses(pdf_text)

    # Deduplicate by course label, keeping the last occurrence of each.
    unique_courses = deduplicate_courses(courses)

    # Build a mapping of label -> Course representing the original, unmodified
    # transcript state. We clone by going through `to_dict()` to avoid sharing
    # references.
    original_courses = {
        course.label: Course(**course.to_dict()) for course in unique_courses
    }

    # ------------------------------------------------------------------
    # Start the Qt application and show the main window.
    # ------------------------------------------------------------------
    app = QApplication(sys.argv)

    window = MainWindow(unique_courses, original_courses)
    window.resize(900, 600)
    window.show()

    # Start the event loop.
    sys.exit(app.exec())