# PostgreSQL MCP Demo Scripts

This directory contains setup scripts for the PostgreSQL MCP Server advanced demo scenarios. Each script creates a specialized database with particular characteristics to demonstrate different capabilities of PostgreSQL MCP.

## Setup Requirements

Before running these scripts, make sure you have:

1. PostgreSQL installed and running (version 12 or higher recommended)
2. Superuser privileges to create databases and install extensions
3. At least 8GB of free RAM and 10GB of free disk space

## Setup Instructions

### 1. Create and populate the databases

Each script will create and populate a database with the scenarios described in the Demos.md file. You can run them individually:

```bash
# Create E-commerce Performance Optimization demo database
createdb ecommerce_optimization
psql ecommerce_optimization -f advanced_demo1_setup.sql

# Create Data Warehouse Query Optimization demo database
createdb datawarehouse_optimization
psql datawarehouse_optimization -f advanced_demo2_setup.sql

# Create Database Migration Validation demo database
createdb migration_validation
psql migration_validation -f advanced_demo3_setup.sql

# Create Time-Series Data Management demo database
createdb timeseries_iot_demo
psql timeseries_iot_demo -f advanced_demo4_setup.sql
```

### 2. Resource considerations

These scripts create databases with:
- Large numbers of tables and rows
- Multiple indexes 
- Complex relationships
- Intentional performance issues (for demonstration purposes)

Each database requires significant resources:
- **E-commerce demo**: ~5GB disk space, 2GB+ RAM
- **Data warehouse demo**: ~8GB disk space, 4GB+ RAM
- **Migration validation demo**: ~2GB disk space, 1GB+ RAM
- **Time-series IoT demo**: ~3GB disk space, 2GB+ RAM

If you are running on a system with limited resources, you can modify the scripts to reduce the data volume by changing the number of rows generated in the `generate_series()` calls.

### 3. Demo script details

#### Advanced Demo 1: E-commerce Performance Optimization

The e-commerce demo creates a database simulating an online store with:
- Customer, product, and order data
- Performance issues with indexing
- Bloated tables from updates
- Inefficient queries

Use this to demonstrate:
- Performance analysis with `analyze_db_health`
- Query optimization with `explain_query`
- Index recommendations with `analyze_query_indexes`

#### Advanced Demo 2: Data Warehouse Query Optimization

The data warehouse demo creates a database simulating a star schema analytics database with:
- Fact and dimension tables
- Historical data (orders, inventory, sales targets)
- Slowly changing dimensions
- Complex analytical queries

Use this to demonstrate:
- Data warehouse query optimization
- Materialized views
- Partitioning recommendations
- Performance gains from progressive optimization

#### Advanced Demo 3: Database Migration Validation

The migration validation demo simulates a database that has been migrated from MySQL to PostgreSQL with common issues:
- Missing primary keys
- Foreign keys without indexes
- Inconsistent naming conventions
- Data type conversion issues
- Inefficient query patterns

Use this to demonstrate:
- Migration validation checks
- Schema structure improvements
- Performance optimization techniques specific to migrated databases

#### Advanced Demo 4: Time-Series Data Management

The time-series demo creates a database for IoT sensor data with:
- High-frequency sensor readings with timestamps
- TimescaleDB hypertable optimizations for time-series data
- Efficient vs. inefficient time-series query patterns
- Anomaly detection patterns
- Data retention and compression policies

Use this to demonstrate:
- Time-series specific optimizations with TimescaleDB integration
- Time-based partitioning and compression strategies
- Real-time analytics with continuous aggregates
- Statistical anomaly detection
- Efficient downsampling and rollup strategies

## Cleanup

After you're finished with the demos, you can remove the databases with:

```bash
dropdb ecommerce_optimization
dropdb datawarehouse_optimization
dropdb migration_validation
dropdb timeseries_iot_demo
```

## Advanced Usage

To modify the data volume in these scripts:

1. Open the script file and locate the `generate_series()` calls
2. Reduce the upper bound to generate less data
3. For example, change `FROM generate_series(1, 100000)` to `FROM generate_series(1, 10000)`

This will create a smaller database that requires fewer resources but still demonstrates the key features.
