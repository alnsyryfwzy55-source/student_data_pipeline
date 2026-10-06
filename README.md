# Student Data Pipeline

## Project Overview
A Python Data Engineering ETL pipeline that combines student data from five heterogeneous sources and produces both an analysis-ready dataset and a machine-learning-ready feature table:

1. CSV (`data/raw/students.csv`)
2. REST API / JSON (`data/raw/api_mock.json` fallback)
3. SQLite (`database/students.db`)
4. MongoDB (`data/raw/mongodb_students.json` fallback)
5. Web scraping (`data/raw/students_web.html` fallback)

## Architecture
```text
CSV ──────────┐
REST API ─────┤
SQLite ───────┼─> Extract -> Validate -> Clean -> Integrate -> Transform
MongoDB ──────┤                                                  |
Web scraping ─┘                                                  v
                                                          Final Validation
                                                     /          |          \
                                                    v           v           v
                                         final_dataset.csv  rejected_    ml_ready_dataset.csv
                                                           records.csv   + feature_schema.json
```

## Project Structure
```text
student_data_pipeline/
├── app/
│   ├── sources/          csv, api, database, mongodb, web scraper
│   ├── validation/       per-source and final quality rules
│   ├── transformation/   cleaning, integration, derived columns
│   ├── ml/               ML-ready feature preparation
│   ├── output/           CSV writers
│   └── utils/            logger
├── data/
│   ├── raw/              source files and offline fixtures
│   ├── processed/        final_dataset.csv        (generated)
│   ├── rejected/         rejected_records.csv     (generated)
│   └── ml/               ml_ready_dataset.csv, feature_schema.json (generated)
├── database/             students.db (SQLite)
├── docs/                 data_dictionary.md
├── scripts/              seed_mongodb.py
├── tests/
├── .github/workflows/    CI
├── docker-compose.yml    local MongoDB
├── .env.example
├── main.py
└── requirements.txt
```

## Data Sources
| Source | Provides | Live configuration | Offline fallback |
|---|---|---|---|
| CSV | name, age, major, city | file | - |
| REST API | gpa, attendance, status | `API_URL` | `data/raw/api_mock.json` |
| SQLite | courses, semester, score (SQL JOIN) | file | - |
| MongoDB | credit_hours, enrollment_status | `MONGO_URI`, `MONGO_DATABASE`, `MONGO_COLLECTION` | `data/raw/mongodb_students.json` |
| Web scraping | scholarship (HTML table via BeautifulSoup) | `WEB_SOURCE_URL` | `data/raw/students_web.html` |

When a live source is not configured or fails, the pipeline logs it and uses the local fixture, so runs are reproducible offline. Credentials are only read from environment variables (see `.env.example`); never commit them.

### Running MongoDB locally (optional)
```bash
docker compose up -d
export MONGO_URI=mongodb://localhost:27017
python scripts/seed_mongodb.py
python main.py
```

## ETL Pipeline
- **Extract:** CSV, REST API, SQLite query, MongoDB, HTML table.
- **Validate:** per-source rules (below) plus a final gate; rejected rows are never dropped silently.
- **Clean:** normalise text, majors (e.g. `AI` -> `Artificial Intelligence`), types and missing values.
- **Integrate:** CSV, API and SQLite are required (inner join on `student_id`); MongoDB and web data are enrichment (left join), so a student missing from them is kept. Overlapping web columns are compared with the CSV (conflicts are logged) instead of duplicated.
- **Transform:** `performance_level`, `attendance_status`, `academic_load`.
- **ML preparation:** see below.
- **Load:** final, rejected and ML-ready files.

## Data Quality Rules
- `student_id` cannot be NULL and must be unique within each source (first record kept).
- `age` 16-80, `gpa` 0-4, `attendance` 0-100, `score` 0-100, `credit_hours` 0-30.
- A student valid in some required sources but missing from others is rejected as `Incompatible student_id`.
- Final gate: any row failing the range rules is written to the rejected file with the reason.
- `rejected_records.csv` columns: `student_id`, `source`, `error_reason`.

