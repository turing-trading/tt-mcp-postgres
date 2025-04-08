# Postgres Pro MCP Server Demos

This document contains examples and scripts to demonstrate the capabilities of Postgres Pro MCP Server with AI assistants like Claude, Cursor, and other MCP-compatible agents.

## Setup

Before running these demos, ensure you have:

1. Postgres Pro MCP Server installed and configured
2. A PostgreSQL database (sample databases provided below)
3. An MCP-compatible AI assistant configured to use Postgres Pro

## Demo 1: Database Health Assessment

### Scenario
You've inherited a production database and need to understand its health and identify potential issues.

### Sample Interaction

**User:** "Can you check the health of my database and identify any issues that might impact performance?"

**Assistant Actions:**
1. Uses `analyze_db_health` to perform comprehensive health checks
2. Analyzes buffer cache hit rates, connection health, vacuum status, etc.
3. Identifies problems such as unused indexes, bloated tables, or vacuum issues
4. Presents findings in an organized format with severity ratings
5. Provides specific recommendations for each issue

### Practical Implementation

#### Step 1: Create test database with issues

```bash
# Create a test database
createdb health_demo

# Connect to the database
psql health_demo
```

```sql
-- Create tables with common issues
CREATE TABLE big_table (
  id SERIAL PRIMARY KEY,
  data TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  status TEXT,
  category TEXT,
  price NUMERIC(10,2)
);

-- Insert dummy data (1 million rows)
INSERT INTO big_table (data, status, category, price)
SELECT 
  md5(random()::text), 
  (ARRAY['active', 'inactive', 'pending', 'deleted'])[ceil(random()*4)],
  (ARRAY['A', 'B', 'C', 'D', 'E'])[ceil(random()*5)],
  random()*1000
FROM generate_series(1, 1000000);

-- Create inefficient indexes
CREATE INDEX idx_big_table_data ON big_table(data); -- Inefficient text index
CREATE INDEX idx_big_table_status ON big_table(status); -- Duplicate of another index we'll create
CREATE INDEX idx_big_table_status_category ON big_table(status, category); -- Redundant with status index

-- Create a table with a sequence that will approach its limit
CREATE SEQUENCE almost_depleted_sequence START 2147483000; -- Close to max int
CREATE TABLE high_sequence_table (
  id INTEGER PRIMARY KEY DEFAULT nextval('almost_depleted_sequence'),
  data TEXT
);

-- Insert some rows to use the sequence
INSERT INTO high_sequence_table (data)
SELECT md5(random()::text) FROM generate_series(1, 100);

-- Create bloated table by updating frequently
CREATE TABLE bloated_table (
  id SERIAL PRIMARY KEY,
  counter INTEGER,
  data TEXT
);

INSERT INTO bloated_table (counter, data)
SELECT 0, md5(random()::text) FROM generate_series(1, 10000);

-- Create many updates to cause bloat
DO $$
BEGIN
  FOR i IN 1..20 LOOP
    UPDATE bloated_table SET counter = counter + 1, data = md5(random()::text);
  END LOOP;
END $$;

-- Create tables with no stats
CREATE TABLE no_stats_table (
  id SERIAL PRIMARY KEY,
  data TEXT
);

INSERT INTO no_stats_table (data)
SELECT md5(random()::text) FROM generate_series(1, 1000);
```

#### Step 2: Connect to the database with Postgres Pro MCP

Configure your AI assistant to connect to the health_demo database.

#### Step 3: Ask for health assessment

**User:** "Can you check the health of my database and identify any issues that might impact performance?"

#### Step 4: Review findings and apply fixes

After receiving the health assessment, you can apply the recommended fixes:

```sql
-- Sample fixes based on expected findings:

-- Remove duplicate/redundant indexes
DROP INDEX idx_big_table_status;

-- Fix sequence approaching limit
ALTER SEQUENCE almost_depleted_sequence RESTART WITH 1;
-- or
ALTER TABLE high_sequence_table ALTER COLUMN id TYPE BIGINT;

-- Fix bloated table
VACUUM FULL bloated_table;

-- Update statistics
ANALYZE no_stats_table;
```

### Expected Results

The assessment should identify common issues like:
- Low buffer cache hit rates
- Connections approaching limits
- Unused or duplicate indexes
- Tables that haven't been vacuumed recently
- Bloated tables and indexes
- Sequences approaching their limits

## Demo 2: Index Recommendations for a Slow Application

### Scenario
Users are reporting that your application is running slow. You suspect database query performance is the culprit.

### Sample Interaction

