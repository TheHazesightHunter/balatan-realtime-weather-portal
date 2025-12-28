/**
 * Real-time Weather Card with Intelligent Caching and Dynamic Icons
 */
class RealTimeWeatherCard {
	constructor(config = {}) {
		this.config = {
			stationId: config.stationId || "St1",
			apiEndpoint: config.apiEndpoint || "/api/weather-data",
			refreshInterval: config.refreshInterval || 60000,
			enableAutoRefresh: config.enableAutoRefresh !== false,
			...config,
		};

		this.lastUpdate = null;
		this.refreshTimer = null;
		this.retryCount = 0;
		this.maxRetries = 3;
		this.isUpdating = false;
		this.lastDataTimestamp = null;

		this.cachedData = null;
		this.lastSuccessfulFetch = null;
		this.consecutiveErrors = 0;
		this.backoffMultiplier = 1;

		// Weather icon configuration
		this.iconConfig = {
			thresholds: {
				none: 0.0,
				lightMin: 0.5,
				lightMax: 5.0,
				moderateMax: 15.0,
			},
			nightHours: {
				start: 18, // 6 PM
				end: 5, // 5 AM
			},
			icons: {
				day: {
					clear: "sunny.png",
					light: "light-rain.png",
					moderate: "rainy.png",
					heavy: "intense-rain.png",
				},
				night: {
					clear: "night-no-rain.png",
					light: "night-rainy.png",
					moderate: "night-rainy.png",
					heavy: "night-rainy.png",
				},
			},
		};

		// Override with server config if available
		if (window.APP_CONFIG?.weatherIconConfig) {
			this.iconConfig = {
				...this.iconConfig,
				...window.APP_CONFIG.weatherIconConfig,
			};
		}
	}

	async initialize() {
		await this.updateWeatherCard();

		if (this.config.enableAutoRefresh) {
			this.startAutoRefresh();
		}

		this.setupRefreshButton();
	}

	async updateWeatherCard() {
		if (this.isUpdating) return;
		this.isUpdating = true;

		try {
			this.showLoadingState();
			const data = await this.fetchWeatherData();
			const stationData = this.findMDRRMOStationData(data);

			if (stationData) {
				this.cachedData = stationData;
				this.lastSuccessfulFetch = new Date();
				this.consecutiveErrors = 0;
				this.backoffMultiplier = 1;

				this.updateCardElements(stationData);
				this.lastDataTimestamp =
					stationData.DateTime || stationData.DateTimeStamp;
				this.lastUpdate = new Date();
				this.updateLastRefreshTime();
				this.retryCount = 0;
				this.hideErrorIndicator();
			} else {
				throw new Error("No MDRRMO data in response");
			}
		} catch (error) {
			console.warn("[WEATHER_CARD] Fetch failed:", error.message);
			this.handleUpdateError(error);
		} finally {
			this.isUpdating = false;
			this.hideLoadingState();
		}
	}

