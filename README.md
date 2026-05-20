# Weighbridge SaaS Backend — The Complete API & Admin Manual

This manual provides a detailed technical breakdown of every API endpoint in the Weighbridge SaaS ecosystem. It is intended for the Frontend, Mobile (Flutter), and QA teams to understand the logic, purpose, and usage of the backend services.

---

## 🏗 System Architecture & Concepts
To understand the APIs, you must understand these core entities:
*   **App (Software Product)**: A specific software version or tier (e.g., "Standard Tier", "Enterprise V2").
*   **Activation Key (License)**: A unique token sold to a client (Company). It links a physical machine to a product and a set of configurations (Branding, SMTP, WhatsApp).
*   **Machine**: A physical weighbridge terminal. It identifies itself using the `ActivationKey.token`.
*   **Receipt**: A record of a vehicle weightment. Synced from the machine to the cloud.

---

## 🔄 The Lifecycle: How It Works
To give the frontend team a clear picture, here is the end-to-end workflow of the system:

### 1. The Onboarding (Admin Flow)
*   **Step A**: The Super Admin creates a **Product (App)** (e.g., "Industrial Weigh 1.0").
*   **Step B**: When a client buys the software, the Admin generates an **Activation Key**.
*   **Step C**: The Admin configures the client's **Branding** (Logo, Company Name) and **Comms** (SMTP/WhatsApp).
*   **Step D**: The system sends the Activation Key to the client via Email/WhatsApp automatically.

### 2. The Activation (Device Flow)
*   **Step A**: The client opens the software on their physical machine and enters the **Activation Key**.
*   **Step B**: The machine calls the **Sync Config** API. It downloads its branding, header/footer text, and security token.
*   **Step C**: The machine is now "Paired" and shows as **ACTIVE** on the Admin Dashboard.

### 3. Daily Operations (The Weightment)
*   **Step A**: A truck arrives. The operator weighs it. A **Receipt** is created *locally* on the machine's database (SQLite).
*   **Step B**: The machine's background worker periodically calls the **Sync Receipts** API to push batches of receipts to the Cloud (PostgreSQL).
*   **Step C**: For every receipt received, the Cloud backend checks the client's settings and triggers a **WhatsApp/Email notification** to the truck owner with a PDF link.

### 4. Continuous Monitoring (Super Admin)
*   **Step A**: If a machine goes offline, the Admin sees the status change on the dashboard.
*   **Step B**: If a WhatsApp message fails (e.g., invalid number), it lands in the **DLQ (Dead Letter Queue)**. The Admin can fix the number and click **Retry**.
*   **Step C**: The Admin can search for any truck number globally to verify its weightment history across different sites.

---

## 🔐 1. Authentication APIs

### 👨‍💼 Admin Authentication (Web Panel)
Used by the SaaS Super Admins to manage the entire platform.

| API Name | Endpoint | Method | Purpose | What it does |
| :--- | :--- | :--- | :--- | :--- |
| **Login Initiation** | `/admin/auth/login` | `POST` | Start the login process. | Validates email/password and sends a 6-digit OTP to the admin's email. |
| **Verify OTP** | `/admin/auth/verify-otp` | `POST` | Complete login. | Verifies the OTP and returns a JWT Bearer Token for all other `/admin` routes. |
| **Seed Admin** | `/admin/auth/seed` | `POST` | System Setup. | Creates the initial default admin account (only used once during deployment). |

### 👷 Employee Authentication (Flutter Device)
Used by weighbridge operators on the field.

| API Name | Endpoint | Method | Purpose | What it does |
| :--- | :--- | :--- | :--- | :--- |
| **Operator Login** | `/employee/login` | `POST` | Device login. | Authenticates operators via username/email + password. Returns a 24h JWT. |
| **Get My Profile** | `/employee/me` | `GET` | Profile sync. | Returns the current operator's name, role, and company link. |
| **Self Register** | `/employee/register` | `POST` | Easy onboarding. | Allows an operator to create their account directly on an activated machine. |

---

## 🛠 2. Admin Dashboard & Product Management

### 📊 Dashboard Monitoring
| API Name | Endpoint | Method | Purpose | What it does |
| :--- | :--- | :--- | :--- | :--- |
| **Get Stats** | `/admin/apps/dashboard/stats` | `GET` | Summary Cards. | Returns total counts of Apps, Keys, Receipts, and Active Machines. |
| **Activity Chart** | `/admin/apps/dashboard/activity` | `GET` | Growth Chart. | Returns day-by-day counts of activations/revocations for the last 10 days. |

### 📦 App (Product) Management
| API Name | Endpoint | Method | Purpose | What it does |
| :--- | :--- | :--- | :--- | :--- |
| **List Apps** | `/admin/apps` | `GET` | Product Catalog. | Returns all software versions/products created in the system. |
| **Create App** | `/admin/apps` | `POST` | New Product. | Define a new software tier (name, description, notification settings). |
| **Update App** | `/admin/apps/{id}` | `PATCH` | Edit Product. | Update product names or global notification templates. |
| **Delete App** | `/admin/apps/{id}` | `DELETE` | Retirement. | Soft-deletes a product from the active catalog. |

---

## 🔑 3. License & Machine Management