**User:** "My application is slow, especially when users access the reporting dashboard. Can you help me figure out what's wrong and how to fix it?"

**Assistant Actions:**
1. Uses `get_top_queries` to identify slow queries
2. Analyzes the query patterns using `analyze_workload_indexes`
3. Identifies missing indexes or optimization opportunities
4. Recommends specific indexes to improve performance
5. Provides estimates of performance improvements for each recommendation

### Expected Results

The analysis should provide:
- List of the slowest queries by execution time
- Recommended indexes with estimated performance improvements
- Storage requirements for the proposed indexes
- Explanation of how each index would improve specific queries

## Demo 3: Query Optimization with Hypothetical Indexes

### Scenario
You have a specific complex query that's running slow, and you want to optimize it without making immediate changes to the database.

### Sample Interaction

**User:** "This query is running slow: `SELECT o.order_id, c.customer_name, p.product_name, o.order_date 
FROM orders o 
JOIN customers c ON o.customer_id = c.id 
JOIN order_items oi ON o.order_id = oi.order_id 
JOIN products p ON oi.product_id = p.id 
WHERE o.order_date > '2022-01-01' AND c.state = 'CA' 
ORDER BY o.order_date DESC LIMIT 100;`
Can you help me optimize it?"

**Assistant Actions:**
1. Uses `explain_query` to analyze the execution plan
2. Identifies bottlenecks in the query execution
3. Tests hypothetical indexes using HypoPG
4. Compares execution plans before and after proposed indexes
5. Recommends the most effective index(es) for this specific query

### Practical Implementation

#### Step 1: Create test schema and data

```bash
# Create a test database
createdb query_demo

# Connect to the database
psql query_demo
```

```sql
-- Create a sample e-commerce schema
CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  customer_name VARCHAR(100),
  email VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  city VARCHAR(100),
  state VARCHAR(2)
);

CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  product_name VARCHAR(100),
  category VARCHAR(50),
  price NUMERIC(10,2),
  inventory_count INTEGER
);

CREATE TABLE orders (
  order_id SERIAL PRIMARY KEY,
  customer_id INTEGER REFERENCES customers(id),
  order_date TIMESTAMP DEFAULT NOW(),
  total_amount NUMERIC(12,2),
  status VARCHAR(20)
);

CREATE TABLE order_items (
  id SERIAL PRIMARY KEY,
  order_id INTEGER REFERENCES orders(order_id),
  product_id INTEGER REFERENCES products(id),
  quantity INTEGER,
  unit_price NUMERIC(10,2)
);

-- Insert sample data
INSERT INTO customers (customer_name, email, city, state)
SELECT 
  'Customer ' || i,
  'customer' || i || '@example.com',
  (ARRAY['New York', 'Chicago', 'Los Angeles', 'Houston', 'Phoenix'])[1 + (i % 5)],
  (ARRAY['NY', 'IL', 'CA', 'TX', 'AZ'])[1 + (i % 5)]
FROM generate_series(1, 10000) i;

INSERT INTO products (product_name, category, price, inventory_count)
SELECT 
  'Product ' || i,
  (ARRAY['Electronics', 'Clothing', 'Books', 'Home', 'Food'])[1 + (i % 5)],
  (random() * 500)::numeric(10,2),
  (random() * 1000)::integer
FROM generate_series(1, 1000) i;

INSERT INTO orders (customer_id, order_date, total_amount, status)
SELECT 
  (random() * 10000)::integer + 1,
  NOW() - (random() * 365 * 2)::integer * INTERVAL '1 day',
  (random() * 1000)::numeric(12,2),
  (ARRAY['Completed', 'Processing', 'Shipped', 'Cancelled'])[1 + (i % 4)]
FROM generate_series(1, 50000) i;

INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT 
  (random() * 50000)::integer + 1,
  (random() * 1000)::integer + 1,
  (random() * 5)::integer + 1,
  (random() * 500)::numeric(10,2)
FROM generate_series(1, 150000) i;

-- Create some basic indexes, but not optimal ones
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
```

#### Step 2: Install required extensions

```sql
-- Install required extensions for hypothetical indexes testing
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS hypopg;
```

#### Step 3: Connect to the database with Postgres Pro MCP

Configure your AI assistant to connect to the query_demo database.

#### Step 4: Submit slow query for optimization

**User:** "This query is running slow: `SELECT o.order_id, c.customer_name, p.product_name, o.order_date 
FROM orders o 
JOIN customers c ON o.customer_id = c.id 
JOIN order_items oi ON o.order_id = oi.order_id 
JOIN products p ON oi.product_id = p.id 
WHERE o.order_date > '2022-01-01' AND c.state = 'CA' 
ORDER BY o.order_date DESC LIMIT 100;`
Can you help me optimize it?"

#### Step 5: Implement the recommended indexes

After receiving the optimization recommendations:

```sql
-- Example optimal indexes that might be recommended
CREATE INDEX idx_orders_order_date ON orders(order_date DESC);
CREATE INDEX idx_customers_state_id ON customers(state, id);
CREATE INDEX idx_order_items_order_id_product_id ON order_items(order_id, product_id);