	async fetchWeatherData() {
		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), 10000);

		try {
			const response = await fetch(this.config.apiEndpoint, {
				method: "GET",
				headers: { Accept: "application/json" },
				signal: controller.signal,
			});

			clearTimeout(timeoutId);

			if (!response.ok) throw new Error(`HTTP ${response.status}`);

			const data = await response.json();

			if (Array.isArray(data)) return data;
			if (data?.success && Array.isArray(data.data)) return data.data;
			if (Array.isArray(data?.data)) return data.data;

			throw new Error("Invalid response format");
		} catch (error) {
			clearTimeout(timeoutId);
			throw error;
		}
	}

	findMDRRMOStationData(dataArray) {
		if (!Array.isArray(dataArray) || dataArray.length === 0) return null;

		const mdrrmoStationIds = ["St1"];
		const mdrrmoReadings = dataArray.filter((r) =>
			mdrrmoStationIds.includes(r.StationID)
		);

		if (mdrrmoReadings.length === 0) return null;

		mdrrmoReadings.sort((a, b) => {
			const timeA = new Date(a.DateTime || a.DateTimeStamp || 0);
			const timeB = new Date(b.DateTime || b.DateTimeStamp || 0);
			return timeB - timeA;
		});

		return mdrrmoReadings[0];
	}

	updateCardElements(data) {
		const timestamp = this.formatTimestamp(data.DateTimeStamp || data.DateTime);
		this.updateElement(".weather-card__time", `Updated Data: ${timestamp}`);

		const rainfall =
			data.HourlyRain != null ? parseFloat(data.HourlyRain) : null;
		const rainfallDisplay =
			rainfall != null
				? `${rainfall.toFixed(1)}<small>mm/hr</small>`
				: `--<small>mm/hr</small>`;
		this.updateElement(".weather-card__main-value", rainfallDisplay);

		const waterLevel =
			data.WaterLevel != null ? parseFloat(data.WaterLevel) : null;
		if (waterLevel != null) {
			this.updateMetricValue(
				"water level",
				`${waterLevel.toFixed(1)}<span class="unit">m</span>`
			);
		}

		const windSpeed =
			data.WindSpeed != null ? parseFloat(data.WindSpeed) : null;
		if (windSpeed != null) {
			this.updateMetricValue(
				"wind speed",
				`${windSpeed.toFixed(1)}<span class="unit">m/s</span>`
			);
		}

		const humidity = data.Humidity != null ? parseFloat(data.Humidity) : null;
		if (humidity != null) {
			this.updateMetricValue(
				"humidity",
				`${Math.round(humidity)}<span class="unit">%</span>`
			);
		}

		const temperature =
			data.Temperature != null ? parseFloat(data.Temperature) : null;
		if (temperature != null) {
			this.updateMetricValue(
				"temperature",
				`${temperature.toFixed(1)}<span class="unit">°C</span>`
			);
		}

		// Update weather icon based on rainfall and time
		const dataTimestamp = data.DateTime || data.DateTimeStamp;
		this.updateWeatherIcon(rainfall, dataTimestamp);
		this.pulseCard();
	}

	updateMetricValue(metricType, html) {
		const metrics = document.querySelectorAll(".weather-card__metric");

		for (const metric of metrics) {
			const icon = metric.querySelector(".weather-card__metric-icon");
			if (icon?.alt?.toLowerCase().includes(metricType.replace("_", " "))) {
				const valueElement = metric.querySelector(
					".weather-card__metric-value"
				);
				if (valueElement) {
					valueElement.innerHTML = html;
					break;
				}
			}
		}
	}

	updateElement(selector, content) {
		const element = document.querySelector(selector);
		if (element) {
			element.innerHTML = content;
		}
	}

	isNightTime(hour) {
		const { start, end } = this.iconConfig.nightHours;
		return hour >= start || hour < end;
	}

	getRainfallCategory(rainfall) {
		const { none, lightMin, lightMax, moderateMax } =
			this.iconConfig.thresholds;

		if (rainfall == null || rainfall < lightMin) return "clear";
		if (rainfall <= lightMax) return "light";
		if (rainfall <= moderateMax) return "moderate";
		return "heavy";
	}

	getWeatherIconFilename(rainfall, timestamp) {
		let hour = new Date().getHours();

		if (timestamp) {
			try {
				const dataDate = new Date(timestamp);
				if (!isNaN(dataDate.getTime())) {
					hour = dataDate.getHours();
				}
			} catch (e) {}
		}

		const timeOfDay = this.isNightTime(hour) ? "night" : "day";
		const category = this.getRainfallCategory(rainfall);

		return this.iconConfig.icons[timeOfDay][category];
	}

	updateWeatherIcon(rainfall, timestamp) {
		const iconElement = document.querySelector(".weather-card__icon img");
		if (!iconElement) return;

		const iconFilename = this.getWeatherIconFilename(rainfall, timestamp);
		const basePath = iconElement.src.includes("/static/")
			? "/static/media/forecast-icons/"
			: "media/forecast-icons/";

		const newSrc = `${basePath}${iconFilename}`;

		if (iconElement.src !== newSrc) {
			iconElement.src = newSrc;
			iconElement.alt = this.getWeatherDescription(rainfall, timestamp);
		}
	}

	getWeatherDescription(rainfall, timestamp) {
		let hour = new Date().getHours();
		if (timestamp) {
			try {
				hour = new Date(timestamp).getHours();
			} catch (e) {}
		}

		const isNight = this.isNightTime(hour);
		const category = this.getRainfallCategory(rainfall);

		const descriptions = {
			day: {
				clear: "Sunny",
				light: "Light rain",
				moderate: "Moderate rain",
				heavy: "Heavy rain",
			},
			night: {
				clear: "Clear night",
				light: "Night with light rain",
				moderate: "Night with rain",
				heavy: "Night with heavy rain",
			},
		};

		return descriptions[isNight ? "night" : "day"][category];
	}

	formatTimestamp(timestamp) {
		if (!timestamp) return "--:--";

		try {
			const date = new Date(timestamp);
			const hours = date.getHours();
			const minutes = date.getMinutes().toString().padStart(2, "0");
			const ampm = hours >= 12 ? "PM" : "AM";
			const displayHours = (hours % 12 || 12).toString().padStart(2, "0");
			return `${displayHours}:${minutes} ${ampm}`;
		} catch {
			return "--:--";
		}
	}

	startAutoRefresh() {
		if (this.refreshTimer) clearInterval(this.refreshTimer);

		const actualInterval = this.config.refreshInterval * this.backoffMultiplier;

		this.refreshTimer = setInterval(() => {
			this.updateWeatherCard();
		}, actualInterval);

		setInterval(() => this.updateLastRefreshTime(), 10000);
	}

	updateLastRefreshTime() {
		let lastUpdateElement = document.querySelector(
			".weather-card__last-update"
		);

		if (!lastUpdateElement) {
			const timeElement = document.querySelector(".weather-card__time");
			if (timeElement && this.lastUpdate) {
				lastUpdateElement = document.createElement("div");
				lastUpdateElement.className = "weather-card__last-update";
				lastUpdateElement.style.cssText =
					"font-size: 0.75rem; opacity: 0.7; margin-top: 0.25rem;";
				timeElement.appendChild(lastUpdateElement);
			}
		}

		if (lastUpdateElement && this.lastSuccessfulFetch) {
			const secondsAgo = Math.floor(
				(new Date() - this.lastSuccessfulFetch) / 1000
			);

			if (secondsAgo < 60) {
				lastUpdateElement.textContent = `Refreshed ${secondsAgo}s ago`;
			} else if (secondsAgo < 3600) {
				lastUpdateElement.textContent = `Refreshed ${Math.floor(
					secondsAgo / 60
				)}m ago`;
			} else {
				lastUpdateElement.textContent = `Refreshed ${Math.floor(
					secondsAgo / 3600
				)}h ago`;
			}
		}
	}

	showLoadingState() {
		const card = document.querySelector(".weather-card");
		if (card) card.classList.add("weather-card--updating");
	}

	hideLoadingState() {
		const card = document.querySelector(".weather-card");
		if (card) card.classList.remove("weather-card--updating");
	}

	pulseCard() {
		const card = document.querySelector(".weather-card");
		if (card) {
			card.classList.add("weather-card--pulse");
			setTimeout(() => card.classList.remove("weather-card--pulse"), 500);
		}
	}

	setupRefreshButton() {
		const refreshBtn = document.getElementById("weather-card-refresh");
		if (refreshBtn) {
			refreshBtn.addEventListener("click", async (e) => {
				e.preventDefault();
				await this.updateWeatherCard();
			});
		}
	}

	handleUpdateError(error) {
		this.consecutiveErrors++;

		if (this.cachedData) {
			this.updateCardElements(this.cachedData);
			this.showStaleDataIndicator();

			if (this.consecutiveErrors >= 3) {
				this.backoffMultiplier = Math.min(this.backoffMultiplier * 2, 5);
				this.restartWithBackoff();
			}
		} else if (this.retryCount < this.maxRetries) {
			this.retryCount++;
			const retryDelay = 2000 * Math.pow(2, this.retryCount);
			setTimeout(() => this.updateWeatherCard(), retryDelay);
		} else {
			this.showErrorState();
		}
	}

	restartWithBackoff() {
		if (this.refreshTimer) clearInterval(this.refreshTimer);
		const newInterval = this.config.refreshInterval * this.backoffMultiplier;

		this.refreshTimer = setInterval(() => {
			this.updateWeatherCard();
		}, newInterval);
	}

	showStaleDataIndicator() {
		const timeElement = document.querySelector(".weather-card__time");
		if (timeElement && !timeElement.querySelector(".stale-indicator")) {
			const indicator = document.createElement("span");
			indicator.className = "stale-indicator";
			indicator.style.cssText =
				"color: #f59e0b; font-size: 0.7rem; margin-left: 8px;";
			indicator.textContent = "(cached)";
			timeElement.appendChild(indicator);
		}
	}

	hideErrorIndicator() {
		const indicator = document.querySelector(".stale-indicator");
		if (indicator) indicator.remove();
	}

	showErrorState() {
		const timeElement = document.querySelector(".weather-card__time");
		if (timeElement) {
			timeElement.innerHTML = `
				<span style="color: #ef4444; font-size: 0.8rem;">
					Connection Error - 
					<a href="#" onclick="window.weatherCard.updateWeatherCard(); return false;" 
					   style="color: white; text-decoration: underline;">Retry</a>
				</span>
			`;
		}
	}

	destroy() {
		if (this.refreshTimer) clearInterval(this.refreshTimer);
		this.cachedData = null;
	}
}

document.addEventListener("DOMContentLoaded", function () {
	window.weatherCard = new RealTimeWeatherCard({
		stationId: "St1",
		refreshInterval: 60000,
		enableAutoRefresh: true,
	});

	window.weatherCard.initialize();
});

window.addEventListener("beforeunload", function () {
	if (window.weatherCard) window.weatherCard.destroy();
});
