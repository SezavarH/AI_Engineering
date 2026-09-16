## A Simple Example with an English Table

Suppose we have this table called `scores`:

| name | score |
|------|-------|
| Ali  | 18    |
| Ali  | 15    |
| Sara | 20    |
| Sara | 17    |
| Sara | 19    |

---

### 1. Simplest Case (Average per Person)

```sql
SELECT 
    name,
    score,
    AVG(score) OVER (PARTITION BY name) AS avg_score
FROM scores;
```

Result:

| name | score | avg_score |
|------|-------|-----------|
| Ali  | 18    | 16.5      |
| Ali  | 15    | 16.5      |
| Sara | 20    | 18.666    |
| Sara | 17    | 18.666    |
| Sara | 19    | 18.666    |

---

### 2. Numbering the Rows (ROW_NUMBER)

```sql
SELECT 
    name,
    score,
    ROW_NUMBER() OVER (
        PARTITION BY name 
        ORDER BY score DESC
    ) AS row_num
FROM scores;
```

Result:

| name | score | row_num |
|------|-------|---------|
| Ali  | 18    | 1       |
| Ali  | 15    | 2       |
| Sara | 20    | 1       |
| Sara | 19    | 2       |
| Sara | 17    | 3       |

---

### 3. Ranking (RANK)

```sql
SELECT 
    name,
    score,
    RANK() OVER (
        PARTITION BY name 
        ORDER BY score DESC
    ) AS rank_num
FROM scores;
```

---

### 4. Running Total

```sql
SELECT 
    name,
    score,
    SUM(score) OVER (
        PARTITION BY name 
        ORDER BY score
    ) AS running_total
FROM scores;
```

---

### 5. Seeing the Previous Row's Value (LAG)

```sql
SELECT 
    name,
    score,
    LAG(score) OVER (
        PARTITION BY name 
        ORDER BY score
    ) AS previous_score
FROM scores;
```

---

## یک مثال ساده با جدول انگلیسی

فرض کن این جدول را داریم به اسم `scores`:

| name | score |
|------|-------|
| Ali  | 18    |
| Ali  | 15    |
| Sara | 20    |
| Sara | 17    |
| Sara | 19    |

---

### ۱. ساده‌ترین حالت (میانگین برای هر نفر)

```sql
SELECT 
    name,
    score,
    AVG(score) OVER (PARTITION BY name) AS avg_score
FROM scores;
```

نتیجه:

| name | score | avg_score |
|------|-------|-----------|
| Ali  | 18    | 16.5      |
| Ali  | 15    | 16.5      |
| Sara | 20    | 18.666    |
| Sara | 17    | 18.666    |
| Sara | 19    | 18.666    |

---

### ۲. شماره‌گذاری ردیف‌ها (ROW_NUMBER)

```sql
SELECT 
    name,
    score,
    ROW_NUMBER() OVER (
        PARTITION BY name 
        ORDER BY score DESC
    ) AS row_num
FROM scores;
```

نتیجه:

| name | score | row_num |
|------|-------|---------|
| Ali  | 18    | 1       |
| Ali  | 15    | 2       |
| Sara | 20    | 1       |
| Sara | 19    | 2       |
| Sara | 17    | 3       |

---

### ۳. رتبه‌بندی (RANK)

```sql
SELECT 
    name,
    score,
    RANK() OVER (
        PARTITION BY name 
        ORDER BY score DESC
    ) AS rank_num
FROM scores;
```

---

### ۴. جمع تجمعی (Running Total)

```sql
SELECT 
    name,
    score,
    SUM(score) OVER (
        PARTITION BY name 
        ORDER BY score
    ) AS running_total
FROM scores;
```

---

### ۵. دیدن مقدار ردیف قبلی (LAG)

```sql
SELECT 
    name,
    score,
    LAG(score) OVER (
        PARTITION BY name 
        ORDER BY score
    ) AS previous_score
FROM scores;
```