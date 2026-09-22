# Student Result Management System

A web-based Student Result Management System built using **Python Flask, SQLite, Jinja2, and Bootstrap 5**. The system provides separate functionality for administrators to manage students and marks, and allows students to publicly search and view their results using their Student ID.

## Features

### Admin Features
- Secure admin login and logout
- Add new students
- Edit student details
- Delete students
- Add subject-wise marks
- Edit marks
- Delete marks
- Automatic result calculation
- Pass/Fail status calculation
- Grade calculation
- Failed-subject identification

### Student Features
- Public result search without login
- Search result using Student ID
- View student details
- View subject-wise marks
- View total marks
- View percentage
- View grade
- View Pass/Fail status
- View failed subjects when applicable

## Result Calculation

### Percentage

Percentage is calculated using:

```text
Percentage = (Total Marks Obtained / Total Maximum Marks) × 100
