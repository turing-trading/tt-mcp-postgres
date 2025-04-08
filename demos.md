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

## Advanced Multi-Step Demo Scenarios

The following scenarios demonstrate more comprehensive, real-world uses of Postgres Pro MCP that involve multiple interactions and progressive problem-solving approaches.

## Advanced Demo 1: E-commerce Performance Optimization Journey

### Scenario
You're the lead developer at a growing e-commerce site experiencing periodic slowdowns during peak hours. Customer complaints are increasing, and the marketing team plans a major promotion next week that will significantly increase traffic.

### Multi-step Interaction Flow

#### Step 1: Initial Assessment

**User:** "Our e-commerce site has been slowing down, especially during peak hours. We've got a major sales event next week and need to make sure the database can handle the load."

**Assistant:**
"I'll help you optimize your database for the upcoming sales event. Let's start with a comprehensive health check to establish baseline metrics and identify any immediate issues."

*The assistant runs:*
```
analyze_db_health with all components
```

"I've analyzed your database health and found several issues that could be affecting performance:

1. Your buffer cache hit rate is 82%, which is below the recommended 99%
2. I've identified 3 unused indexes consuming 4.2GB of storage
3. Several tables haven't been vacuumed in over 30 days
4. The 'orders' table appears to be bloated (43% bloat ratio)

Let's examine your slow queries before making optimization recommendations."

#### Step 2: Workload Analysis

*The assistant runs:*
```
get_top_queries
analyze_workload_indexes
```

"Looking at your query patterns, I see that:

1. The product search query accounts for 42% of your database load:
   ```sql
   SELECT p.*, c.category_name 
   FROM products p 
   JOIN categories c ON p.category_id = c.id 
   WHERE p.is_available = true 
   AND (p.name ILIKE $1 OR p.description ILIKE $1) 
   ORDER BY p.popularity_score DESC LIMIT 20;
   ```

2. Order history lookups are taking 2.3 seconds on average:
   ```sql
   SELECT o.*, ol.*, p.name, p.image_url
   FROM orders o
   JOIN order_lines ol ON o.id = ol.order_id
   JOIN products p ON ol.product_id = p.id
   WHERE o.customer_id = $1
   ORDER BY o.created_at DESC
   LIMIT 10;
   ```

3. Your checkout process involves 12 separate queries, several of which could be optimized

Based on the workload analysis, I recommend these specific optimizations:

1. Create a partial index for product searches
2. Add a covering index for order history
3. Drop the 3 unused indexes I identified
4. Run VACUUM FULL on the bloated orders table
5. Add an index on customer_id + created_at for the orders table"

**User:** "Can you explain how these changes will improve our product search specifically? That's the most critical part of our application."

#### Step 3: Testing Hypothetical Indexes

*The assistant runs:*
```
explain_query with hypothetical indexes for the product search query
```

"I've simulated several index combinations for your product search query. Here's what I found:

**Current execution plan (cost: 15403.28, estimated time: 570ms):**
- Performs a bitmap heap scan on products
- Uses a sequential scan on categories
- Uses a nested loop join

**With a multicolumn index on (is_available, popularity_score) including name, description:**
```sql
CREATE INDEX idx_product_search ON products (is_available, popularity_score DESC) 
INCLUDE (name, description, category_id);
```

This would reduce the query cost by 93% to 1078.42 (estimated time: ~40ms) by:
- Enabling an index-only scan instead of bitmap scan
- Eliminating the need for sorting (ORDER BY)
- Reducing the amount of data read from disk

This is the optimal index configuration for this specific query pattern. Would you like me to implement this change or simulate any other indexes?"

**User:** "That sounds promising. Let's implement those changes and verify the improvements."

#### Step 4: Implementing and Verifying Changes

*The assistant provides SQL statements for each change:*
```sql
-- Create optimal product search index
CREATE INDEX idx_product_search ON products (is_available, popularity_score DESC) 
INCLUDE (name, description, category_id);

-- Add covering index for order history
CREATE INDEX idx_orders_customer_history ON orders (customer_id, created_at DESC);

-- Drop unused indexes
DROP INDEX idx_products_price;
DROP INDEX idx_order_update_time;
DROP INDEX idx_rarely_used_column;

-- Run VACUUM FULL on bloated table
VACUUM FULL orders;

-- Adjust configuration (if you have server access)
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET work_mem = '16MB';
```

