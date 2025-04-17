# courses.py

"""
This module defines the Course class, which represents an academic course with attributes such as label, location, level, title, grade, and credit hours.
The Course class provides methods to access and modify these attributes, check if the course has been passed, and convert the course information to a dictionary format.
"""

from dataclasses import dataclass

@dataclass
class Course:
    label: str             # e.g., "CMPT306"
    location: str          # e.g., "Main Campus"
    level: str             # e.g., "Undergraduate"
    title: str             # e.g., "Game Development"
    grade: str             # e.g., "85" for percentage, "TR" for transfer credit, "W" for withdrawal
    credit_hours: float    # e.g., 3.0

    def get_label(self) -> str:
        """Return the label of the course."""
        return self.label

    def get_location(self) -> str:
        """Return the location of the course."""
        return self.location

    def get_level(self) -> str:
        """Return the level of the course."""
        return self.level

    def get_title(self) -> str:
        """Return the title of the course."""
        return self.title

    def get_grade(self) -> str:
        """Return the grade received in the course."""
        return self.grade

    def get_credit_hours(self) -> float:
        """Return the number of credit hours for the course."""
        return self.credit_hours

    def set_label(self, label: str) -> None:
        """Set the label of the course."""
        self.label = label

    def set_location(self, location: str) -> None:
        """Set the location of the course."""
        self.location = location

    def set_level(self, level: str) -> None:
        """Set the level of the course."""
        self.level = level

    def set_title(self, title: str) -> None:
        """Set the title of the course."""
        self.title = title

    def set_grade(self, grade: str) -> None:
        """Set the grade received in the course."""
        self.grade = grade

    def set_credit_hours(self, credit_hours: float) -> None:
        """Set the number of credit hours for the course."""
        self.credit_hours = credit_hours

    def is_passed(self, passing_grade: float = 50.0) -> bool:
        """Return True if the grade is above the passing threshold.

        Grades "TR" (transfer credit) and "W" (withdrawal) are treated as non-failing.
        If the grade is a numeric value, it checks if it meets or exceeds the passing grade.
        """
        if self.grade == "TR" or self.grade == "W":  # TR or W are treated as non-failing
            return True
        try:
            return float(self.grade) >= passing_grade
        except ValueError:  # if grade is not a number (e.g., TR, W)
            return False

    def to_dict(self) -> dict:
        """Return a dictionary representation of the course."""
        return {
            "label": self.label,
            "location": self.location,
            "level": self.level,
            "title": self.title,
            "grade": self.grade,
            "credit_hours": self.credit_hours
        }

    def __str__(self) -> str:
        """Return a string representation of the course."""
        return (f"{self.label} - {self.title} ({self.level}, {self.location}): "
                f"{self.grade} | {self.credit_hours} Credit Hours")

# Example usage
if __name__ == "__main__":
    example_course = Course(
        label="CMPT 306",
        location="USask - Main,Saskatoon,Campus",
        level="UG",
        title="Game Development",
        grade="92",
        credit_hours=3.0
    )

    print(example_course)
    print("Passed:", example_course.is_passed())