### 🎫 Activation Keys (Company Licenses)
| API Name | Endpoint | Method | Purpose | What it does |
| :--- | :--- | :--- | :--- | :--- |
| **Generate Keys** | `/admin/apps/keys` | `POST` | Sales/Onboarding. | Generates new license tokens for a specific company and email/WhatsApp notifications. |
| **List All Keys** | `/admin/apps/keys/all` | `GET` | Global Audit. | Shows every license key ever generated across all companies. |
| **Update License** | `/admin/apps/keys/{id}` | `PATCH` | Branding/Settings. | Change company logo, custom labels, or SMTP/WhatsApp channel for a specific client. |
| **Rotate Token** | `/admin/apps/keys/{id}/rotate-token` | `PATCH` | Security. | Generates a new machine token if the old one is compromised (1-hour grace period). |
| **Revoke License** | `/admin/apps/keys/{id}/revoke` | `DELETE` | Subscription Stop. | Permanently disables a license key; the machine will stop syncing. |

---

## 📊 4. Data & Operational APIs

### 🚛 Receipt Monitoring
| API Name | Endpoint | Method | Purpose | What it does |
| :--- | :--- | :--- | :--- | :--- |
| **Global Search** | `/admin/receipts` | `GET` | Universal Search. | Search all receipts by truck number, date range, or sync status across all tenants. |
| **Receipt Detail** | `/admin/receipts/{id}` | `GET` | Deep Dive. | View the full JSON data of a single weightment receipt. |
| **Machine List** | `/admin/apps/{id}/machines` | `GET` | Drill-down. | Shows all machines registered under a specific product version. |

### ✉️ Document Delivery & DLQ (Dead Letter Queue)
| API Name | Endpoint | Method | Purpose | What it does |
| :--- | :--- | :--- | :--- | :--- |
| **Delivery Logs** | `/documents/logs` | `GET` | Transparency. | View every Email and WhatsApp message sent for receipts. |
| **DLQ List** | `/admin/dlq` | `GET` | Error Handling. | Shows all failed notifications (e.g., wrong phone number or SMTP down). |
| **Retry DLQ** | `/admin/dlq/{id}/retry` | `POST` | Recovery. | Re-triggers a failed notification back into the queue for delivery. |

---

## ☁️ 5. Device Sync & Public Access

### 🔄 Device Synchronization
Used by the Physical Machine to communicate with the Cloud.

| API Name | Endpoint | Method | Purpose | What it does |
| :--- | :--- | :--- | :--- | :--- |
| **Sync Receipts** | `/sync/receipts` | `POST` | Data Uplink. | Batches multiple receipts from the local machine to the cloud. Secured by HMAC. |
| **Get Config** | `/sync/config` | `GET` | Remote Update. | Machine pulls latest branding (Logo, Labels) and settings from the cloud. |

### 🔗 Public Sharing
Used by truck drivers and third parties to view their weightment.

| API Name | Endpoint | Method | Purpose | What it does |
| :--- | :--- | :--- | :--- | :--- |
| **Web Preview** | `/r/{share_token}` | `GET` | Public View. | Returns a beautiful HTML page showing the receipt data. No login required. |
| **Download PDF** | `/r/{share_token}/pdf` | `GET` | Official Doc. | Generates a branded PDF of the receipt for printing or storage. |

---

## 🎨 6. Assets & Branding
| API Name | Endpoint | Method | Purpose | What it does |
| :--- | :--- | :--- | :--- | :--- |
| **Upload Logo** | `/admin/upload/logo` | `POST` | Customization. | Upload a company logo to the CDN and get back a public URL. |
| **Signup Image** | `/admin/upload/signup` | `POST` | UI Polish. | Upload background/illustration images for the login/signup screens. |

---

## 🛠 Postman / cURL Operations (Quick Reference)

### 1. Admin Login & OTP Flow
```bash
# 1. Login
curl -X POST "http://localhost:8000/admin/auth/login" -d "username=admin@weighbridge.com&password=Admin123!"

# 2. Verify (Copy OTP from your email/logs)
curl -X POST "http://localhost:8000/admin/auth/verify-otp" -H "Content-Type: application/json" -d '{"email": "admin@weighbridge.com", "otp": "123456"}'
```

### 2. Fetch Dashboard Statistics
```bash
curl -X GET "http://localhost:8000/admin/apps/dashboard/stats" -H "Authorization: Bearer <YOUR_JWT_TOKEN>"
```

### 3. Search Receipts by Truck No
```bash
curl -X GET "http://localhost:8000/admin/receipts?search=MP09&page=1&limit=20" -H "Authorization: Bearer <YOUR_JWT_TOKEN>"
```

---

## 💡 Frontend Tips
1.  **JWT Handling**: Store the `access_token` in Secure Storage (Mobile) or HttpOnly Cookies/LocalStorage (Web). Include it in the `Authorization: Bearer <token>` header.
2.  **Pagination**: Most list APIs support `page` and `limit` query parameters. Use them to implement infinite scroll or pagination buttons.
3.  **Real-time Branding**: When the Admin updates a logo via `/admin/upload/logo`, save the returned URL in the `ActivationKey` update. The physical machine will see this update next time it calls `/sync/config`.
4.  **Error Handling**: If an API returns `401`, redirect to the login page immediately. If it returns `403`, the user doesn't have permission for that action.