*After implementation, the assistant verifies:*
```
explain_query for the product search with the new index
get_top_queries to confirm improvements
```

"I've verified the improvements:

1. The product search query is now running 14x faster, down from 570ms to 41ms
2. Order history lookups improved from 2.3s to 320ms
3. Overall database load has decreased by approximately 35%
4. We've reclaimed 4.2GB of storage by removing unused indexes
5. Buffer cache hit rate has improved to 96% after configuration changes

These optimizations should provide significant headroom for your upcoming sales event."

#### Step 5: Load Testing Simulation

**User:** "How can we verify the database will handle our projected load for the sales event?"

**Assistant:**
"To verify your database will handle the increased load, I recommend simulating your peak traffic patterns. Here's how we can set up a test:

1. First, create a custom pgbench script that mirrors your actual workload:

```sql
-- Save as custom_workload.sql
\set customer_id random(1, 10000)
\set search_term 'product' || random(1, 100)
\set product_id random(1, 5000)

BEGIN;
-- Product search (most common operation)
SELECT p.*, c.category_name 
FROM products p 
JOIN categories c ON p.category_id = c.id 
WHERE p.is_available = true 
AND (p.name ILIKE '%' || :search_term || '%') 
ORDER BY p.popularity_score DESC LIMIT 20;

-- View product details
SELECT * FROM products WHERE id = :product_id;

-- Customer order history (less frequent)
SELECT o.*, ol.*, p.name, p.image_url
FROM orders o
JOIN order_lines ol ON o.id = ol.order_id
JOIN products p ON ol.product_id = p.id
WHERE o.customer_id = :customer_id
ORDER BY o.created_at DESC
LIMIT 10;
COMMIT;
```

2. Run the load test with your projected traffic (for example, 5x current load):

```bash
pgbench -h localhost -U username -d dbname -f custom_workload.sql -c 50 -j 4 -T 300
```

This simulates 50 concurrent connections running your custom workload for 5 minutes.

3. During the test, monitor these key metrics:
   - Transaction throughput (TPS)
   - Average latency
   - 95th percentile latency
   - Connection utilization
   - CPU and memory usage

With these optimizations implemented, you should be able to handle the increased load for your sales event. The load test will confirm this and identify any remaining bottlenecks."

### Expected Results

After completing this multi-step optimization process, you should achieve:

- 80-95% reduction in query execution time for critical queries
- 30-50% overall reduction in database load
- Significantly improved buffer cache utilization
- Confidence in the database's ability to handle peak traffic
- Elimination of unused or redundant database objects

## Advanced Demo 2: Data Warehouse Query Optimization

### Scenario
You're managing a data warehouse that analysts use for business intelligence. Reports that were fast with smaller data volumes now take hours to complete after a year of data collection. Your analytics team needs these reports to run much faster to support weekly instead of quarterly business reviews.

### Multi-Step Interactions

#### Step 1: Problem Assessment

**User:** "Our quarterly sales report query used to take 5 minutes but now runs for over 3 hours. We need to generate these reports weekly instead of quarterly, so this performance is unacceptable."

**Assistant:**
"I'll help you optimize your data warehouse queries. Can you share the problematic query so I can analyze it?"

**User:**
```sql
SELECT 
  date_trunc('month', o.order_date) as month,
  c.category_name,
  r.region_name,
  SUM(ol.quantity) as units_sold,
  SUM(ol.quantity * ol.unit_price) as revenue,
  COUNT(DISTINCT o.customer_id) as unique_customers
FROM orders o
JOIN order_lines ol ON o.id = ol.order_id
JOIN products p ON ol.product_id = p.id
JOIN categories c ON p.category_id = c.id
JOIN customers cust ON o.customer_id = cust.id
JOIN regions r ON cust.region_id = r.id
WHERE o.order_date >= '2022-01-01'
  AND o.status = 'completed'
GROUP BY 1, 2, 3
ORDER BY 1, 3, 2;
```

#### Step 2: Schema and Data Volume Analysis

*The assistant examines the schema and data volumes:*
```
list_schemas
list_objects in public schema
get_object_details for tables: orders, order_lines, products, categories, customers, regions
```