-- Or a covering index such as:
CREATE INDEX idx_orders_customer_date ON orders(customer_id, order_date DESC);
```

#### Step 6: Verify performance improvement

```sql
-- Compare execution times before and after index creation
EXPLAIN ANALYZE SELECT o.order_id, c.customer_name, p.product_name, o.order_date 
FROM orders o 
JOIN customers c ON o.customer_id = c.id 
JOIN order_items oi ON o.order_id = oi.order_id 
JOIN products p ON oi.product_id = p.id 
WHERE o.order_date > '2022-01-01' AND c.state = 'CA' 
ORDER BY o.order_date DESC LIMIT 100;
```

### Expected Results

The optimization should provide:
- Original execution plan with identified bottlenecks
- Several hypothetical index options
- Comparison of execution costs with each index option
- Recommendation of the most effective index(es)
- Potential SQL for creating the recommended index(es)

## Demo 4: Schema Discovery and Documentation

### Scenario
You're working with a new database and need to understand its structure, relationships, and data.

### Sample Interaction

**User:** "I'm new to this database. Can you help me understand its structure and how the tables are related?"

**Assistant Actions:**
1. Uses `list_schemas` to identify available schemas
2. Uses `list_objects` to find tables, views, and other objects
3. Uses `get_object_details` to examine table structures and relationships
4. Identifies primary keys, foreign keys, and indexing strategies
5. Creates a comprehensive overview of the database structure

### Expected Results

The assistant should provide:
- List of schemas and their purpose
- Major tables and their relationships
- Primary and foreign key structure
- Existing indexing strategy
- Entity-relationship description in natural language
- Recommendations for better documentation if needed

## Demo 5: Storage Optimization

### Scenario
Your database is growing rapidly and you're concerned about storage usage.

### Sample Interaction

**User:** "My database is growing too large. Can you help me identify what's taking up space and how I can optimize storage?"

**Assistant Actions:**
1. Analyzes table and index sizes
2. Identifies bloated tables and indexes
3. Finds unused indexes that can be safely removed
4. Recommends partitioning strategies for large tables
5. Suggests VACUUM and maintenance strategies

### Expected Results

The analysis should provide:
- List of largest tables and indexes
- Identification of bloated objects
- Unused indexes that can be removed
- Partitioning recommendations for large tables
- Vacuum and maintenance schedule recommendations
- Estimated storage savings from implementing recommendations

## Demo 6: Advanced Workload Analysis

### Scenario
You want to understand your database workload patterns to plan for scaling and optimization.

### Sample Interaction

**User:** "We're planning to scale our application. Can you analyze our database workload patterns to help us understand what we need to optimize?"

**Assistant Actions:**
1. Analyzes query patterns from pg_stat_statements
2. Identifies peak usage times and resource-intensive operations
3. Categorizes queries by type (read/write, tables accessed)
4. Recommends caching strategies, connection pooling optimizations
5. Suggests application-level and database-level improvements

### Practical Implementation

#### Step 1: Set up a simulated production workload

```bash
# Create a test database
createdb workload_demo

# Connect to the database
psql workload_demo
```

```sql
-- Install required extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create sample schema
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(100) UNIQUE,
  email VARCHAR(100) UNIQUE,
  created_at TIMESTAMP DEFAULT NOW(),
  last_login TIMESTAMP
);

CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  price NUMERIC(10,2),
  stock INTEGER,
  category VARCHAR(50)
);

CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  status VARCHAR(20)
);

CREATE TABLE order_items (
  id SERIAL PRIMARY KEY,
  order_id INTEGER REFERENCES orders(id),
  product_id INTEGER REFERENCES products(id),
  quantity INTEGER,
  price NUMERIC(10,2)
);

CREATE TABLE page_views (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  page VARCHAR(100),
  viewed_at TIMESTAMP DEFAULT NOW()
);

-- Load sample data
INSERT INTO users (username, email, created_at, last_login)
SELECT 
  'user' || i, 
  'user' || i || '@example.com',
  NOW() - (random() * 365)::integer * INTERVAL '1 day',
  NOW() - (random() * 30)::integer * INTERVAL '1 day'
