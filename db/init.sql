-- Schema Definition for HR/IT Helpdesk
DROP TABLE IF EXISTS it_tickets;
DROP TABLE IF EXISTS employees;

CREATE TABLE employees (
    emp_id VARCHAR(20) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    department VARCHAR(50) NOT NULL,
    role VARCHAR(100) NOT NULL,
    annual_leave_balance INT NOT NULL,
    sick_leave_balance INT NOT NULL,
    laptop_asset_id VARCHAR(50) NOT NULL,
    manager_name VARCHAR(100) NOT NULL
);

CREATE TABLE it_tickets (
    ticket_id VARCHAR(20) PRIMARY KEY,
    emp_id VARCHAR(20) NOT NULL REFERENCES employees(emp_id),
    issue_category VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Realistic Seed Data: Employees
INSERT INTO employees (emp_id, full_name, email, phone, department, role, annual_leave_balance, sick_leave_balance, laptop_asset_id, manager_name) VALUES
('EMP101', 'Alice Johnson', 'alice.johnson@enterprise.internal', '+1-555-012-3456', 'Engineering', 'Senior Backend Engineer', 18, 8, 'LPTP-MAC-2024-01', 'Marcus Vance'),
('EMP102', 'Bob Smith', 'bob.smith@enterprise.internal', '+1-555-014-9876', 'Marketing', 'Lead Growth Strategist', 12, 5, 'LPTP-DELL-8821', 'Sarah Jenkins'),
('EMP103', 'Carlos Davis', 'carlos.davis@enterprise.internal', '+1-555-019-2834', 'Finance', 'Financial Analyst', 22, 10, 'LPTP-LEN-5510', 'Elena Rostova'),
('EMP104', 'Diana Prince', 'diana.prince@enterprise.internal', '+1-555-017-4321', 'Product', 'Principal Product Manager', 15, 6, 'LPTP-MAC-2023-09', 'Marcus Vance'),
('EMP105', 'Evan Lee', 'evan.lee@enterprise.internal', '+1-555-018-7654', 'Human Resources', 'HR Operations Specialist', 14, 7, 'LPTP-DELL-9940', 'Karen White');

-- Realistic Seed Data: IT Tickets
INSERT INTO it_tickets (ticket_id, emp_id, issue_category, description, status, created_at) VALUES
('TKT-001', 'EMP101', 'Software Access', 'Request for staging Kubernetes cluster and Datadog read access.', 'RESOLVED', '2026-10-15 09:30:00'),
('TKT-002', 'EMP102', 'Hardware', 'Secondary external monitor flickers intermittently when connected via USB-C dock.', 'OPEN', '2026-11-10 14:15:00'),
('TKT-003', 'EMP102', 'Network', 'Okta MFA push notification delayed on mobile device during remote login.', 'IN_PROGRESS', '2026-11-12 11:00:00'),
('TKT-004', 'EMP103', 'Software Access', 'Need license key update for Tableau Desktop financial forecasting workbook.', 'RESOLVED', '2026-10-28 16:45:00'),
('TKT-005', 'EMP104', 'Hardware', 'Laptop battery health degraded below 70%, requesting battery diagnostic or swap.', 'OPEN', '2026-11-14 10:20:00'),
('TKT-006', 'EMP105', 'Account Security', 'Password expiration notification received; requesting guidance on SSO sync.', 'RESOLVED', '2026-11-01 13:00:00');
