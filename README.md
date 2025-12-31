# 🚌 FleetTrack: Enterprise IoT-Driven Bus Tracking System

**FleetTrack** is a high-performance, real-time fleet management solution specifically engineered for university transit systems. By integrating **IoT hardware (ESP32)** with a robust **Django backend**, the system provides seamless real-time tracking, intelligent route progress monitoring, and enterprise-grade security.

---

## 🚀 Key Features

### 📡 Real-Time Synchronization
* **WebSocket Integration:** Powered by **Django Channels** and **Redis** for sub-second latency in location updates.
* **Live Progress Timeline:** Automatically tracks bus movement through stops and updates users on current status (On Trip, Ready, or At Stop).

### 🧠 Smart Logic Engine
* **Automatic Direction Detection:** Intelligent algorithms detect if the bus is heading toward the campus or the city based on GPS coordinates and terminal proximity.
* **Stop-by-Stop Progress:** Real-time sequence tracking to update students on exactly which stop the bus has reached.
* **Traffic Intensity Analytics:** Real-time speed analysis to categorize traffic as Normal, Medium, or Heavy.

### 🔐 Multi-Layer Security
* **Hardware Security:** IoT devices utilize unique, dynamically generated **API Keys** for data ingestion.
* **User Authentication:** **JWT (JSON Web Token)** based authentication for Web and Mobile applications, including Token Blacklisting upon logout.
* **Authorized Access:** Restricted registration to University **Edu-Mails** to ensure only verified students can access tracking data.

### ⚙️ Performance & Scalability
* **Asynchronous Task Queue:** Heavy database writes and broadcasting tasks are offloaded to **Celery Workers** to maintain high API responsiveness.
* **Atomic Transactions:** Ensures data integrity by using `transaction.atomic` for synchronized updates between live state and history logs.
* **Redis Caching:** Minimizes database hits by caching live bus states in memory.

---

## 🏗 System Architecture

```text
[ IoT Device ] ----(POST + API Key)----> [ Django REST API ]
                                              |
                                     [ Celery Async Worker ]
                                              |
                     +------------------------+-----------------------+
                     |                        |                       |
            [ PostgreSQL DB ]          [ Redis Cache ]        [ Sentry Monitoring ]
             (History Logs)            (Live Tracking)         (Error Tracking)
                     |                        |                       |
                     +------------------------+-----------------------+
                                              |
                                    [ Django Channels ]
                                              |
                             [ Web / Mobile Clients (JWT Auth) ]
                            

```

## 🛠 Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python, Django 5.x, Django REST Framework |
| **Real-time** | Django Channels, WebSockets, Redis |
| **Tasks/Queue**| Celery, Celery Beat |
| **Database** | PostgreSQL, Redis (Caching) |
| **Frontend** | HTML5, Tailwind CSS, Leaflet.js |
| **Monitoring** | Sentry.io SDK |
| **Infrastructure**| Docker-ready, Coolify, Systemd |

---

## 📈 Device Health Monitoring

The system monitors critical hardware metrics in real-time to ensure maximum uptime and data reliability:

*   **GSM Signal Strength (RSSI):** Visual indicators for network reliability and connection stability.
*   **Battery Voltage Level:** Real-time monitoring of the bus-mounted device's power status to prevent unexpected downtime.
*   **Satellite Count:** Monitors GPS fix quality to ensure high precision in location coordinates.

