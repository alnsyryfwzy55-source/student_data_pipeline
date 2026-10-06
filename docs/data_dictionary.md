# Data Dictionary

## `final_dataset.csv`
| Column | Source | Type | Description |
|---|---|---|---|
| student_id | all | int | Join key |
| student_name, major, city | CSV | text | Normalised text (`city` title-cased, `AI` -> `Artificial Intelligence`) |
| age | CSV | int | 16-80; missing values imputed with the median |
| gpa | API | float | 0-4; missing values imputed with the median |
| attendance | API | float | Percentage 0-100 |
| status | API | text | Active / Probation |
| course | SQLite | text | Courses taken, joined with `; ` |
| score | SQLite | float | Mean enrollment score 0-100 |
| semester | SQLite | text | Semesters, joined with `; ` |
| credit_hours | MongoDB | int | Credit hours this term (0-30) |
| enrollment_status | MongoDB | text | Active / Probation |
| scholarship | Web | bool | Whether the student has a scholarship |
| performance_level | derived | category | From GPA: <2.0 At Risk, <2.5 Acceptable, <3.0 Good, <3.5 Very Good, else Excellent |
| attendance_status | derived | category | `Good` if attendance >= 75 else `Low` |
| academic_load | derived | category | `Full` if credit_hours >= 12 else `Part-time` |

## `rejected_records.csv`
`student_id`, `source` (csv, api, database, mongodb, web, integration, final_validation), `error_reason`.

## `ml_ready_dataset.csv`
Target: `performance_level`. Features: z-scored `age`, `attendance`, `score`, `credit_hours`; `scholarship` (0/1); one-hot columns prefixed `major_`, `city_`, `status_`, `enrollment_status_`, `attendance_status_`, `academic_load_`; one column per course (`course_*`). `gpa`, `student_id` and `student_name` are excluded. Scaling parameters are in `feature_schema.json`.