FROM generate_series(1, 10000) i;

INSERT INTO products (name, price, stock, category)
SELECT 
  'Product ' || i,
  (random() * 1000)::numeric(10,2),
  (random() * 100)::integer,
  (ARRAY['Electronics', 'Clothing', 'Home', 'Books', 'Food'])[1 + (i % 5)]
FROM generate_series(1, 1000) i;

INSERT INTO orders (user_id, created_at, status)
SELECT 
  (random() * 10000)::integer + 1,
  NOW() - (random() * 180)::integer * INTERVAL '1 day',
  (ARRAY['completed', 'processing', 'shipped', 'cancelled'])[1 + (i % 4)]
FROM generate_series(1, 50000) i;

INSERT INTO order_items (order_id, product_id, quantity, price)
SELECT 
  (random() * 50000)::integer + 1,
  (random() * 1000)::integer + 1,
  (random() * 5)::integer + 1,
  (random() * 1000)::numeric(10,2)
FROM generate_series(1, 100000) i;

INSERT INTO page_views (user_id, page, viewed_at)
SELECT 
  (random() * 10000)::integer + 1,
  (ARRAY['home', 'product', 'cart', 'checkout', 'profile'])[1 + (i % 5)],
  NOW() - (random() * 30)::integer * INTERVAL '1 day' - (random() * 24)::integer * INTERVAL '1 hour'
FROM generate_series(1, 500000) i;
```

#### Step 2: Run a mixed workload simulation

```sql
-- Create a function to run random queries
CREATE OR REPLACE FUNCTION run_random_workload() RETURNS void AS $$
DECLARE
  user_id_var INTEGER;
  product_id_var INTEGER;
  order_id_var INTEGER;
  category_var VARCHAR;
BEGIN
  -- Select random values to use in queries
  SELECT id INTO user_id_var FROM users ORDER BY random() LIMIT 1;
  SELECT id INTO product_id_var FROM products ORDER BY random() LIMIT 1;
  SELECT id INTO order_id_var FROM orders ORDER BY random() LIMIT 1;
  SELECT category INTO category_var FROM products ORDER BY random() LIMIT 1;
  
  -- Run a random mix of queries
  CASE (random() * 10)::integer
    WHEN 0 THEN
      -- User profile query
      PERFORM * FROM users WHERE id = user_id_var;
    WHEN 1 THEN
      -- Product search
      PERFORM * FROM products WHERE category = category_var ORDER BY price LIMIT 10;
    WHEN 2 THEN
      -- Order history
      PERFORM o.id, o.created_at, sum(oi.price * oi.quantity) 
      FROM orders o JOIN order_items oi ON o.id = oi.order_id 
      WHERE o.user_id = user_id_var
      GROUP BY o.id, o.created_at ORDER BY o.created_at DESC;
    WHEN 3 THEN
      -- Product detail with stock
      PERFORM p.*, sum(oi.quantity) as total_ordered
      FROM products p LEFT JOIN order_items oi ON p.id = oi.product_id
      WHERE p.id = product_id_var
      GROUP BY p.id;
    WHEN 4 THEN
      -- Dashboard summary
      PERFORM count(*), sum(oi.price * oi.quantity)
      FROM orders o JOIN order_items oi ON o.id = oi.order_id
      WHERE o.created_at > (NOW() - INTERVAL '7 days');
    WHEN 5 THEN
      -- Insert page view
      INSERT INTO page_views (user_id, page)
      VALUES (user_id_var, (ARRAY['home', 'product', 'cart', 'checkout', 'profile'])[1 + (random() * 4)::integer]);
    WHEN 6 THEN
      -- Update product stock
      UPDATE products SET stock = stock - 1 WHERE id = product_id_var AND stock > 0;
    WHEN 7 THEN
      -- Order analysis
      PERFORM p.category, count(*), sum(oi.quantity)
      FROM order_items oi JOIN products p ON oi.product_id = p.id
      JOIN orders o ON oi.order_id = o.id
      WHERE o.created_at > (NOW() - INTERVAL '30 days')
      GROUP BY p.category ORDER BY sum(oi.quantity) DESC;
    WHEN 8 THEN
      -- User session analysis
      PERFORM user_id, count(*), min(viewed_at), max(viewed_at)
      FROM page_views
      WHERE viewed_at > (NOW() - INTERVAL '1 day')
      GROUP BY user_id HAVING count(*) > 5
      ORDER BY count(*) DESC LIMIT 10;
    ELSE
      -- Complex join for reporting
      PERFORM u.id, u.username, count(o.id) as order_count, sum(oi.price * oi.quantity) as total_spent
      FROM users u
      JOIN orders o ON u.id = o.user_id
      JOIN order_items oi ON o.id = oi.order_id
      WHERE u.created_at > (NOW() - INTERVAL '90 days')
      GROUP BY u.id, u.username
      ORDER BY total_spent DESC LIMIT 100;
  END CASE;
