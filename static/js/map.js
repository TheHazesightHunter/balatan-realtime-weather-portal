/**
 * Interactive Station Map
 * Syncs with AlertManager for coordinated alerts
 */

const StationMap = {
	map: null,
	markers: {},
	refreshTimer: null,
	lastUpdate: null,
	cssColors: null,
	thresholds: null,
	cachedWeatherData: null,
	lastSuccessfulFetch: null,
	consecutiveErrors: 0,
	isInitialized: false,

	stationCoordinates: {
		St1: {
			lat: 13.3483,
			lng: 123.2609,
			name: "Binudegahan Station",
			stationIds: ["St1"],
			active: true,
		},
		St2: {
			lat: 13.3464,
			lng: 123.2517,
			name: "Mang-it Station",
			stationIds: ["St2"],
			active: true,
		},
		St3: {
			lat: 13.3296,
			lng: 123.2481,
			name: "Laganac Station",
			stationIds: ["St3"],
			active: true,
		},
		St4: {
			lat: 13.31639,
			lng: 123.24003,
			name: "MDRRMO Weather Station",
			stationIds: ["St4"],
			active: true,
		},
		St5: {
			lat: 13.3235,
			lng: 123.2344,
			name: "Luluasan Station",
			stationIds: ["St5"],
			active: true,
		},
	},

	apiEndpoint: "/api/weather-data",
	cssApiEndpoint: "/api/css-variables",
	refreshInterval: 60000,

	async initialize() {
		if (this.isInitialized) return;

		try {
			this.loadConfig();
			await this.loadCSSVariables();
			await this.initializeMap();
			await this.updateAllStations();
			this.startAutoRefresh();
			this.isInitialized = true;
		} catch (error) {
			console.error("[MAP] Init failed:", error);
			this.showError("Failed to load map");
		}
	},

	loadConfig() {
		if (window.APP_CONFIG?.thresholds?.water_level) {
			this.thresholds = window.APP_CONFIG.thresholds.water_level;
		} else {
			this.thresholds = {
				advisory: 700,
				alert: 800,
				warning: 900,
				critical: 1000,
			};
		}
	},

	async loadCSSVariables() {
		try {
			const response = await fetch(this.cssApiEndpoint);
			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			const data = await response.json();
			this.cssColors = data.success ? data : null;
		} catch {
			this.cssColors = {
				flood_colors: {
					normal: "#10b981",
					advisory: "#0ea5e9",
					alert: "#eab308",
					warning: "#f59e0b",
					critical: "#dc2626",
				},
			};
		}
	},

	async initializeMap() {
		const loading = document.querySelector(".map-loading");
		if (loading) loading.classList.add("hidden");

		this.map = L.map("station-map", {
			center: [13.335841, 123.2508871],
			zoom: 13.0,
		});

		L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
			attribution: "© OpenStreetMap contributors",
			maxZoom: 19,
			minZoom: 10,
		}).addTo(this.map);

		this.addStyles();
	},

	async fetchWeatherData() {
		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), 10000);

		try {
			const response = await fetch(this.apiEndpoint, {
				headers: { Accept: "application/json" },
				signal: controller.signal,
			});

			clearTimeout(timeoutId);
			if (!response.ok) throw new Error(`HTTP ${response.status}`);

			const data = await response.json();
			let weatherData;

			if (Array.isArray(data)) {
				weatherData = data;
			} else if (data?.success && Array.isArray(data.data)) {
				weatherData = data.data;
			} else if (Array.isArray(data?.data)) {
				weatherData = data.data;
			} else {
				throw new Error("Invalid format");
			}

			this.cachedWeatherData = weatherData;
			this.lastSuccessfulFetch = new Date();
			this.consecutiveErrors = 0;

			return weatherData;
		} catch (error) {
			clearTimeout(timeoutId);
			this.consecutiveErrors++;

			if (this.cachedWeatherData) return this.cachedWeatherData;
			return [];
		}
	},

	getStationLatestReading(weatherData, stationKey) {
		if (!Array.isArray(weatherData) || !weatherData.length) return null;

		const config = this.stationCoordinates[stationKey];
		if (!config) return null;

		const readings = weatherData.filter((r) =>
			config.stationIds.includes(r.StationID)
		);
		if (!readings.length) return null;

		readings.sort((a, b) => {
			const timeA = new Date(a.DateTime || a.DateTimeStamp || 0);
			const timeB = new Date(b.DateTime || b.DateTimeStamp || 0);
			return timeB - timeA;
		});

		return readings[0];
	},

	async updateAllStations() {
		if (!this.cssColors) return;

		const weatherData = await this.fetchWeatherData();
		if (!weatherData?.length) return;

		Object.keys(this.stationCoordinates).forEach((key) => {
			const config = this.stationCoordinates[key];
			if (config.active) {
				this.updateStationMarker(key, config, weatherData);
			}
		});

		this.lastUpdate = new Date();

		if (window.AlertManager) {
			window.AlertManager.updateFromStationData(weatherData);
		}
	},

	updateStationMarker(stationKey, stationConfig, weatherData) {
		if (this.markers[stationKey]) {
			this.map.removeLayer(this.markers[stationKey]);
		}

		const data = this.getStationLatestReading(weatherData, stationKey);
		const alertLevel = data ? this.getAlertLevel(data.WaterLevel) : "normal";
		const isOnline = this.isStationOnline(data);
		const icon = this.createStationIcon(alertLevel, isOnline);

		const marker = L.marker([stationConfig.lat, stationConfig.lng], {
			icon,
		}).addTo(this.map);
		marker.bindPopup(
			this.buildPopupContent(
				stationKey,
				stationConfig,
				data,
				alertLevel,
				isOnline
			)
		);

		this.markers[stationKey] = marker;

		if (["critical", "warning"].includes(alertLevel) && window.AlertManager) {
			window.AlertManager.triggerAlert(
				stationKey,
				alertLevel,
				data?.WaterLevel
			);
		}
	},

	isStationOnline(data) {
		if (!data) return false;

		const timestamp = data.DateTime || data.DateTimeStamp;
		if (!timestamp) return false;

		const dataTime = new Date(timestamp);
		const now = new Date();
		const diffMinutes = (now - dataTime) / (1000 * 60);

		return diffMinutes <= 60;
	},

	buildPopupContent(stationKey, stationConfig, data, alertLevel, isOnline) {
		const statusBadge = isOnline
			? '<span style="color:#10b981;font-size:10px;">● Online</span>'
			: '<span style="color:#ef4444;font-size:10px;">● Offline</span>';

		let content = `
			<div class="station-popup" style="min-width:180px;">
				<h4 style="margin:0 0 4px 0;color:#1f2937;font-size:14px;font-weight:600;">
					${stationConfig.name}
				</h4>
				<div style="margin-bottom:8px;">${statusBadge}</div>
		`;

		if (data) {
			const alertColor = this.getAlertColor(alertLevel);
			const timeStr = this.formatTimestamp(data.DateTime || data.DateTimeStamp);

			const waterLevel = data.WaterLevel
				? parseFloat(data.WaterLevel).toFixed(1)
				: "--";
			const rainfall = data.HourlyRain
				? parseFloat(data.HourlyRain).toFixed(1)
				: "--";
			const dailyRain = data.DailyRain
				? parseFloat(data.DailyRain).toFixed(1)
				: "--";

			content += `
				<div style="font-size:11px;color:#6b7280;margin-bottom:8px;">
					Last Update: ${timeStr}
				</div>
				<div style="display:grid;gap:4px;font-size:12px;">
					<div><span style="color:#6b7280;">Water Level:</span> <strong style="color:${alertColor};">${waterLevel} cm</strong></div>
					<div><span style="color:#6b7280;">Rainfall:</span> <strong>${rainfall} mm/hr</strong></div>
					<div><span style="color:#6b7280;">Daily Rain:</span> <strong>${dailyRain} mm</strong></div>
				</div>
				<div style="margin-top:8px;padding:4px 8px;border-radius:4px;text-align:center;font-size:11px;font-weight:600;background:${alertColor}20;color:${alertColor};">
					${alertLevel.toUpperCase()}
				</div>
			`;
		} else {
			content += `<p style="color:#94a3b8;text-align:center;font-size:12px;">No data</p>`;
		}

		content += `
			<div style="margin-top:8px;text-align:center;">
				<a href="/sites/${stationKey}" style="color:#3b82f6;font-size:11px;font-weight:600;text-decoration:none;">View Details →</a>
			</div>
			</div>
		`;

		return content;
	},

	getAlertLevel(waterLevel) {
		if (!waterLevel) return "normal";
		const level = parseFloat(waterLevel);

		if (level >= this.thresholds.critical) return "critical";
		if (level >= this.thresholds.warning) return "warning";
		if (level >= this.thresholds.alert) return "alert";
		if (level >= this.thresholds.advisory) return "advisory";
		return "normal";
	},

	getAlertColor(alertLevel) {
		const colors = this.cssColors?.flood_colors || {
			critical: "#dc2626",
			warning: "#f59e0b",
			alert: "#eab308",
			advisory: "#0ea5e9",
			normal: "#10b981",
		};
		return colors[alertLevel] || colors.normal;
	},

	createStationIcon(alertLevel, isOnline) {
		const color = this.getAlertColor(alertLevel);
		const pulseClass = alertLevel === "critical" ? "pulse-marker" : "";
		const opacity = isOnline ? "1" : "0.5";

		return L.divIcon({
			className: "custom-marker",
			html: `
				<div class="marker-wrapper ${pulseClass}" style="opacity:${opacity}">
					<svg width="30" height="40" viewBox="0 0 30 40">
						<path d="M15 0C6.716 0 0 6.716 0 15c0 8.284 15 25 15 25s15-16.716 15-25C30 6.716 23.284 0 15 0z"
							fill="${color}" stroke="white" stroke-width="2"/>
						<circle cx="15" cy="15" r="6" fill="white"/>
						<circle cx="15" cy="15" r="4" fill="${color}"/>
					</svg>
				</div>
			`,
			iconSize: [30, 40],
			iconAnchor: [15, 40],
			popupAnchor: [0, -40],
		});
	},

	formatTimestamp(timestamp) {
		if (!timestamp) return "--:--";

		try {
			const date = new Date(timestamp);
			const hours = date.getHours();
			const minutes = date.getMinutes().toString().padStart(2, "0");
			const ampm = hours >= 12 ? "PM" : "AM";
			const h = (hours % 12 || 12).toString().padStart(2, "0");
			return `${h}:${minutes} ${ampm}`;
		} catch {
			return "--:--";
		}
	},

	startAutoRefresh() {
		if (this.refreshTimer) clearInterval(this.refreshTimer);
		this.refreshTimer = setInterval(
			() => this.updateAllStations(),
			this.refreshInterval
		);
	},

	stopAutoRefresh() {
		if (this.refreshTimer) {
			clearInterval(this.refreshTimer);
			this.refreshTimer = null;
		}
	},

	showError(message) {
		const el = document.getElementById("station-map");
		if (el) {
			el.innerHTML = `
				<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#ef4444;">
					<div style="text-align:center;">
						<p style="margin:0;font-weight:600;">⚠️ ${message}</p>
					</div>
				</div>
			`;
		}
	},

	addStyles() {
		if (document.getElementById("map-styles")) return;

		const style = document.createElement("style");
		style.id = "map-styles";
		style.textContent = `
			@keyframes pulse {
				0%, 100% { transform: scale(1); opacity: 1; }
				50% { transform: scale(1.1); opacity: 0.7; }
			}
			.pulse-marker { animation: pulse 2s infinite; }
			.station-popup { font-family: inherit; }
		`;
		document.head.appendChild(style);
	},

	async refresh() {
		await this.updateAllStations();
	},

	destroy() {
		this.stopAutoRefresh();
		if (this.map) this.map.remove();
		this.markers = {};
		this.cachedWeatherData = null;
		this.isInitialized = false;
	},
};

document.addEventListener("DOMContentLoaded", () => {
	StationMap.initialize().catch(console.error);
});

window.StationMap = StationMap;