## Missing Values
- Missing age: median of valid ages in the student source (stored as integer).
- Missing GPA: median of valid GPA values from the API source.
- Missing attendance or score is not fabricated; such a row is rejected by the final validation.
- Missing MongoDB/web data leaves `credit_hours`, `enrollment_status`, `scholarship` empty (enrichment only).

## ML-Ready Output
`data/ml/ml_ready_dataset.csv` is fully numeric with no missing values:
- identifiers (`student_id`, `student_name`) removed;
- `gpa` removed because the target `performance_level` is derived from it (target leakage);
- numeric features standardised (z-score); the means/standard deviations are saved in `data/ml/feature_schema.json` so new data can be scaled identically;
- categoricals one-hot encoded, `course` expanded to one column per course, `scholarship` as 0/1.

Note: the bundled sample is tiny (7 rows) and only demonstrates the format; train/test splitting should be done on real data volumes. Column descriptions: `docs/data_dictionary.md`.

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
Tests write pipeline outputs to a temporary directory and do not modify the repository. CI runs them on every push.

## Output
- `data/processed/final_dataset.csv`
- `data/rejected/rejected_records.csv`
- `data/ml/ml_ready_dataset.csv`, `data/ml/feature_schema.json`
- `logs/pipeline.log`

(Generated files are git-ignored.)

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
حتى تبقى مسؤولية كل طبقة واضحة ويمكن تغيير مصدر البيانات أو إضافة مصدر جديد (مثل MongoDB أو Web Scraping) دون إعادة كتابة منطق التنظيف والتحويل.

### 9. لماذا يعتبر Validation Data جزءًا أساسيًا من هندسة البيانات؟
لأن جودة البيانات الداخلة تؤثر مباشرة على صحة التحليل والنماذج والقرارات المبنية عليها.
### 10. كيف يمكن تطوير Pipeline ليعمل بشكل دوري وآلي؟
يمكن تشغيله بواسطة scheduler مثل cron أو Windows Task Scheduler أو نظام orchestration.

### 11. كيف يمكن جعل Pipeline يتعامل مع ملايين السجلات؟
باستخدام المعالجة على دفعات، القراءة الجزئية، قواعد بيانات مناسبة، parallelism عند الحاجة، ومراقبة الذاكرة والأداء.

### 12. ما الفرق بين Processing Batch وProcessing Streaming؟
Batch يعالج مجموعة من البيانات على دفعات، بينما Streaming يعالج البيانات أثناء وصولها بصورة مستمرة أو شبه فورية.

### 13. لماذا لا نضع MongoDB credentials مباشرة في الكود؟

لأسباب أمنية وللفصل بين configuration وsource code. يتم استخدام environment variables مثل `MONGO_URI` حتى لا تظهر بيانات الاتصال الحساسة في Git أو GitHub.

### 14. لماذا يمكن أن يكون تنظيف Web Scraping مختلفًا عن تنظيف MongoDB؟

لأن كل مصدر قد يحتوي على اختلافات في schema وdata types وformatting. لذلك يمكن أن توجد source-specific cleaning functions، ثم يتم توحيد البيانات قبل مرحلة integration.

### 13. لماذا لا نضع MongoDB credentials مباشرة في الكود؟
لأسباب أمنية وللفصل بين configuration وsource code. يتم استخدام environment variables مثل `MONGO_URI` حتى لا تظهر بيانات الاتصال الحساسة في Git أو GitHub.

### 14. لماذا يمكن أن يكون تنظيف Web Scraping مختلفًا عن تنظيف MongoDB؟
لأن كل مصدر قد يحتوي على اختلافات في schema وdata types وformatting. لذلك توجد source-specific cleaning functions، ثم يتم توحيد البيانات قبل مرحلة integration.

## Design Notes
Source extraction, validation, transformation, integration, ML preparation and output are separate modules, so an additional source can be introduced without rewriting the pipeline.
