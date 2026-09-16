# JOIN

## Mental Model

- Think of tables as stacks of paper (rows). 
- A JOIN is the act of laying two stacks side-by-side and deciding which pairs of sheets you keep based on a matching rule (the ON condition).

```sql
SELECT ...
FROM left_table  AS l
[INNER | LEFT | RIGHT | FULL] JOIN right_table AS r
  ON l.key = r.key          -- or any boolean condition
[WHERE ...]
```

## Example

### Ex.1
Tables:

- orders (order_id, customer_id, order_date, amount)
- customers (customer_id, name, city)

Question: 

- “List every customer and the total amount they have spent. Include customers who have never ordered.”

Solution:
- Pay attention to: every customer, total amount, customers who never ordered (Left Join)
- For customers with no orders, o.amount is NULL, SUM() ignores NULLs and returns NULL (not 0) for an all-NULL group, So wrap it with __COALESCE__


```sql
SELECT
    c.customer_id,
    c.name,
    COALESCE(SUM(o.amount), 0) AS total_spent
FROM customers c
LEFT JOIN orders o
    ON c.customer_id = o.customer_id 
GROUP BY 
    c.customer_id,
    c.name

```

### Ex.2
Tables:

- orders (order_id, customer_id, order_date, amount)
- customers (customer_id, name, city)

Question: 

- write a query that returns every order together with the customer’s name. 
- If an order has a customer_id that no longer exists in the customers table, still show the order (with NULL name).

```sql
SELECT
    c.name,
    o.order_id
FROM orders o 
LEFT JOIN customers c
    ON o.customer_id = c.customer_id 
```

### Ex.3

Tables:

- orders (order_id, customer_id, order_date, amount)
- customers (customer_id, name, city)

Question:

- "List every city and the total amount spent by customers in that city. Include cities where customers have never placed any orders. Show only cities where the total spent is greater than 100."

Solution:

- Keywords: every city, total amount, city where have never (LEFT), GT spent >100

```sql
SELECT
    c.city,
    COALESCE(SUM(o.amount), 0) AS total_spent
FROM customers c
LEFT JOIN orders o
    ON c.customer_id = o.customer_id
GROUP BY 
    c.city
HAVING
    COALESCE(SUM(o.amount), 0) > 100
```

# GROUP BY

## Mental Model

- GROUP BY is “collapse groups of rows that share the same values into a single summary row.”
- HAVING is the WHERE clause that runs after the groups have been formed.
- Problems with each ...,

## Ex 1

Tables:

- orders (order_id, customer_id, order_date, amount)
- customers (customer_id, name, city)

Question: 

- “Find cities that have more than 3 customers who have placed at least one order, and show the number of such customers and their total spend.”

Solution: 

- Which Tables Do I Need? customers → gives us city and customer_id and orders → tells us who actually ordered + the amount (JOIN)
- Which JOIN? → customers who have placed at least one order => INNER JOIN
- cities that have ... → GROUP BY

```sql
SELECT
    c.city.
    COUNT(DISTINCT c.customer_id) AS customer_count,
    SUM(o.amount) AS total_spend
FROM customers c
INNER JOIN orders o
    ON c.customer_id = o.customer_id
GROUP BY
    c.city
HAVING
    COUNT(DISTINCT c.customer_id) > 3
```

## Ex 2

Tables:

- orders (order_id, customer_id, order_date, amount)
- customers (customer_id, name, city)

Question: 

- Return each customer’s total spend and number of orders, but only for customers whose average order value is greater than 100.

```sql
SELECT 
    SUM(amount) AS total_spend,
    COUNT(order_id) AS order_count
FROM orders 
GROUP BY
    customer_id
HAVING
    AVG(amount) > 100;
```

## Ex 3

- "How many orders has each customer placed?"       "هر مشتری چند سفارش داده؟"

each customer => per group (customer)

```sql
SELECT customer_id, COUNT(*)
FROM orders
GROUP BY customer_id;
```

## Ex 4

- "How much did each city sell?"       "هر شهر چقدر فروش داشته؟"

each city => per group (customer)

```sql
SELECT customer_id, COUNT(*)
FROM orders
GROUP BY customer_id;
```