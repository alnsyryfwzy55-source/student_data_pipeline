# Student Data Pipeline

## Project Overview
A Python Data Engineering ETL/Integration pipeline that combines student data from:
1. CSV
2. REST API (with a local JSON mock fallback)
3. SQLite

The pipeline extracts, validates, cleans, integrates, transforms, performs final validation, and loads the final dataset.

## Architecture
```text
CSV ───────┐
API ───────┼──> Extract -> Validate -> Clean -> Integrate -> Transform
SQLite ────┘                                      |
                                                   v
                                           Final Validation
                                             /          \
                                            v            v
                                 final_dataset.csv  rejected_records.csv
```

## Project Structure
```text
student_data_pipeline/
├── app/
│   ├── sources/
│   ├── transformation/
│   ├── validation/
│   ├── output/
│   └── utils/
├── data/
│   ├── raw/
│   ├── processed/
│   └── rejected/
├── database/
├── tests/
├── logs/
├── main.py
├── requirements.txt
└── README.md
```

## Data Sources
### CSV
`data/raw/students.csv` contains basic student information.

### REST API
`app/sources/api_source.py` supports a real REST endpoint using `requests`.  
For offline/reproducible execution, the project includes `data/raw/api_mock.json`.

### SQLite
`database/students.db` contains `courses` and `enrollments`. Data is extracted using SQL JOIN.

## ETL Pipeline
- **Extract:** read CSV, request JSON API, query SQLite.
- **Validate:** enforce student ID, age, GPA, attendance and score rules.
- **Clean:** normalize text, whitespace and data types; apply documented missing-value strategies.
- **Integrate:** join sources using `student_id`.
- **Transform:** create `performance_level` and `attendance_status`.
- **Load:** write final and rejected CSV files.

## Data Quality Rules
- `student_id` cannot be NULL.
- `student_id` must be unique within the student source.
- `age` must be 16–80.
- `gpa` must be 0–4.
- `attendance` must be 0–100.
- `score` must be 0–100.
- IDs must be compatible across sources.
- Invalid records are written to `data/rejected/rejected_records.csv`.

## Missing Values
- Missing student age: median of the available valid ages in the student source.
- Missing GPA: median of available valid GPA values from the API source.
- Missing attendance is not silently fabricated; a missing attendance value cannot pass final validation.

## Installation
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/WSL:
source .venv/bin/activate

pip install -r requirements.txt
```

## Running
```bash
python main.py
```

## Tests
```bash
pytest -q
```

## Output
- `data/processed/final_dataset.csv`
- `data/rejected/rejected_records.csv`
- `logs/pipeline.log`

## Questions
### 1. لماذا نحتاج إلى Pipeline Data عند التعامل مع مصادر متعددة؟
لأن البيانات موزعة بين مصادر مختلفة وتحتاج إلى عملية موحدة وقابلة للتكرار للاستخراج والتحقق والتنظيف والدمج قبل استخدامها في التحليل أو الذكاء الاصطناعي.

### 2. ما الفرق بين Data Raw وData Processed؟
Raw هي البيانات كما وصلت من المصدر، بينما Processed هي البيانات التي خضعت للتنظيف والتحويل والتحقق وأصبحت جاهزة للاستخدام.

### 3. ما الفرق بين Extract وTransform وLoad؟
Extract استخراج البيانات من المصادر، Transform تحويلها وتنظيفها ودمجها، وLoad حفظ الناتج في الوجهة المطلوبة.

### 4. ما المشاكل التي واجهتها أثناء دمج البيانات؟
اختلاف جودة القيم، التكرارات، القيم المفقودة، والقيم غير الصالحة، إضافة إلى ضرورة التأكد من توافق `student_id` بين المصادر.

### 5. كيف تعاملت مع Values Missing؟
تم استخدام Median للعمر وGPA وفق استراتيجية موثقة، بينما القيم التي تمنع اجتياز قواعد الجودة لا يتم تمريرها إلى الناتج النهائي.

### 6. كيف تعاملت مع Records Duplicate؟
يتم الاحتفاظ بأول سجل للطالب وتسجيل التكرار كسجل مرفوض.

### 7. كيف تعاملت مع Records Invalid؟
يتم اكتشافها بقواعد الجودة وتسجيل سبب الرفض في `rejected_records.csv`.

### 8. لماذا يجب فصل طبقة Extraction عن Transformation؟
حتى تبقى مسؤولية كل طبقة واضحة ويمكن تغيير مصدر البيانات دون إعادة كتابة منطق التنظيف والتحويل.

### 9. لماذا يعتبر Validation Data جزءًا أساسيًا من هندسة البيانات؟
لأن جودة البيانات الداخلة تؤثر مباشرة على صحة التحليل والنماذج والقرارات المبنية عليها.

### 10. كيف يمكن تطوير Pipeline ليعمل بشكل دوري وآلي؟
يمكن تشغيله بواسطة scheduler مثل cron أو Windows Task Scheduler أو نظام orchestration.

### 11. كيف يمكن جعل Pipeline يتعامل مع ملايين السجلات؟
باستخدام المعالجة على دفعات، القراءة الجزئية، قواعد بيانات مناسبة، parallelism عند الحاجة، ومراقبة الذاكرة والأداء.

### 12. ما الفرق بين Processing Batch وProcessing Streaming؟
Batch يعالج مجموعة من البيانات على دفعات، بينما Streaming يعالج البيانات أثناء وصولها بصورة مستمرة أو شبه فورية.

## Design Notes
The implementation keeps source extraction, validation, transformation, integration and output responsibilities separated so that an additional source can be introduced without rewriting the entire pipeline.