END;
$$ LANGUAGE plpgsql;

-- Run the workload multiple times
DO $$
BEGIN
  FOR i IN 1..1000 LOOP
    PERFORM run_random_workload();
  END LOOP;
END $$;

-- Reset pg_stat_statements to get clean data
SELECT pg_stat_statements_reset();

-- Run the workload again to collect stats
DO $$
BEGIN
  FOR i IN 1..1000 LOOP
    PERFORM run_random_workload();
  END LOOP;
END $$;
```

#### Step 3: Connect to the database with Postgres Pro MCP

Configure your AI assistant to connect to the workload_demo database.

#### Step 4: Analyze workload patterns

**User:** "We're planning to scale our application. Can you analyze our database workload patterns to help us understand what we need to optimize?"

#### Step 5: Implement the recommendations

After receiving the analysis and recommendations, you might implement changes such as:

```sql
-- Example implementations based on common recommendations:

-- Create targeted indexes for the most frequent queries
CREATE INDEX idx_page_views_user_viewed_at ON page_views(user_id, viewed_at);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_products_category_price ON products(category, price);

-- Add materialized view for dashboard summary
CREATE MATERIALIZED VIEW mv_sales_summary AS
SELECT 
  date_trunc('day', o.created_at) as day,
  p.category,
  count(distinct o.id) as order_count,
  count(distinct o.user_id) as user_count,
  sum(oi.quantity) as items_sold,
  sum(oi.price * oi.quantity) as total_sales
FROM orders o 
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.status = 'completed'
GROUP BY 1, 2;

-- Create refresh function
CREATE OR REPLACE FUNCTION refresh_sales_summary()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW mv_sales_summary;
END
$$ LANGUAGE plpgsql;

-- Add table partitioning for large tables
CREATE TABLE page_views_partitioned (
  id SERIAL,
  user_id INTEGER,
  page VARCHAR(100),
  viewed_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (viewed_at);

-- Create partitions
CREATE TABLE page_views_y2023m01 PARTITION OF page_views_partitioned
  FOR VALUES FROM ('2023-01-01') TO ('2023-02-01');
CREATE TABLE page_views_y2023m02 PARTITION OF page_views_partitioned
  FOR VALUES FROM ('2023-02-01') TO ('2023-03-01');
-- Add more partitions as needed

-- Add connection pooling configuration example (for pgbouncer)
-- This would be added to your pgbouncer.ini file
/*
[databases]
workload_demo = host=127.0.0.1 port=5432 dbname=workload_demo

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 50
*/
```

### Expected Results

The analysis should provide:
- Breakdown of query types (SELECT, INSERT, UPDATE, DELETE)
- Time distribution of database activity
- Resource consumption patterns
- Tables and operations that are most resource-intensive
- Recommendations for scaling strategies
- Specific application and database optimization suggestions

## Sample Databases for Demo

To run these demos effectively, you can use these sample databases:

1. **Pagila** - A sample DVD rental database
   - [GitHub Repository](https://github.com/devrimgunduz/pagila)
   - Good for demonstrating JOIN optimizations and complex queries

2. **Northwind** - A classic sample database
   - [GitHub Repository](https://github.com/pthom/northwind_psql)
   - Simple structure that's easy to understand

3. **DVD Rental** - Another sample database from PostgreSQL tutorials
   - [Download Link](https://www.postgresqltutorial.com/postgresql-getting-started/postgresql-sample-database/)
   - Includes rental, inventory, and customer data

4. **PgBench** - For performance testing
   - Built into PostgreSQL
   - Run `pgbench -i -s 10` to create a test database with scaling factor 10

## Tips for Effective Demos

1. **Pre-warm the database**: Run some queries before the demo to ensure the cache is warm
2. **Create some issues**: Deliberately create some issues (like missing indexes) to demonstrate problem detection
3. **Use real-world queries**: Use realistic queries that demonstrate complex relationships and calculations
4. **Prepare failure cases**: Show how the system handles errors and edge cases
5. **Demonstrate progressive optimization**: Show how incremental improvements can significantly boost performance 