"I've analyzed your schema and found:

1. The `orders` table has 8.5 million rows (245GB)
2. The `order_lines` table has 42 million rows (512GB)
3. The `products` table has 250,000 rows
4. Your tables are not partitioned by date
5. There's no index on orders.order_date which is causing a sequential scan
6. The query involves 5 joins without optimal join indexes

These factors explain why your query performance has degraded as data volumes increased."

#### Step 3: Query Plan Analysis

*The assistant runs:*
```
explain_query with ANALYZE for the report query
```

"The execution plan reveals several bottlenecks:

1. **Sequential scan on orders table** (245GB) - Cost: 1,245,832.45, actual time: 1532.4ms
2. **Hash join between orders and order_lines** - Cost: 3,852,421.12, actual time: 5284.7ms
3. **Sort operation for GROUP BY** - Cost: 854,372.18, actual time: 3842.5ms
4. **Additional nested loop joins** with smaller tables - Cost: 452,471.85, actual time: 2143.2ms

The total execution time is 186 minutes, with most time spent on disk I/O and sorting operations. Let's implement a series of optimizations to address each bottleneck."

#### Step 4: Progressive Optimization

**Assistant:** "I recommend a progressive optimization approach where we implement changes in stages and measure the improvement at each step."

##### Stage 1: Basic Indexing

*Assistant provides SQL for initial improvements:*
```sql
-- Add index for the WHERE clause
CREATE INDEX idx_orders_date_status ON orders (order_date, status);

-- Add index for the GROUP BY
CREATE INDEX idx_orderlines_order_id ON order_lines (order_id);
```

"After implementing these basic indexes, the query execution time reduced from 186 minutes to 78 minutes - a 58% improvement, but still not enough."

##### Stage 2: Materialized View Creation

```sql
-- Create a materialized view for monthly sales aggregations
CREATE MATERIALIZED VIEW mv_monthly_sales AS
SELECT 
  date_trunc('month', o.order_date) as month,
  p.category_id,
  cust.region_id,
  SUM(ol.quantity) as units_sold,
  SUM(ol.quantity * ol.unit_price) as revenue,
  COUNT(DISTINCT o.customer_id) as unique_customers
FROM orders o
JOIN order_lines ol ON o.id = ol.order_id
JOIN products p ON ol.product_id = p.id
JOIN customers cust ON o.customer_id = cust.id
WHERE o.order_date >= '2022-01-01'
  AND o.status = 'completed'
GROUP BY 1, 2, 3;

-- Add indexes to the materialized view
CREATE INDEX idx_mv_monthly_sales_month ON mv_monthly_sales(month);
CREATE INDEX idx_mv_monthly_sales_category ON mv_monthly_sales(category_id);
CREATE INDEX idx_mv_monthly_sales_region ON mv_monthly_sales(region_id);

-- Create a refresh function
CREATE OR REPLACE FUNCTION refresh_sales_mv()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW mv_monthly_sales;
END
$$ LANGUAGE plpgsql;
```

"Now let's rewrite the query to use the materialized view:"

```sql
SELECT 
  mv.month,
  c.category_name,
  r.region_name,
  SUM(mv.units_sold) as units_sold,
  SUM(mv.revenue) as revenue,
  SUM(mv.unique_customers) as unique_customers
FROM mv_monthly_sales mv
JOIN categories c ON mv.category_id = c.id
JOIN regions r ON mv.region_id = r.id
GROUP BY 1, 2, 3
ORDER BY 1, 3, 2;
```

"This rewritten query now executes in 12 seconds - a 930x improvement over the original 3-hour runtime."

##### Stage 3: Table Partitioning Strategy

"For a long-term solution, I recommend implementing table partitioning on your orders table by date range:"

```sql
-- Create partitioned orders table
CREATE TABLE orders_partitioned (
  -- Same schema as original orders table
) PARTITION BY RANGE (order_date);

-- Create partitions by quarter
CREATE TABLE orders_y2022q1 PARTITION OF orders_partitioned
  FOR VALUES FROM ('2022-01-01') TO ('2022-04-01');
  
CREATE TABLE orders_y2022q2 PARTITION OF orders_partitioned
  FOR VALUES FROM ('2022-04-01') TO ('2022-07-01');
  
-- Add additional partitions as needed
-- ...

-- Create similar partitioning for order_lines if needed
```

