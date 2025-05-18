
-- Create the database (note: this is usually done outside of the script in PostgreSQL)
-- CREATE DATABASE product_website;

-- Connect to the database
-- \c product_website;

-- Table: Subscription Plans
CREATE TABLE IF NOT EXISTS plans (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  features JSON NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO plans (name, price, features) VALUES
('Basic Tier', 2500.00, '["Up to 100 devices", "30-Day data retention", "3 admin accounts", "Standard ML models", "Email and chat support"]'::json),
('Professional Tier', 5000.00, '["Up to 500 devices", "90-day data retention", "10 admin accounts", "Advanced ML models", "Priority support"]'::json),
('Enterprise Tier', 9000.00, '["Unlimited devices", "Custom data retention policies", "Unlimited admin accounts", "Custom ML models", "24/7 dedicated support"]'::json);

-- Table: User Reviews
CREATE TABLE IF NOT EXISTS reviews (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  rating INT CHECK (rating BETWEEN 1 AND 5),
  comment TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO reviews (name, rating, comment) VALUES
('Alice', 5, 'NetDash greatly enhanced our visibility.'),
('Bob', 4, 'Stable and powerful IDS dashboard. Recommended!');

-- Table: Homepage Features
CREATE TABLE IF NOT EXISTS features (
  id SERIAL PRIMARY KEY,
  title VARCHAR(150) NOT NULL,
  description TEXT NOT NULL
);

INSERT INTO features (title, description) VALUES
('AI-Powered Threat Detection', 'Analyze network traffic using ML to identify threats early.'),
('Real-Time Monitoring', 'Live dashboards and alerting system for real-time visibility.'),
('Automated Incident Response', 'Automatically mitigate common threats with configured responses.'),
('Anomaly Detection', 'Detect unusual patterns with behavior analytics.'),
('Comprehensive Reporting', 'Generate reports for audits and compliance.'),
('Network-Wide Integration', 'Integrate with existing security tools and infrastructure.');

-- Table: Download Options
CREATE TABLE IF NOT EXISTS downloads (
  id SERIAL PRIMARY KEY,
  plan_id INT REFERENCES plans(id) ON DELETE CASCADE,
  os_name VARCHAR(50),
  download_link VARCHAR(255)
);

INSERT INTO downloads (plan_id, os_name, download_link) VALUES
(1, 'Windows', '#'),
(1, 'Linux', '#'),
(1, 'macOS', '#'),
(1, 'Docker', '#'),
(2, 'Windows', '#'),
(2, 'Linux', '#'),
(2, 'macOS', '#'),
(2, 'Docker', '#');

-- Table: Guides
CREATE TABLE IF NOT EXISTS guides (
  id SERIAL PRIMARY KEY,
  type VARCHAR(50),
  title VARCHAR(150) NOT NULL,
  link VARCHAR(255) NOT NULL
);

INSERT INTO guides (type, title, link) VALUES
('guide', 'Getting Started Guide', '#'),
('tutorial', 'Tutorials', '#'),
('api', 'API Documentation', '#'),
('features', 'Feature Guides', '#');

-- Table: Users
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(100) UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) CHECK (role IN ('platform_admin', 'company_admin')) DEFAULT 'company_admin',
  is_suspended BOOLEAN DEFAULT FALSE,
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Demo insertions
INSERT INTO users (name, email, password_hash, role, first_name, last_name) VALUES
('Platform Admin', 'admin@netdash.com', 'admin123', 'platform_admin', 'Platform', 'Admin'),
('Alice Company', 'alice@company.com', 'alicepass', 'company_admin', 'Alice', 'Company'),
('Bob Company', 'bob@company.com', 'bobpass', 'company_admin', 'Bob', 'Company');

-- Table: Purchases
CREATE TABLE IF NOT EXISTS purchases (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id) ON DELETE CASCADE,
  plan_id INT REFERENCES plans(id) ON DELETE CASCADE,
  amount DECIMAL(10,2) NOT NULL,
  status VARCHAR(20) CHECK (status IN ('pending', 'completed', 'failed', 'refunded')) DEFAULT 'pending',
  purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: Demo Sessions
CREATE TABLE IF NOT EXISTS demo_sessions (
  id SERIAL PRIMARY KEY,
  token VARCHAR(255) UNIQUE NOT NULL,
  email VARCHAR(255),
  expiry_time TIMESTAMP NOT NULL,
  features_accessed JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO demo_sessions (token, email, expiry_time, features_accessed) VALUES
('sample_demo_token_123', 'demo@example.com', NOW() + interval '1 hour', '["monitoring", "threats"]'::json);

-- Table: Contacts
CREATE TABLE IF NOT EXISTS contacts (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  message TEXT NOT NULL,
  status VARCHAR(20) CHECK (status IN ('new', 'responded', 'closed')) DEFAULT 'new',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO contacts (name, email, message, status) VALUES
('John Doe', 'john@example.com', 'I need more information about the Enterprise plan.', 'new'),
('Jane Smith', 'jane@example.com', 'Having issues with the dashboard.', 'new'),
('Mark Wilson', 'mark@example.com', 'Interested in a custom solution.', 'new');


-- Fix column names (PostgreSQL syntax uses RENAME COLUMN)
ALTER TABLE users RENAME COLUMN suspended TO is_suspended;
ALTER TABLE users RENAME COLUMN password TO password_hash;

-- Add missing columns (check manually since PostgreSQL doesn't support IF NOT EXISTS for columns directly)
DO $$ BEGIN
    BEGIN
        ALTER TABLE users ADD COLUMN first_name VARCHAR(100);
    EXCEPTION WHEN duplicate_column THEN END;
    BEGIN
        ALTER TABLE users ADD COLUMN last_name VARCHAR(100);
    EXCEPTION WHEN duplicate_column THEN END;
END $$;

-- Update existing data for first_name and last_name
UPDATE users SET 
    first_name = split_part(name, ' ', 1),
    last_name = split_part(name, ' ', 2)
WHERE name IS NOT NULL;

-- Add created_at and updated_at columns to users and is_active to plans
DO $$ BEGIN
    BEGIN
        ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    EXCEPTION WHEN duplicate_column THEN END;
    BEGIN
        ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    EXCEPTION WHEN duplicate_column THEN END;
    BEGIN
        ALTER TABLE plans ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
    EXCEPTION WHEN duplicate_column THEN END;
END $$;

-- Create email configuration table
CREATE TABLE IF NOT EXISTS email_config (
    id SERIAL PRIMARY KEY,
    smtp_server VARCHAR(255) DEFAULT 'smtp.gmail.com',
    smtp_port INT DEFAULT 587,
    smtp_username VARCHAR(255),
    smtp_password VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert static pricing plans (if not exists workaround)
INSERT INTO plans (id, name, price, features, is_active)
VALUES
(101, 'Basic Tier', 2500.00, '["Up to 100 devices", "30-Day data retention", "3 admin accounts", "Standard ML models", "Email and chat support"]', TRUE),
(102, 'Professional Tier', 5000.00, '["Up to 500 devices", "90-day data retention", "10 admin accounts", "Advanced ML models", "Priority support"]', TRUE),
(103, 'Enterprise Tier', 9000.00, '["Unlimited devices", "Custom data retention policies", "Unlimited admin accounts", "Custom ML models", "24/7 dedicated support"]', TRUE)
ON CONFLICT (id) DO NOTHING;
