# Data Portal API Guide

Base URL: `http://localhost:8001`

## Public Endpoints (No Authentication Required)

These endpoints are for the public-facing UI to display programs, scholarships, conferences, and exchanges.

---

### Programs

#### List All Programs
```
GET /api/public/programs
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| page_size | int | 20 | Items per page (max 100) |

**Example Request:**
```bash
curl "http://localhost:8001/api/public/programs?page=1&page_size=10"
```

**Example Response:**
```json
{
  "items": [
    {
      "id": "b3747a8b-da28-4866-b92a-3b10fbfcbf3e",
      "type": "PROGRAM",
      "data": {
        "program_name": "Master of Science in Computer Science",
        "description": "The MS in Computer Science program prepares students...",
        "duration_months": 24,
        "gpa_minimum": 3.0,
        "tuition_usd": 55000
      },
      "tags": null,
      "updated_at": "2026-02-01T11:14:17.564619+02:00"
    }
  ],
  "total": 16,
  "page": 1,
  "page_size": 10,
  "total_pages": 2
}
```

#### Get Single Program
```
GET /api/public/programs/{program_id}
```

**Example Request:**
```bash
curl "http://localhost:8001/api/public/programs/b3747a8b-da28-4866-b92a-3b10fbfcbf3e"
```

#### Get Program Filter Options
```
GET /api/public/programs/filters/options
```

Returns available filter values (countries, fields, degree types, etc.)

---

### Scholarships

#### List All Scholarships
```
GET /api/public/scholarships
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| page_size | int | 20 | Items per page (max 100) |

**Example Request:**
```bash
curl "http://localhost:8001/api/public/scholarships?page=1&page_size=10"
```

**Example Response:**
```json
{
  "items": [
    {
      "id": "uuid-here",
      "type": "SCHOLARSHIP",
      "data": {
        "scholarship_name": "Fulbright Scholarship",
        "provider": "U.S. Department of State",
        "deadline": "2026-10-01",
        "monthly_stipend_usd": 2000,
        "covers_tuition": true
      },
      "tags": null,
      "updated_at": "2026-02-01T11:14:17.564619+02:00"
    }
  ],
  "total": 0,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

#### Get Single Scholarship
```
GET /api/public/scholarships/{scholarship_id}
```

#### Get Scholarship Filter Options
```
GET /api/public/scholarships/filters/options
```

---

### Conferences

#### List All Conferences
```
GET /api/public/conferences
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| page_size | int | 20 | Items per page (max 100) |

**Example Request:**
```bash
curl "http://localhost:8001/api/public/conferences?page=1&page_size=10"
```

**Example Response:**
```json
{
  "items": [
    {
      "id": "uuid-here",
      "type": "CONFERENCE",
      "data": {
        "conference_name": "IEEE Conference on AI",
        "start_date": "2026-06-15",
        "end_date": "2026-06-18",
        "city": "San Francisco",
        "country": "USA",
        "submission_deadline": "2026-03-01"
      },
      "tags": null,
      "updated_at": "2026-02-01T11:14:17.564619+02:00"
    }
  ],
  "total": 0,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

#### Get Single Conference
```
GET /api/public/conferences/{conference_id}
```

#### Get Conference Filter Options
```
GET /api/public/conferences/filters/options
```

---

### Exchanges

#### List All Exchanges
```
GET /api/public/exchanges
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| page_size | int | 20 | Items per page (max 100) |

**Example Request:**
```bash
curl "http://localhost:8001/api/public/exchanges?page=1&page_size=10"
```

**Example Response:**
```json
{
  "items": [
    {
      "id": "1f298e3b-bdec-4515-a492-f86320fa036b",
      "type": "EXCHANGE",
      "data": {
        "name": "International Exchange Programs",
        "description": "Partner universities in 15 European countries...",
        "gpa_minimum": 3.0,
        "deadline": "october 1"
      },
      "tags": null,
      "updated_at": "2026-02-01T11:14:17.564619+02:00"
    }
  ],
  "total": 16,
  "page": 1,
  "page_size": 10,
  "total_pages": 2
}
```

