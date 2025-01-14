# Import packages
import csv
import math
import sys
import string
import random
import pandas as pd
import os
import re
from faker import Faker
from pathlib import Path

# region Variables
studentCount = 1000
currentTerm = 202122
currentSemester = 2

# Default mark distribution for 1st, 2:1, 2:2, 3rd, and Ord class degrees. (See random.choices() weight parameter)
markDistribution = [35, 40, 20, 4, 1]
# Troublesome programmes and courses in XLSX dataset are removed as they are not within the project scope.
bannedKeywords = ["phd", "mdes", "msc", "diploma", "dubai", "malaysia", "ocean", "+ 1 El", "elect", "or ele"]

FLAG_SECOND_YEAR_SLUMP = True
FACTOR_SECOND_YEAR_SLUMP = 0.2
FREQUENCY_SECOND_YEAR_SLUMP = [1, 2, 3]  # Probability is equal to 1 / len(FREQUENCY)

FLAG_INACTIVE_STUDENTS = False
YEAR_COUNT_INACTIVE_STUDENTS = 1  # Maximum value is 17, Value of 1 will allow inactive students from up to 5 years ago

# Keep track of generated ID's to ensure uniqueness
uniqueHWIDs = []
uniqueUserIDs = []

courses = {}
programmes = {}
# endregion


class Programme:

    def __init__(self, row):
        self.mandCourses = {
            1: [[], [], []],
            2: [[], [], []],
            3: [[], [], []],
            4: [[], [], []],
            5: [[], [], []]
        }
        self.optCourses = {
            1: [[], [], []],
            2: [[], [], []],
            3: [[], [], []],
            4: [[], [], []],
            5: [[], [], []]
        }
        try:
            self.PROG_DESC = row[8].strip()
            # TODO: Make CSV include course code, then use this properly
            self.PROG_CODE = row[9].strip()
            self.addCourse(row)
        except Exception as e:
            print("(Programme__inti) Something is wrong with: ", end='')
            print(e)
            print(row)

    def addCourse(self, row):
        try:
            semester = courses[row[1]].PTRM - 1
            year = int(row[5][0])
            if "mandatory" in row[3].lower() and row[1] not in self.mandCourses[year][semester]:
                self.mandCourses[year][semester].append(row[1])
            elif "optional" in row[3].lower() and row[1] not in self.optCourses[year][semester]:
                self.optCourses[year][semester].append(row[1])

        except Exception as e:
            print("(Programme_addCourse) Something is wrong with: ", end='')
            print(e)
            print(row)


class Course:

    def __init__(self, row):
        try:
            self.COURSE_CODE = row[1].strip()
            self.COURSE_TITLE = re.sub(r"\(.*\)", "", row[2]).strip()
            if isinstance(row[4], int):
                self.PTRM = row[4]
            else:
                self.PTRM = int(row[4][0])
            # TODO: Future format of CSV may have credits in its own column. For now its within the description
            creds = re.match(r'^.*?\([^\d]*(\d+\.*\d+)[^\d]*\).*$', row[2])
            if creds and float(creds.group(1)) < 99:
                self.CREDIT_HOURS = float(creds.group(1))
            else:
                self.CREDIT_HOURS = 15.0
        except Exception as e:
            print(e)
            print("(Course__init) Something is wrong in line: /n" + row)