"Partitioning would give you additional benefits:
1. More efficient pruning of irrelevant data
2. Faster vacuum and maintenance operations
3. Ability to archive older partitions to lower-cost storage
4. Improved query planning"

#### Step 5: Maintenance and Automation

"To maintain optimal performance as your data continues to grow:

1. Schedule regular refreshes of the materialized view:
   ```sql
   -- Add to crontab or pg_cron
   SELECT refresh_sales_mv();
   ```

2. Automate the creation of new partitions as needed

3. Set up a monitoring query to track the execution time trends:
   ```sql
   SELECT query, calls, mean_exec_time, total_exec_time
   FROM pg_stat_statements
   WHERE query ILIKE '%category%region%revenue%'
   ORDER BY total_exec_time DESC
   LIMIT 10;
   ```

4. Schedule statistics updates for optimal query planning:
   ```sql
   ANALYZE mv_monthly_sales;
   ```

With these optimizations in place, your reports will complete in seconds instead of hours, enabling weekly business reviews."

### Expected Results

After completing this data warehouse optimization:
- Query execution time reduced from 3+ hours to seconds
- Automated maintenance ensures consistent performance
- Data growth is managed through partitioning
- Analysts can run reports on demand rather than scheduling them overnight

## Advanced Demo 3: Database Migration Validation

### Scenario
You're migrating from a legacy database to a new PostgreSQL instance. You need to verify data integrity, optimize for the new workload, and ensure performance meets expectations.

### Multi-Step Interactions

#### Step 1: Initial Assessment

**User:** "We've just migrated our application database from MySQL to PostgreSQL. I need to validate the migration, ensure data integrity, and optimize for our workload patterns. Can you help?"

**Assistant:**
"I'll help you validate your migration and optimize your new PostgreSQL database. Let's start with a systematic assessment of the new database structure and health."

*The assistant runs:*
```
list_schemas
list_objects in public schema
analyze_db_health
```

"I've completed an initial assessment of your PostgreSQL database:

1. Schema structure: 42 tables, 18 views, 87 indexes, 6 triggers
2. Database health findings:
   - Missing primary keys on 3 tables
   - Foreign key constraints without indexes: 8
   - No indexes on frequently queried timestamp columns
   - Several tables missing ANALYZE statistics
   - No extensions currently installed

Let's continue with more detailed validation checks."

#### Step 2: Data Integrity Validation

**User:** "What checks should we run to ensure all data migrated correctly?"

**Assistant:**
"To validate data integrity after migration, let's run these checks:

