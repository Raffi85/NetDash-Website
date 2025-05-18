
-- Create the database
CREATE DATABASE IF NOT EXISTS product_website;
USE product_website;

-- Table: Subscription Plans
CREATE TABLE plans (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  features TEXT NOT NULL -- store as JSON string
);

INSERT INTO plans (name, price, features) VALUES
('Standard', 29.99, '["Real-Time Monitoring", "Threat Detection", "Weekly Reports"]'),
('Enterprise', 79.99, '["Multi-IDS Support", "Daily Reports", "Priority Support", "Full Dashboard Access"]');

-- Table: User Reviews
CREATE TABLE reviews (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  rating INT CHECK (rating BETWEEN 1 AND 5),
  comment TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO reviews (name, rating, comment) VALUES
('Alice', 5, 'NetDash greatly enhanced our visibility.'),
('Bob', 4, 'Stable and powerful IDS dashboard. Recommended!');

-- Table: Homepage Features
CREATE TABLE features (
  id INT AUTO_INCREMENT PRIMARY KEY,
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
CREATE TABLE downloads (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT,
  os_name VARCHAR(50),
  download_link VARCHAR(255),
  FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
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

-- Table: Guides (Documentation / Tutorials)
CREATE TABLE guides (
  id INT AUTO_INCREMENT PRIMARY KEY,
  type VARCHAR(50), -- guide, tutorial, api, etc.
  title VARCHAR(150) NOT NULL,
  link VARCHAR(255) NOT NULL
);

INSERT INTO guides (type, title, link) VALUES
('guide', 'Getting Started Guide', '#'),
('tutorial', 'Tutorials', '#'),
('api', 'API Documentation', '#'),
('features', 'Feature Guides', '#');

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(100),
    role ENUM('platform_admin', 'company_admin'),
    suspended BOOLEAN DEFAULT FALSE
);

INSERT INTO users (name, email, password, role) VALUES
('Platform Admin', 'admin@netdash.com', 'admin123', 'platform_admin'),
('Alice Company', 'alice@company.com', 'alicepass', 'company_admin'),
('Bob Company', 'bob@company.com', 'bobpass', 'company_admin');

USE product_website;

-- Fix column names
ALTER TABLE users CHANGE COLUMN suspended is_suspended BOOLEAN DEFAULT FALSE;
ALTER TABLE users CHANGE COLUMN password password_hash VARCHAR(255) NOT NULL;

-- Add missing columns
ALTER TABLE users ADD COLUMN first_name VARCHAR(100);
ALTER TABLE users ADD COLUMN last_name VARCHAR(100);

-- Update existing data
UPDATE users SET 
    first_name = SUBSTRING_INDEX(name, ' ', 1),
    last_name = SUBSTRING_INDEX(name, ' ', -1)
WHERE name IS NOT NULL;

USE product_website;

-- Add missing columns to existing tables
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Create purchases table
CREATE TABLE IF NOT EXISTS purchases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    plan_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status ENUM('pending', 'completed', 'failed', 'refunded') DEFAULT 'pending',
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- Create demo sessions table
CREATE TABLE IF NOT EXISTS demo_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    expiry_time TIMESTAMP NOT NULL,
    features_accessed JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create email configuration table
CREATE TABLE IF NOT EXISTS email_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    smtp_server VARCHAR(255) DEFAULT 'smtp.gmail.com',
    smtp_port INT DEFAULT 587,
    smtp_username VARCHAR(255),
    smtp_password VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert some sample plans if they don't exist

-- Insert sample demo data (optional)
INSERT IGNORE INTO demo_sessions (token, email, expiry_time, features_accessed) VALUES
('sample_demo_token_123', 'demo@example.com', DATE_ADD(NOW(), INTERVAL 1 HOUR), '["monitoring", "threats"]');

-- Verify tables were created
SHOW TABLES;

-- Check structure of key tables
DESCRIBE users;
DESCRIBE purchases;
DESCRIBE demo_sessions;
-- Insert updated static pricing plans
INSERT INTO plans (id, name, price, features) VALUES
(101, 'Basic Tier', 2500.00, '["Up to 100 devices", "30-Day data retention", "3 admin accounts", "Standard ML models", "Email and chat support"]'),
(102, 'Professional Tier', 5000.00, '["Up to 500 devices", "90-day data retention", "10 admin accounts", "Advanced ML models", "Priority support"]'),
(103, 'Enterprise Tier', 9000.00, '["Unlimited devices", "Custom data retention policies", "Unlimited admin accounts", "Custom ML models", "24/7 dedicated support"]');


-- Create contacts table
CREATE TABLE IF NOT EXISTS contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status ENUM('new', 'responded', 'closed') DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert some sample contacts for testing (optional)
INSERT INTO contacts (name, email, message, status) VALUES
('John Doe', 'john@example.com', 'I need more information about the Enterprise plan.', 'new'),
('Jane Smith', 'jane@example.com', 'Having issues with the dashboard.', 'new'),
('Mark Wilson', 'mark@example.com', 'Interested in a custom solution.', 'new');

