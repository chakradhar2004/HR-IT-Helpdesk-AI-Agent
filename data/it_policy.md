# Enterprise Global IT Policies & Security Guidelines

Welcome to the Company IT Helpdesk and Information Security Knowledge Base. This document outlines mandatory technology standards, device refresh cadences, connectivity protocols, and access management requirements.

---

## Section 1: Virtual Private Network (VPN) and MFA Setup

### 1.1 Remote Access Requirement
All remote connections accessing internal enterprise resources (production databases, staging clusters, code repositories, intranet portals, and Jira/Confluence instances) must traverse the corporate **Cisco AnyConnect VPN** client.

### 1.2 Multi-Factor Authentication (MFA) Setup
Corporate authentication is governed by **Okta Verify**. To establish MFA:
1. Download Okta Verify on your company-managed or approved personal mobile smartphone from Google Play Store or Apple App Store.
2. Navigate to `https://sso.enterprise.internal` on your workstation and scan the displayed QR code using Okta Verify.
3. Configure biometric verification (Face ID / Fingerprint) and push notifications.
4. When logging into the VPN client, select the gateway `vpn.enterprise.internal`, provide your corporate Active Directory credentials, and approve the push notification prompt sent to your mobile device.

### 1.3 VPN Troubleshooting and Inactivity Timeout
The VPN session will automatically disconnect after 8 hours of continuous connection or 30 minutes of idle inactivity. If you experience repeated disconnections, ensure IPv6 is disabled on your home router adapter and verify your clock synchronization.

---

## Section 2: Laptop and Hardware Replacement Cycle

### 2.1 Standard Replacement Cadence (3 Years / 36 Months)
All standard company-issued workstations (MacBook Pro, Dell Latitude/Precision, Lenovo ThinkPad) are subject to a **36-month (3-year) hardware replacement cycle**. 

### 2.2 Refresh Eligibility and Ordering Process
Employees become eligible to request a modern replacement unit 60 days prior to reaching the 36-month milestone from their machine's initial provisioning date. The IT Asset Management system automatically generates a notification to eligible employees with a link to choose their preferred workstation specification tier:
- Engineering / Data Tier: MacBook Pro 16" (M-series Pro/Max) or Dell Precision 32GB RAM.
- General / Business Tier: MacBook Pro 14" or Dell Latitude 16GB RAM.

### 2.3 Premature Hardware Failure or Accidental Damage
If a workstation suffers irreparable hardware breakdown, motherboard failure, or battery degradation under 70% before the 3-year refresh window, an IT ticket should be filed under category `Hardware`. If diagnosed as defective, IT will provide a hot-swap replacement within 24 to 48 business hours. Old assets must be returned to IT Operations within 14 calendar days of receiving the new unit.

---

## Section 3: Password and Credential Management Policy

### 3.1 Password Complexity Requirements
Corporate passwords must adhere to stringent complexity requirements:
- Minimum length of **14 characters**.
- Must contain at least one uppercase letter, one lowercase letter, one number, and one special character (e.g., `!@#$%^&*`).
- Must not contain dictionary words, usernames, or repetitive sequential patterns (e.g., `Passw0rd1234!`).

### 3.2 90-Day Rotation Schedule
Passwords for Active Directory, VPN, and corporate SSO accounts expire every **90 calendar days**. Automated warning notifications will be emailed 14, 7, and 1 day prior to expiration. The system prevents reuse of the previous 10 passwords.

### 3.3 Zero Tolerance for Password Sharing
Under no circumstances may passwords, API keys, SSH private keys, or MFA tokens be shared via email, Slack, or verbal communication. Violations will result in immediate suspension of network credentials and HR escalation.

---

## Section 4: Device Security, Incident Reporting, and BYOD

### 4.1 Lost or Stolen Device Protocol
If a company-managed laptop or mobile device enrolled in MDM is lost or stolen, the employee must contact IT Security (`security@enterprise.internal` or emergency hotline `+1-800-555-0199`) within **two (2) hours**. IT will initiate an immediate remote cryptographic wipe.

### 4.2 Endpoint Protection and Disk Encryption
All company laptops are protected by CrowdStrike Falcon EDR and FileVault (macOS) or BitLocker (Windows). Disabling endpoint telemetry or disk encryption is strictly prohibited.