class Student:

    def __init__(self, f):
        self.ESTS_CODE = "EN"  # Language?
        self.ACTIVE_COURSES = []
        self.COMPLETED_COURSES = []
        # Establish what degree class a student is upon creation to generate marks accordingly.
        self.EXPECTED_DEG_CLASS = random.choices([1, 2.1, 2.2, 3, 4], weights=markDistribution)[0]
        self.SLUMPER = random.choice(FREQUENCY_SECOND_YEAR_SLUMP) == 1

        self.__genPersonalInfo(f)
        self.__genCourseInfo()
        # print("\nCreating new year " + str(self.YOS_CODE) + self.PROG_CODE + " student...")
        self.__genCourses()

    def __genPersonalInfo(self, f):
        self.BANNER_ID = genHWUid()
        self.TITLE = random.choices(["Mr", "Ms", "Mrs"], weights=[70, 25, 5])[0]
        if self.TITLE == "Mr":
            self.FIRST_NAME = f.first_name_male()
            if random.randint(1, 10) < 5:
                self.MIDDLE_NAME = f.first_name_male()
            else:
                self.MIDDLE_NAME = ''
        else:
            self.FIRST_NAME = f.first_name_female()
            if random.randint(1, 10) < 5:
                self.MIDDLE_NAME = f.first_name_female()
            else:
                self.MIDDLE_NAME = ''
        self.LAST_NAME = f.last_name()

        if not self.MIDDLE_NAME:
            userInitials = self.FIRST_NAME[0].lower() + self.LAST_NAME[0].lower()
        else:
            userInitials = self.FIRST_NAME[0].lower() + self.MIDDLE_NAME[0].lower() + self.LAST_NAME[0].lower()
        self.USERNAME = genUsername(userInitials)

    def __genCourseInfo(self):
        self.PROG_CODE = random.choice(list(programmes.keys()))
        self.PROG_DESC = programmes[self.PROG_CODE].PROG_DESC

        # Discount picking years on a course where there are no courses
        validYears = []
        for year in programmes[self.PROG_CODE].mandCourses:
            if any(programmes[self.PROG_CODE].mandCourses[year]):
                validYears.append(year)
        for year in programmes[self.PROG_CODE].optCourses:
            if any(programmes[self.PROG_CODE].optCourses[year]):
                validYears.append(year)
        self.YOS_CODE = random.randrange(0, max(validYears)) + 1

        # Deprecated as long as PG programmes are in the bannedProgramme global list
        if "MSc" in self.PROG_DESC or "PhD" in self.PROG_DESC:
            # Check to see which years in a programme actually contain courses
            if self.YOS_CODE != 5:
                self.LEVL_CODE = "UG"
            else:
                self.LEVL_CODE = "PG"
        else:
            self.LEVL_CODE = "UG"

        # Project Scope is limited to Edinburgh Campus Students
        self.CAMP_CODE = "1ED"
        self.CAMP_DESC = "Edinburgh"

        self.ACTIVE_STATUS = "AS"
        self.TERM_CODE = currentTerm
        if FLAG_INACTIVE_STUDENTS and random.choice(range(YEAR_COUNT_INACTIVE_STUDENTS+1)) != 1:
            self.ACTIVE_STATUS = "IS"
            terms = [currentTerm - (i * 101) for i in range(YEAR_COUNT_INACTIVE_STUDENTS)]
            self.TERM_CODE = (random.choice(terms))
            self.YOS_CODE = max(validYears)+1

    def __genCourses(self):
        # Loop through each year and semester, adding all mandatory courses from the students programme.
        for year in programmes[self.PROG_CODE].mandCourses:
            for i in range(len(programmes[self.PROG_CODE].mandCourses[year])):
                if programmes[self.PROG_CODE].mandCourses[year][i] and self.YOS_CODE >= year:
                    self.__addMandatoryCourses(year, i)
        # print(" ¦¦¦ Completed Mandatory Courses: " + str([*self.COMPLETED_COURSES]))

        # Loop through each year and semester, adding optional courses until the sum of a semesters course is 60 credits
        for year in programmes[self.PROG_CODE].optCourses:
            for i in range(len(programmes[self.PROG_CODE].optCourses[year])):
                if programmes[self.PROG_CODE].optCourses[year][i] and self.YOS_CODE >= year:
                    self.__addOptionalCourse(year, i)

    # Adds all mandatory courses from the specified year and semester to active and completed course list.
    def __addMandatoryCourses(self, year, semesterIndex):
        for course in programmes[self.PROG_CODE].mandCourses[year][semesterIndex]:
            if self.YOS_CODE > year:
                self.COMPLETED_COURSES.append((course, self.__generateMark(course)))
            elif self.YOS_CODE == year:
                if semesterIndex == currentSemester-1 and self.ACTIVE_STATUS == "AS":
                    self.ACTIVE_COURSES.append(course)
                elif semesterIndex < currentSemester-1:
                    self.COMPLETED_COURSES.append((course, self.__generateMark(course)))

    # Adds optional courses from the student's programme year and semester until the semester's courses sum 60 credits
    def __addOptionalCourse(self, year, semesterIndex):
        # Troubleshooting print statements
        # print(self.BANNER_ID + " - " + self.PROG_CODE + " Y" + str(self.YOS_CODE))
        # print("Adding optional courses for y" + str(year) + " s" + str(semesterIndex+1) + "...")
        # print("¦¦ Programme Mandatory y" + str(year) + ": " + str(programmes[self.PROG_CODE].mandCourses[year]))
        # print("¦¦ Programme Optional y" + str(year) + ": " + str(programmes[self.PROG_CODE].optCourses[year]))
        # print("¦¦ Courses this semester: " + str(self.getStudentCourses(year, semesterIndex)), end='')

        # Sum credits for already added mandatory courses in this year and semester
        semesterCredits = 0
        if self.YOS_CODE == year and currentSemester == semesterIndex+1:
            for c in self.ACTIVE_COURSES:
                if courses[c].PTRM == semesterIndex + 1:
                    if c in programmes[self.PROG_CODE].optCourses[year][semesterIndex] \
                            or c in programmes[self.PROG_CODE].mandCourses[year][semesterIndex]:
                        semesterCredits += courses[c].CREDIT_HOURS
        else:
            for c in self.COMPLETED_COURSES:
                if courses[c[0]].PTRM == semesterIndex + 1:
                    if c[0] in programmes[self.PROG_CODE].optCourses[year][semesterIndex] \
                            or c[0] in programmes[self.PROG_CODE].mandCourses[year][semesterIndex]:
                        semesterCredits += courses[c[0]].CREDIT_HOURS

        while semesterCredits < 60:
            # Pick an optional course at random, as long as it isn't already in the students course list
            course = random.choice(programmes[self.PROG_CODE].optCourses[year][semesterIndex])
            while course in self.COMPLETED_COURSES or course in self.ACTIVE_COURSES:
                course = random.choice(programmes[self.PROG_CODE].optCourses[year][semesterIndex])

            # Add optional courses for each year up until active year, then add to active course list.
            if self.YOS_CODE > year:
                self.COMPLETED_COURSES.append((course, self.__generateMark(course)))
                semesterCredits += courses[course].CREDIT_HOURS
            elif self.YOS_CODE == year:
                if semesterIndex == currentSemester-1 and self.ACTIVE_STATUS == "AS":
                    self.ACTIVE_COURSES.append(course)
                    semesterCredits += courses[course].CREDIT_HOURS
                elif semesterIndex < currentSemester-1:
                    self.COMPLETED_COURSES.append((course, self.__generateMark(course)))
                    semesterCredits += courses[course].CREDIT_HOURS

    # Generates a random mark within the expected degree range +-margin and has a 1/3 chance of +-20% in 1st and
    # 2nd year respectively, this is to simulate students with previous experience who excel in first year and pull
    # back in second year due to building bad habits for university study or burnout.
    def __generateMark(self, course):
        deg = self.EXPECTED_DEG_CLASS
        margin = 4
        year = findYearForCourse(self.PROG_CODE, course)
        if deg == 1:
            # 1st class students have a 1/5 chance of getting 90+
            if random.randrange(1, 5) == 1:
                mark = random.randrange(90, 100)
            else:
                mark = random.randrange(70-margin, 80+margin)
        elif deg == 2.1:
            mark = random.randrange(60-margin, 70+margin)
        elif deg == 2.2:
            mark = random.randrange(50-margin, 60+margin)
        elif deg == 3:
            mark = random.randrange(40-margin, 50+margin)
        elif deg == 4:
            mark = random.randrange(10-margin, 40+margin)
        else:
            mark = 0

        # Apply Second Year Slump factor to first and second year marks for some students
        if FLAG_SECOND_YEAR_SLUMP and self.SLUMPER:
            if year == 1:
                mark += mark * FACTOR_SECOND_YEAR_SLUMP
            elif year == 2:
                mark -= mark * FACTOR_SECOND_YEAR_SLUMP
        return math.trunc(min(mark, 100))

    def getStudentCourses(self, year, semesterIndex):
        courseList = []
        for c in self.COMPLETED_COURSES:
            if courses[c[0]].PTRM == semesterIndex + 1:
                if c[0] in programmes[self.PROG_CODE].optCourses[year][semesterIndex] \
                        or c[0] in programmes[self.PROG_CODE].mandCourses[year][semesterIndex]:
                    courseList.append(c[0])
        for c in self.ACTIVE_COURSES:
            if courses[c].PTRM == semesterIndex + 1:
                if c in programmes[self.PROG_CODE].optCourses[year][semesterIndex] \
                        or c in programmes[self.PROG_CODE].mandCourses[year][semesterIndex]:
                    courseList.append(c)
        return courseList


