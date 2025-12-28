/**
 * Dashboard Alert Manager
 * Syncs alerts between map, metric cards, and alert banners
 */

const AlertManager = {
	TOTAL_STATIONS: 5,
	STATION_IDS: ['St1', 'St2', 'St3', 'St4', 'St5'],
	
	thresholds: null,
	currentAlerts: new Map(),
	
	initialize() {
		this.loadThresholds();
	},
	
	loadThresholds() {
		if (window.APP_CONFIG?.thresholds?.water_level) {
			this.thresholds = window.APP_CONFIG.thresholds.water_level;
		} else {
			this.thresholds = { advisory: 700, alert: 800, warning: 900, critical: 1000 };
		}
	},
	
	getAlertLevel(waterLevel) {
		if (!waterLevel && waterLevel !== 0) return 'normal';
		const level = parseFloat(waterLevel);
		if (isNaN(level)) return 'normal';
		
		if (level >= this.thresholds.critical) return 'critical';
		if (level >= this.thresholds.warning) return 'warning';
		if (level >= this.thresholds.alert) return 'alert';
		if (level >= this.thresholds.advisory) return 'advisory';
		return 'normal';
	},
	
	updateFromStationData(stationsData) {
		if (!stationsData) return;
		
		const alerts = { critical: [], warning: [], alert: [], advisory: [], normal: [] };
		const attentionStations = [];
		const now = new Date();
		const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
		
		const dataArray = Array.isArray(stationsData) ? stationsData : Object.values(stationsData);
		
		const latestByStation = new Map();
		dataArray.forEach(reading => {
			const stationId = reading.StationID;
			if (!stationId || !this.STATION_IDS.includes(stationId)) return;
			
			const existing = latestByStation.get(stationId);
			if (!existing) {
				latestByStation.set(stationId, reading);
			} else {
				const existingTime = new Date(existing.DateTime || existing.DateTimeStamp || 0);
				const currentTime = new Date(reading.DateTime || reading.DateTimeStamp || 0);
				if (currentTime > existingTime) {
					latestByStation.set(stationId, reading);
				}
			}
		});
		
		let onlineCount = 0;
		
		latestByStation.forEach((data, stationId) => {
			const timestamp = new Date(data.DateTime || data.DateTimeStamp);
			const isOnline = timestamp > oneHourAgo;
			
			if (isOnline) onlineCount++;
			
			const waterLevel = parseFloat(data.WaterLevel) || 0;
			const alertLevel = this.getAlertLevel(waterLevel);
			
			alerts[alertLevel].push({ stationId, waterLevel, isOnline });
			
			if (['critical', 'warning', 'alert'].includes(alertLevel)) {
				attentionStations.push(stationId);
			}
			
			this.currentAlerts.set(stationId, { level: alertLevel, waterLevel, isOnline, timestamp });
		});
		
		this.updateAlertBanners(alerts);
		this.updateMetricCards(alerts, onlineCount, attentionStations);
		
		return { alerts, onlineCount, totalCount: this.TOTAL_STATIONS, attentionStations };
	},
	
	updateAlertBanners(alerts) {
		let container = document.querySelector('.alert-banners-row');
		
		if (!container) {
			const existingSection = document.getElementById('dynamic-alert-section');
			if (existingSection) {
				container = existingSection.querySelector('.alert-banners-row');
			}
		}
		
		if (!container) {
			const section = document.createElement('section');
			section.className = 'pb-1';
			section.id = 'dynamic-alert-section';
			section.innerHTML = '<div class="container-fluid px-0"><div class="row g-2 g-md-3 alert-banners-row mx-0"></div></div>';
			
			const metricSection = document.querySelector('section.py-40');
			if (metricSection) {
				metricSection.after(section);
				container = section.querySelector('.alert-banners-row');
			}
		}
		
		if (!container) return;
		
		const hasAlerts = alerts.critical.length > 0 || alerts.warning.length > 0 || 
		                  alerts.alert.length > 0 || alerts.advisory.length > 0;
		
		const section = container.closest('section');
		if (section) section.style.display = hasAlerts ? 'block' : 'none';
		
		if (!hasAlerts) return;
		
		let html = '';
		
		if (alerts.critical.length > 0) {
			html += this.createBanner('critical', 'FLOOD ALERT - Critical', 'fa-exclamation-triangle', alerts.critical.length);
		}
		if (alerts.warning.length > 0) {
			html += this.createBanner('warning', 'FLOOD ALERT - Warning', 'fa-exclamation-circle', alerts.warning.length);
		}
		if (alerts.alert.length > 0) {
			html += this.createBanner('alert', 'FLOOD ALERT - Alert', 'fa-bolt', alerts.alert.length);
		}
		if (alerts.advisory.length > 0) {
			html += this.createBanner('advisory', 'FLOOD ADVISORY', 'fa-info-circle', alerts.advisory.length);
		}
		
		container.innerHTML = html;
	},
	
	createBanner(level, title, icon, count) {
		return `
			<div class="col-6 col-lg-auto">
				<div class="alert border-0 rounded-pill shadow-sm mb-0 flood-alert flood-alert--${level}" 
				     role="alert" aria-live="${level === 'critical' ? 'assertive' : 'polite'}">
					<div class="d-flex align-items-center gap-2">
						<i class="fas ${icon} alert-icon" aria-hidden="true"></i>
						<div class="alert-content">
							<h6 class="mb-0 fw-semibold text-uppercase">${title}</h6>
							${count > 1 ? `<small class="opacity-75">${count} stations</small>` : ''}
						</div>
					</div>
				</div>
			</div>
		`;
	},
	
	updateMetricCards(alerts, onlineCount, attentionStations) {
		const alertCard = document.querySelector('.alert-card');
		if (alertCard) {
			let highestLevel = 'normal';
			for (const level of ['critical', 'warning', 'alert', 'advisory']) {
				if (alerts[level].length > 0) {
					highestLevel = level;
					break;
				}
			}
			
			alertCard.className = alertCard.className.replace(/alert-card--\w+/g, '');
			alertCard.classList.add(`alert-card--${highestLevel}`);
			
			const levelText = alertCard.querySelector('.fs-3.fw-bold');
			if (levelText) {
				levelText.textContent = highestLevel.charAt(0).toUpperCase() + highestLevel.slice(1);
			}
			
			const icon = alertCard.querySelector('.fs-2 i');
			if (icon) {
				const iconMap = {
					critical: { cls: 'fa-skull-crossbones', color: '#dc2626' },
					warning: { cls: 'fa-exclamation-triangle', color: '#f97316' },
					alert: { cls: 'fa-exclamation-circle', color: '#eab308' },
					advisory: { cls: 'fa-info-circle', color: '#0ea5e9' },
					normal: { cls: 'fa-check-circle', color: '#409ac7' }
				};
				const cfg = iconMap[highestLevel];
				icon.className = `fas ${cfg.cls}`;
				icon.style.color = cfg.color;
			}
		}
		
		const cards = document.querySelectorAll('.card.border-0.shadow-sm');
		cards.forEach(card => {
			const title = card.querySelector('h6');
			if (!title) return;
			const titleText = title.textContent.trim();
			
			if (titleText.includes('Stations Requiring Attention')) {
				const valueEl = card.querySelector('.fs-3.fw-bold');
				const iconEl = card.querySelector('.fs-2 i');
				
				if (valueEl) valueEl.textContent = `${attentionStations.length}/${this.TOTAL_STATIONS}`;
				if (iconEl) {
					iconEl.className = attentionStations.length > 0 
						? 'fas fa-exclamation-triangle text-danger' 
						: 'fas fa-check-circle text-primary';
				}
			}
			
			if (titleText.includes('Weather Stations Online')) {
				const valueEl = card.querySelector('.fs-3.fw-bold');
				const iconEl = card.querySelector('.fs-2 i');
				
				if (valueEl) valueEl.textContent = `${onlineCount}/${this.TOTAL_STATIONS}`;
				if (iconEl) {
					iconEl.className = onlineCount === this.TOTAL_STATIONS 
						? 'fas fa-check-circle text-primary' 
						: 'fas fa-exclamation-circle text-warning';
				}
			}
		});
	},
	
	triggerAlert(stationId, alertLevel, waterLevel) {
		if (alertLevel === 'critical') {
			this.showNotification(stationId, waterLevel);
		}
		document.dispatchEvent(new CustomEvent('stationAlert', {
			detail: { stationId, alertLevel, waterLevel }
		}));
	},
	
	showNotification(stationId, waterLevel) {
		if ('Notification' in window && Notification.permission === 'granted') {
			new Notification('⚠️ CRITICAL FLOOD ALERT', {
				body: `Station ${stationId}: Water level at ${waterLevel}cm`,
				icon: '/static/media/logo.png',
				requireInteraction: true
			});
		}
	},
	
	requestNotificationPermission() {
		if ('Notification' in window && Notification.permission === 'default') {
			Notification.requestPermission();
		}
	}
};

document.addEventListener('DOMContentLoaded', () => {
	AlertManager.initialize();
	AlertManager.requestNotificationPermission();
});

window.AlertManager = AlertManager;