# Smart Home Management System

[中文](./README_zh.md) | English

A Vue 3 + Vite + Element Plus based smart home management frontend. Monitor network devices, manage cameras, view analytics, and more.

## Features

### Dashboard
Overview of home status including members present, camera status, network devices, today's recordings, and unknown device alerts. Real-time activity feed shows recent events.

![Dashboard](./screenshots/dashboard.png)

### Device Management
Browse and manage all network devices. Filter by device type (camera, computer, phone, IoT, router, etc.), search by MAC/IP/hostname, and view device details.

![Devices](./screenshots/devices.png)

### Camera Management
Full-featured camera management with ONVIF protocol support. Preview live streams (MJPEG/HLS), take snapshots, start/stop recording, and probe camera capabilities.

![Cameras](./screenshots/cameras.png)

### Analytics
Comprehensive analytics dashboard with multiple chart types:
- **Heatmap**: Device activity by hour/day
- **Online Trend**: Device online/offline trends over time
- **Device Type Distribution**: Donut chart of device categories
- **Recording Calendar**: GitHub-style calendar of recording activity
- **Response Time**: Horizontal bar chart of device latency
- **Stability**: Device uptime percentage
- **Type Activity**: Grouped bar chart comparing activity across device types

![Analytics](./screenshots/analytics.png)

### Recordings
Browse, play, download, and delete camera recordings. Filter by camera and date. View recording statistics including total count, duration, and storage size.

![Recordings](./screenshots/recordings.png)

### Members
Track household members and their check-in/check-out events.

![Members](./screenshots/members.png)

### DLNA / Cast
Discover and manage DLNA rendering devices for media casting.

![DLNA](./screenshots/dlna.png)

### Schedule
Configure automated tasks and schedules.

![Schedule](./screenshots/schedule.png)

### Topology
Visualize network topology and device connections.

![Topology](./screenshots/topology.png)

### Settings
System configuration and preferences.

![Settings](./screenshots/settings.png)

## Tech Stack

- **Vue 3** with Composition API (`<script setup>`)
- **Vite** for build tooling
- **Element Plus** UI component library
- **Pinia** state management
- **Vue Router** for routing
- **Vue I18n** for internationalization
- **D3.js** for data visualization (charts)
- **Video.js** for HLS video playback

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Project Structure

```
src/
├── api/            # API client modules
├── components/     # Reusable Vue components
│   ├── charts/     # D3.js chart components
│   └── ...
├── stores/         # Pinia stores
├── views/          # Page-level components
├── router/         # Vue Router configuration
├── composables/    # Vue composables
├── locales/        # i18n translation files
└── assets/         # Static assets
```

---

[中文](./README_zh.md)
```