1. **Row count validation for all tables:**
```sql
-- Save this as rowcount_validation.sql
SELECT 'SELECT ''' || table_name || ''', COUNT(*) FROM ' || table_name || ';'
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

2. **Primary key uniqueness check:**
```sql
-- For each table with a primary key
SELECT COUNT(*) as total_rows, COUNT(DISTINCT id) as unique_ids
FROM users;
-- Repeat for all tables with primary keys
```

3. **Foreign key validation:**
```sql
-- Example for order_items table
SELECT COUNT(*) 
FROM order_items oi 
LEFT JOIN orders o ON oi.order_id = o.id
WHERE o.id IS NULL;
```

4. **Data type conversion issues check:**
```sql
-- Check for truncated values in text fields
SELECT COUNT(*) FROM products WHERE LENGTH(description) = 255;
```

5. **Statistical distribution comparison:**
```sql
-- Check value distributions match expected patterns
SELECT 
  MIN(amount), MAX(amount), AVG(amount), 
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) as median
FROM transactions;
```

Would you like me to implement any of these checks now?"

**User:** "Let's run the row count validation first and then check for foreign key issues."

*The assistant runs the row count validation and foreign key checks*

"I've found several integrity issues:

1. The `order_lines` table has 3,842 orphaned records with no matching order_id
2. The `customer_addresses` table has 275 fewer rows than expected
3. The `product_attributes` table has duplicate entries for some products

These need to be addressed before proceeding with optimization."

#### Step 3: Index and Query Optimization

**User:** "We've fixed those data issues. Now let's focus on optimizing the database for our workload."

*The assistant runs:*
```
get_top_queries
analyze_workload_indexes
```

"Based on your query patterns, I've identified these optimization opportunities:

1. **Missing indexes on foreign keys:**
```sql
CREATE INDEX idx_order_lines_order_id ON order_lines(order_id);
CREATE INDEX idx_order_lines_product_id ON order_lines(product_id);
CREATE INDEX idx_transactions_customer_id ON transactions(customer_id);
```

2. **Timestamp query optimization:**
```sql
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_user_events_timestamp ON user_events(event_timestamp);
```

3. **Text search improvements:**
```sql
-- For product search functionality
CREATE INDEX idx_products_name_gin ON products USING gin(name gin_trgm_ops);
CREATE EXTENSION pg_trgm;
```

4. **Missing primary keys:**
```sql
ALTER TABLE log_entries ADD PRIMARY KEY (id);
ALTER TABLE temporary_uploads ADD PRIMARY KEY (id);
```

5. **Query rewriting opportunities:**
Several queries are using `COUNT(*)` over entire tables which can be optimized by using smaller indexed columns.

Would you like me to implement these optimizations?"

#### Step 4: Configuration Tuning

**User:** "Yes, please implement those index changes. What about PostgreSQL-specific configuration tuning we should consider?"

**Assistant:**
"Now let's tune your PostgreSQL configuration to match your workload characteristics:

1. **Memory configuration:**
```sql
-- Check current settings
SHOW shared_buffers;
SHOW work_mem;
SHOW maintenance_work_mem;
SHOW effective_cache_size;
```

Given your server has 32GB RAM and this is a dedicated database server, I recommend:

```
shared_buffers = 8GB         # 25% of RAM
work_mem = 64MB              # Higher for complex sorts and joins
maintenance_work_mem = 512MB # Higher for VACUUM operations
effective_cache_size = 24GB  # 75% of RAM
```

2. **Write performance:**
```
wal_buffers = 16MB           # Helps with write-heavy workloads
checkpoint_completion_target = 0.9  # Spreads out checkpoint writes
```

3. **Query planning:**
```
random_page_cost = 1.1       # For SSD storage
effective_io_concurrency = 200  # For SSD storage
```

4. **Autovacuum tuning:**
```
autovacuum_vacuum_scale_factor = 0.05  # More aggressive vacuuming
autovacuum_analyze_scale_factor = 0.02  # More frequent statistics updates
```

These settings should be added to your postgresql.conf file."

#### Step 5: Migration-Specific Optimizations

**User:** "Are there any MySQL-to-PostgreSQL specific optimizations we should consider?"

**Assistant:**
"Yes, there are several MySQL-to-PostgreSQL migration-specific optimizations:

1. **Update application query patterns:**
   - Replace `LIMIT x,y` with PostgreSQL's `OFFSET x LIMIT y`
   - Replace `IF()` with `CASE WHEN` expressions
   - Update `GROUP_CONCAT()` functions with PostgreSQL's `string_agg()`

2. **Review and update data types:**
   - Replace `UNSIGNED` integer types with appropriate PostgreSQL types
   - Migrate `ENUM` types to PostgreSQL's native ENUM type or CHECK constraints
   - Update any `DATETIME` fields to use PostgreSQL's richer timestamp types

3. **Indexing differences:**
   - MySQL's implicit primary key indexes vs. PostgreSQL's explicit indexing
   - Consider using PostgreSQL-specific index types (GIN, BRIN, etc.) where appropriate

4. **Transaction isolation:**
   - MySQL's default isolation level (REPEATABLE READ) vs. PostgreSQL's default (READ COMMITTED)
   - Review transaction boundaries in your application code

5. **Text search functionality:**
   - Migrate from MySQL's fulltext search to PostgreSQL's more powerful full-text search
   ```sql
   CREATE INDEX idx_product_search ON products USING gin(to_tsvector('english', name || ' ' || description));
   ```

Would you like me to elaborate on any of these areas?"

### Expected Results

After completing this migration validation and optimization process:
- Verified data integrity with no loss during migration
- Optimized schema and indexes for PostgreSQL
- Configured server parameters for your specific workload
- Updated queries to leverage PostgreSQL-specific features
- Performance equal to or better than the original MySQL database