#### Get Single Exchange
```
GET /api/public/exchanges/{exchange_id}
```

#### Get Exchange Filter Options
```
GET /api/public/exchanges/filters/options
```

---

### Search

#### Search Across All Types
```
GET /api/public/search
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | string | required | Search query |
| type | string | null | Filter by type: PROGRAM, SCHOLARSHIP, CONFERENCE, EXCHANGE |
| page | int | 1 | Page number |
| page_size | int | 20 | Items per page |

**Example Request:**
```bash
curl "http://localhost:8001/api/public/search?q=computer+science&type=PROGRAM"
```

#### Get Search Statistics
```
GET /api/public/search/stats
```

Returns counts by type and other statistics.

---

## Data Field Reference

### Program Fields
| Field | Type | Description |
|-------|------|-------------|
| program_name | string | Name of the program |
| degree_type | enum | BSC, MSC, PHD, CERTIFICATE, DIPLOMA |
| field | string | Field of study |
| field_category | enum | STEM, BUSINESS, ARTS, MEDICINE, LAW, SOCIAL_SCIENCES, OTHER |
| university_name | string | Name of the university |
| department | string | Department name |
| country | string | Country |
| city | string | City |
| duration_months | number | Program duration |
| format | enum | FULL_TIME, PART_TIME, ONLINE, HYBRID |
| language | string | Language of instruction |
| gpa_requirement | number | Minimum GPA (4.0 scale) |
| tuition_total_usd | number | Total tuition cost |
| tuition_per_year_usd | number | Yearly tuition |
| fall_deadline | date | Fall application deadline |
| spring_deadline | date | Spring application deadline |
| application_url | url | Application link |
| program_url | url | Program page link |
| description | text | Program description |

### Scholarship Fields
| Field | Type | Description |
|-------|------|-------------|
| scholarship_name | string | Name of the scholarship |
| provider | string | Organization providing the scholarship |
| provider_type | enum | GOVERNMENT, UNIVERSITY, PRIVATE, NGO, OTHER |
| eligible_countries | array | List of eligible countries |
| eligible_fields | array | List of eligible fields |
| covers_tuition | boolean | Covers tuition or not |
| monthly_stipend_usd | number | Monthly stipend amount |
| funding_amount_usd | number | Total funding amount |
| deadline | date | Application deadline |
| application_url | url | Application link |
| description | text | Scholarship description |

### Conference Fields
| Field | Type | Description |
|-------|------|-------------|
| conference_name | string | Name of the conference |
| acronym | string | Conference acronym |
| field | string | Field/topic |
| start_date | date | Start date |
| end_date | date | End date |
| submission_deadline | date | Paper submission deadline |
| city | string | City |
| country | string | Country |
| is_virtual | boolean | Virtual conference |
| registration_fee_usd | number | Registration fee |
| website_url | url | Conference website |
| description | text | Conference description |

### Exchange Fields
| Field | Type | Description |
|-------|------|-------------|
| program_name | string | Name of the exchange program |
| program_type | enum | ERASMUS, BILATERAL, SUMMER, SEMESTER, YEAR, OTHER |
| host_university | string | Host university name |
| host_country | string | Host country |
| gpa_minimum | number | Minimum GPA requirement |
| duration_months | number | Duration in months |
| stipend_usd | number | Stipend amount |
| deadline | date | Application deadline |
| application_url | url | Application link |
| description | text | Program description |

---

## Response Format

All list endpoints return paginated responses:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

## Error Responses

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 404 | Item not found |
| 422 | Validation error (invalid parameters) |
| 500 | Internal server error |

**Error Response Format:**
```json
{
  "detail": "Error message here"
}
```

---

## Interactive API Documentation

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