def genHWUid():
    hwid = "H00" + str(random.randrange(100000, 400000))
    if hwid not in uniqueHWIDs:
        uniqueHWIDs.append(hwid)
    else:
        hwid = genHWUid()
    return hwid


def genUsername(userInitials):
    n = random.randrange(1, 100)
    username = userInitials + str(n)
    if username not in uniqueUserIDs:
        return username
    else:
        genUsername(userInitials)


def writeCSV(header, studentList):
    with open("f2(0.2,1div3).csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for student in studentList:
            # Define list of attributes to fetch from the Course object
            courseHeaders = ["course", "ptrm", "credit_hours"]
            programmeHeaders = ["yos_code"]
            # Iterate through the student's completed courses (has PERC attribute associated) and write to file
            for course in student.COMPLETED_COURSES:
                line = []
                for column in header:
                    # If the header's data is stored in the course object, fetch it from the course object
                    if bool([x for x in courseHeaders if (x in column.lower())]):
                        line.append(str(getattr(courses[course[0]], column, "")))
                    # If the header is YOS_CODE, find what year of the students programme this course belongs to
                    elif bool([x for x in programmeHeaders if (x in column.lower())]):
                        line.append(str(findYearForCourse(student.PROG_CODE, course[0])))
                    elif column == "PERC":
                        line.append(course[1])
                    elif column == "GRADE":
                        line.append(assignGrade(course[1]))
                    elif column == "TERM_CODE":
                        i = student.YOS_CODE - findYearForCourse(student.PROG_CODE, course[0])
                        line.append(student.TERM_CODE - (101 * i))
                    elif column == "ROLL_DATE":
                        i = student.YOS_CODE - findYearForCourse(student.PROG_CODE, course[0])
                        term = str(student.TERM_CODE - (101 * i))
                        if courses[course[0]].PTRM == 1:
                            date = "31-Oct-" + term[:4]
                        elif courses[course[0]].PTRM == 2:
                            date = "28-Jan-" + term[:2] + term[-2:]
                        else:
                            date = "25-May-" + term[:2] + term[-2:]
                        line.append(date)
                    # TODO: Account for failing a course and resitting (i.e more than one attempt)
                    elif column == "OPPORTUNITY":
                        line.append("1")
                    elif column == "RESIT_FLAG":
                        line.append("N")
                    else:  # If not any of the above, fetch it from the student object
                        line.append(str(getattr(student, column, "")))
                writer.writerow(line)

            #  Iterate through the currently active courses (no PERC attribute) and write to file
            for course in student.ACTIVE_COURSES:
                line = []
                for column in header:
                    # If the header's data is stored in the course object, fetch it from the course object
                    if bool([x for x in courseHeaders if (x in column.lower())]):
                        line.append(str(getattr(courses[course], column, "")))
                    # If the header is YOS_CODE, find what year of the students programme this course belongs to
                    elif bool([x for x in programmeHeaders if (x in column.lower())]):
                        line.append(str(findYearForCourse(student.PROG_CODE, course)))
                    elif column == "ROLL_DATE":
                        if courses[course].PTRM == 1:
                            date = "31-Oct-" + str(student.TERM_CODE)[:4]
                        elif courses[course].PTRM == 2:
                            date = "28-Jan-" + str(student.TERM_CODE)[:2] + str(student.TERM_CODE)[-2:]
                        else:
                            date = "25-May-" + str(student.TERM_CODE)[:2] + str(student.TERM_CODE)[-2:]
                        line.append(date)
                    else:  # If not, fetch it from the student object
                        line.append(str(getattr(student, column, "")))
                writer.writerow(line)


# Helper function to check a programmes course dictionaries to find what year of study it belongs to
def findYearForCourse(programmeCode, courseCode):
    programme = programmes[programmeCode]
    course = courses[courseCode]
    for year in programme.mandCourses:
        if course.COURSE_CODE in programme.mandCourses[year][course.PTRM-1]:
            return year
    for year in programme.optCourses:
        if course.COURSE_CODE in programme.optCourses[year][course.PTRM-1]:
            return year


# Helper function to calculate grade based on percentage mark
def assignGrade(mark):
    if mark >= 70:
        return 'A'
    elif mark >= 60:
        return 'B'
    elif mark >= 50:
        return 'C'
    elif mark >= 40:
        return 'D'
    elif mark >= 30:
        return 'E'
    else:
        return 'F'


def readHeaders(filename: string):
    header = []
    with open(filename, "r") as file:
        h = csv.reader(file)
        for row in h:
            for element in row:
                header.append(element.strip())
    return header


def readProgrammes(fileName: string):
    # Read xlsx and write to csv
    curDir = os.getcwd()
    df = pd.ExcelFile(fileName)
    for sheet in df.sheet_names:
        if "raw" not in sheet.lower():
            df.parse(sheet_name=sheet).to_csv("programmes\\" + sheet + ".csv")

    # Read csv
    os.chdir("programmes")
    for file in os.listdir():
        if file.endswith(".csv"):
            file_path = Path(file)
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    try:
                        if row[0] != "":
                            # Add courses to a dictionary of CourseCode: CourseObject
                            courseCode = row[1]
                            progCode = row[9].strip()
                            if courseCode not in courses and re.match(r'[A-Z]+[0-9]{2}[A-Z]{2}', courseCode):
                                courses[courseCode] = Course(row)
                            elif courseCode == "1 SCQ":
                                break

                            # Add Programmes to a dictionary of ProgCode: ProgrammeObject
                            if not bool([x for x in bannedKeywords if x.lower() in row[8].lower()]
                                        + [x for x in bannedKeywords if x.lower() in row[1].lower()]):
                                if progCode not in programmes:
                                    p = Programme(row)
                                    programmes[progCode] = p
                                else:
                                    programmes[progCode].addCourse(row)
                    except Exception as e:
                        print("(CSV Reader) Something is wrong with: ", end='')
                        print(e)
                        print(row)
    os.chdir(curDir)


if __name__ == '__main__':
    students = []
    headers = readHeaders(sys.argv[1])
    readProgrammes("ProgrammeData.xlsx")

    # region Test Print Output
    # # Print programme List
    # for prog in [*programmes.values()]:
    #     print(prog.PROG_CODE + " ¦¦¦ " + prog.PROG_DESC)
    #     for yearKey in prog.mandCourses:
    #         if any(prog.mandCourses[yearKey]) or any(prog.optCourses[yearKey]):
    #             print("Year " + str(yearKey))
    #             print(prog.mandCourses[yearKey])
    #             print(prog.optCourses[yearKey])
    #     print("################################################## \n")

    # # Print course List
    # for e in [*courses.values()]:
    #     for attribute in (e.__dict__.keys()):
    #         print(str(attribute) + ": " + str(getattr(e, attribute)), end=" ¦ ")
    #     print('')

    # Print student list
    # for s in students:
    #     if (len(s.COMPLETED_COURSES) % 4) != 0:
    #         # for attribute in (s.__dict__.keys()):
    #         #    print(str(attribute) + ":" + str(getattr(s, attribute)), end=" ¦\t")
    #         print('')
    #         print(s.BANNER_ID + " (" + s.PROG_CODE + " Y" + str(s.YOS_CODE) + "): \nActiveCourses:" +
    #               str(s.ACTIVE_COURSES) + "\nCompleted Courses (" + str(len(s.COMPLETED_COURSES)) + ") :"
    #               + str(s.COMPLETED_COURSES))
    #         # print("¦¦ Programme Mandatory y" + str(s.YOS_CODE) + ": " +
    #         #       str(programmes[s.PROG_CODE].mandCourses[s.YOS_CODE]))
    #         # print("¦¦ Programme Optional y" + str(s.YOS_CODE) + ": " +
    #         #       str(programmes[s.PROG_CODE].optCourses[s.YOS_CODE]))
    #         print('')

    # endregion

    faker = Faker(["en_GB"])
    for j in range(studentCount):
        s = Student(faker)
        students.append(s)
        # print(s.EXPECTED_DEG_CLASS, s.LAST_NAME)
    writeCSV(headers, students)
