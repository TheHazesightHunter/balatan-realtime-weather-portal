class WaterLevelChart {
	constructor(config) {
		// Basic config
		this.chartId = config.chartId || "waterLevelChart";
		this.apiEndpoint = config.apiEndpoint || "/api/water-level-data";
		this.showControls = config.showControls !== false;
		this.autoLoad = config.autoLoad !== false;

		this.thresholds = config.thresholds ||
			(window.APP_CONFIG && window.APP_CONFIG.thresholds.water_level) || {
				advisory: 700.0,
				alert: 800.0,
				warning: 900.0,
				critical: 1000.0,
			};

		if (
			window.APP_CONFIG &&
			window.APP_CONFIG.thresholds.water_level &&
			!config.thresholds
		) {
			console.log(
				"[WATER_LEVEL_CHART] Using thresholds from template injection"
			);
		}

		// Alert callback (optional)
		this.onThresholdBreach = config.onThresholdBreach || null;
		this.onDataLoaded = config.onDataLoaded || null;

		// Station configuration
		if (
			!config.stationConfig ||
			Object.keys(config.stationConfig).length === 0
		) {
			throw new Error("[WATER_LEVEL] stationConfig is required!");
		}
		this.stationConfig = config.stationConfig;

		// Internal state
		this.chart = null;
		this.chartData = null;
		this.dateRange = null;
		this.elements = {};
		this.currentAlerts = new Set();
		this._resizeTimer = null;
		this._resizeHandler = null;
		this._retryTimeout = null;
		this._loadDebounceTimer = null;

		// Sliding state (mobile)
		this.currentPage = 0;
		this.totalPages = 2;
		this.hoursPerPage = 12;
		this.dataCache = new Map();

		console.log(`[${this.chartId}] Water Level Chart initialized`);
	}

	// =========================================================================
	// RESPONSIVE HELPERS
	// =========================================================================

	_isMobile() {
		return window.innerWidth < 768;
	}

	_getResponsiveDimensions() {
		const width = window.innerWidth;

		if (width < 480) {
			return {
				height: 250,
				fontSize: 10,
				lineThickness: 2,
				markerSize: 4,
			};
		}
		if (width < 768) {
			return {
				height: 280,
				fontSize: 11,
				lineThickness: 2.5,
				markerSize: 5,
			};
		}
		if (width < 1024) {
			return {
				height: 320,
				fontSize: 12,
				lineThickness: 3,
				markerSize: 6,
			};
		}
		return {
			height: 400,
			fontSize: 12,
			lineThickness: 3,
			markerSize: 6,
		};
	}

	// =========================================================================
	// INITIALIZATION
	// =========================================================================

	async init() {
		console.log(`[${this.chartId}] Setting up...`);

		this._cacheElements();

		if (!this.elements.chartContainer) {
			console.error(`[${this.chartId}] Chart container not found!`);
			return;
		}

		const container = this.elements.chartContainer;
		const computedStyle = window.getComputedStyle(container);
		if (computedStyle.position === "static") {
			container.style.position = "relative";
		}

		this._setupResizeHandler();

		if (this.showControls) {
			await this._loadDateRange();
		}

		if (this.autoLoad) {
			this.loadLatestData();
		}
	}

	_cacheElements() {
		this.elements = {
			chartContainer: document.getElementById(this.chartId),
			loading: document.getElementById("water-chart-loading"),
			error: document.getElementById("water-chart-error"),
			errorMessage: document.getElementById("water-chart-error-message"),
			dateBadge: document.getElementById("water-chart-date-display"),
			datePicker: document.getElementById("waterDatePicker"),
			alertBanner: document.getElementById("water-alert-banner"),
		};
	}

	_setupResizeHandler() {
		this._resizeHandler = () => {
			if (this._resizeTimer) clearTimeout(this._resizeTimer);
			this._resizeTimer = setTimeout(() => {
				if (this.chart) {
					const dims = this._getResponsiveDimensions();
					this.chart.options.height = dims.height;
					this.chart.options.axisX.labelFontSize = dims.fontSize;
					this.chart.options.axisY.labelFontSize = dims.fontSize;
					this.chart.options.axisX.titleFontSize = dims.fontSize + 2;
					this.chart.options.axisY.titleFontSize = dims.fontSize + 2;
					this.chart.options.legend.fontSize = dims.fontSize;

					if (this.chart.options.data) {
						this.chart.options.data.forEach((series) => {
							series.lineThickness = dims.lineThickness;
							series.markerSize = dims.markerSize;
						});
					}

					this.chart.render();
				}
			}, 250);
		};
		window.addEventListener("resize", this._resizeHandler);
	}

	// =========================================================================
	// PUBLIC API
	// =========================================================================

	loadLatestData() {
		this._loadWaterLevelData();
	}

	loadSpecificDate(dateString) {
		console.log(`[${this.chartId}] Loading date: ${dateString}`);
		this.currentPage = 0;

		if (this._loadDebounceTimer) {
			clearTimeout(this._loadDebounceTimer);
		}

		this._loadDebounceTimer = setTimeout(() => {
			this._loadWaterLevelData(dateString);
		}, 300);

		return new Promise((resolve) => {
			const originalCallback = this.onDataLoaded;
			this.onDataLoaded = (data) => {
				if (originalCallback) originalCallback(data);
				resolve(data);
			};
		});
	}

	retry() {
		this._hideError();
		this.loadLatestData();
	}

	refresh() {
		if (this.chartData && this.chartData.date) {
			this.dataCache.delete(this.chartData.date);
		}
		this.loadLatestData();
	}

	destroy() {
		if (this._resizeTimer) clearTimeout(this._resizeTimer);
		if (this._retryTimeout) clearTimeout(this._retryTimeout);
		if (this._loadDebounceTimer) clearTimeout(this._loadDebounceTimer);
		if (this._resizeHandler) {
			window.removeEventListener("resize", this._resizeHandler);
		}
		if (this.chart) this.chart.destroy();
		this.chartData = null;
		this.dateRange = null;
		this.dataCache.clear();
		this.currentAlerts.clear();
		this.elements = {};
	}

	getCurrentData() {
		return this.chartData;
	}

	getActiveAlerts() {
		return Array.from(this.currentAlerts);
	}

	// =========================================================================
	// DATA LOADING
	// =========================================================================

	async _loadDateRange() {
		try {
			const response = await fetch("/api/water-level-date-range");

			if (!response.ok) {
				let errorMessage = `HTTP ${response.status}`;
				try {
					const errorData = await response.json();
					errorMessage = errorData.error || errorMessage;
				} catch (parseError) {
					console.warn("[WATER_LEVEL] Could not parse error response as JSON");
				}
				throw new Error(errorMessage);
			}

			const data = await response.json();
			if (!data.success) throw new Error(data.error || "Invalid date range");

			this.dateRange = {
				earliest: data.earliest_date,
				latest: data.latest_date,
				earliestDisplay: data.earliest_display,
				latestDisplay: data.latest_display,
			};

			if (this.elements.datePicker) {
				this.elements.datePicker.min = this.dateRange.earliest;
				this.elements.datePicker.max = this.dateRange.latest;
				this.elements.datePicker.value = this.dateRange.latest;
			}
		} catch (error) {
			console.warn(`[${this.chartId}] Date range error:`, error);
		}
	}

	async _loadWaterLevelData(dateString = null) {
		if (dateString && this.dataCache.has(dateString)) {
			console.log(
				`[${this.chartId}] Ã¢Å“â€œ Using cached data for ${dateString}`
			);
			const cachedData = this.dataCache.get(dateString);
			this.chartData = cachedData;

			if (this.elements.dateBadge) {
				this.elements.dateBadge.textContent = cachedData.date_display;
			}

			this._renderChart(cachedData);
			this._checkThresholds(cachedData);

			if (typeof this.onDataLoaded === "function") {
				this.onDataLoaded(cachedData);
			}

			return cachedData;
		}

		return this._loadWithRetry(dateString, 1);
	}

	async _loadWithRetry(dateString, attempt) {
		const MAX_RETRIES = 3;
		const RETRY_DELAYS = [1000, 2000, 5000];

		this._showLoading();

		try {
			const apiUrl = dateString
				? `${this.apiEndpoint}?date=${dateString}`
				: this.apiEndpoint;

			console.log(`[${this.chartId}] Fetching from: ${apiUrl}`);
			const response = await fetch(apiUrl);

			if (!response.ok) {
				let errorMessage = `HTTP ${response.status}`;
				try {
					const errorData = await response.json();
					errorMessage = errorData.error || errorMessage;
				} catch (parseError) {
					console.error("[WATER_LEVEL] Non-JSON error response:", parseError);
					errorMessage = `Server error (${response.status}). Please try again.`;
				}
				throw new Error(errorMessage);
			}

			const data = await response.json();

			if (!data.success) {
				if (data.retry_in && attempt < MAX_RETRIES) {
					await this._sleep(data.retry_in * 1000);
					return this._loadWithRetry(dateString, attempt + 1);
				}
				throw new Error(data.error || "Failed to load data");
			}

			const hasData = Object.values(data.stations).some(
				(station) => station.data && station.data.length > 0
			);

			if (!hasData) {
				throw new Error(`No data available for ${data.date_display}`);
			}

			this.chartData = data;

			if (data.date) {
				this.dataCache.set(data.date, data);
				console.log(`[${this.chartId}] Ã¢Å“â€œ Cached data for ${data.date}`);
			}

			if (this.elements.dateBadge) {
				this.elements.dateBadge.textContent = data.date_display;
			}

			this._renderChart(data);
			this._checkThresholds(data);
			this._hideLoading();

			if (typeof this.onDataLoaded === "function") {
				this.onDataLoaded(data);
			}

			return data;
		} catch (error) {
			console.error(`[${this.chartId}] Ã¢ÂÅ’ Error:`, error);

			if (attempt < MAX_RETRIES) {
				const retryDelay = RETRY_DELAYS[attempt - 1];
				this._showRetryMessage(attempt, MAX_RETRIES, retryDelay);
				await this._sleep(retryDelay);
				return this._loadWithRetry(dateString, attempt + 1);
			} else {
				this._showError(
					`Unable to load data after ${MAX_RETRIES} attempts. ` +
						`Please check your connection and try again.`
				);
			}
		}
	}

	_sleep(ms) {
		return new Promise((resolve) => {
			this._retryTimeout = setTimeout(resolve, ms);
		});
	}

	_showRetryMessage(attempt, maxAttempts, delayMs) {
		const seconds = Math.ceil(delayMs / 1000);
		const message = `Retrying ${attempt}/${maxAttempts} in ${seconds}s...`;

		if (this.elements.loading) {
			let loadingText = this.elements.loading.querySelector(
				".chart-loading__text"
			);
			if (loadingText) {
				loadingText.textContent = message;
			}
		}
	}

	// =========================================================================
	// THRESHOLD MONITORING & ALERTS
	// =========================================================================

	_checkThresholds(apiData) {
		this.currentAlerts.clear();

		for (const stationId in apiData.stations) {
			const stationData = apiData.stations[stationId];
			const config = this.stationConfig[stationId];

			if (!config || !stationData.data) continue;

			stationData.data.forEach((point) => {
				const level = point.y;
				const alertLevel = this._getAlertLevel(level);

				if (alertLevel !== "normal") {
					const alert = {
						stationId,
						stationName: config.name,
						level: level,
						alertLevel: alertLevel,
						time: point.label,
						timestamp: point.timestamp,
					};

					this.currentAlerts.add(alert);

					if (alertLevel === "critical") {
						console.error(
							`Ã°Å¸Å¡Â¨ CRITICAL FLOOD ALERT: ${config.name} at ${level}m (${point.label})`
						);
					} else if (alertLevel === "warning") {
						console.warn(
							`Ã¢Å¡ Ã¯Â¸Â FLOOD WARNING: ${config.name} at ${level}m (${point.label})`
						);
					}

					if (typeof this.onThresholdBreach === "function") {
						this.onThresholdBreach(alert);
					}
				}
			});
		}

		this._updateAlertBanner();
	}

	_getAlertLevel(waterLevel) {
		if (waterLevel >= this.thresholds.critical) return "critical";
		if (waterLevel >= this.thresholds.warning) return "warning";
		if (waterLevel >= this.thresholds.alert) return "alert";
		if (waterLevel >= this.thresholds.advisory) return "advisory";
		return "normal";
	}

	_updateAlertBanner() {
		if (!this.elements.alertBanner) return;

		if (this.currentAlerts.size === 0) {
			this.elements.alertBanner.classList.add("hidden");
			return;
		}

		let highestLevel = "advisory";
		for (const alert of this.currentAlerts) {
			if (alert.alertLevel === "critical") {
				highestLevel = "critical";
				break;
			}
			if (alert.alertLevel === "warning" && highestLevel !== "critical") {
				highestLevel = "warning";
			}
			if (
				alert.alertLevel === "alert" &&
				!["critical", "warning"].includes(highestLevel)
			) {
				highestLevel = "alert";
			}
		}

		this.elements.alertBanner.className = `water-alert-banner water-alert-banner--${highestLevel}`;
		this.elements.alertBanner.classList.remove("hidden");

		const message = this._getAlertMessage(
			highestLevel,
			this.currentAlerts.size
		);
		const messageEl = this.elements.alertBanner.querySelector(
			".water-alert-banner__message"
		);
		if (messageEl) {
			messageEl.innerHTML = message;
		}
	}

	_getAlertMessage(level, count) {
		const icons = {
			critical: "",
			warning: "",
			alert: "",
			advisory: "",
		};

		const messages = {
			critical: `${icons.critical} CRITICAL FLOOD LEVEL - ${count} station(s) require immediate attention`,
			warning: `${icons.warning} FLOOD WARNING - ${count} station(s) approaching critical levels`,
			alert: `${icons.alert} FLOOD ALERT - ${count} station(s) above normal levels`,
			advisory: `${icons.advisory} FLOOD ADVISORY - ${count} station(s) under monitoring`,
		};
		return messages[level] || "Monitoring flood levels";
	}

	// =========================================================================
	// CHART RENDERING
	// =========================================================================

	_renderChart(apiData) {
		const isMobile = this._isMobile();
		const dataSeries = [];

		for (const stationId in apiData.stations) {
			const stationData = apiData.stations[stationId];
			const config = this.stationConfig[stationId];

			if (!config) {
				console.warn(`No config for station: ${stationId}`);
				continue;
			}

			const allDataPoints = stationData.data.map((point) => ({
				label: point.label,
				y: point.y,
				actualLabel: point.label,
				day: point.day,
				stationName: config.name,
				alertLevel: this._getAlertLevel(point.y),
			}));

			const dataPoints = isMobile
				? this._getDataPointsForCurrentPage(allDataPoints)
				: allDataPoints;

			dataSeries.push({
				type: "spline",
				name: config.name,
				showInLegend: true,
				visible: true,
				color: config.color,
				dataPoints: dataPoints,
			});
		}

		if (this.chart) {
			this._updateChart(dataSeries);
		} else {
			this._createNewChart(dataSeries);
		}

		this._updateNavigationButtons();
	}

	_getDataPointsForCurrentPage(allDataPoints) {
		const startIndex = this.currentPage * this.hoursPerPage;
		const endIndex = startIndex + this.hoursPerPage;
		return allDataPoints.slice(startIndex, endIndex);
	}

	_updateChart(dataSeries) {
		const dims = this._getResponsiveDimensions();

		this.chart.options.height = dims.height;
		this.chart.options.axisX.labelFontSize = dims.fontSize;
		this.chart.options.axisY.labelFontSize = dims.fontSize;
		this.chart.options.axisX.titleFontSize = dims.fontSize + 2;
		this.chart.options.axisY.titleFontSize = dims.fontSize + 2;
		this.chart.options.legend.fontSize = dims.fontSize;

		this.chart.options.data = dataSeries.map((series) => ({
			...series,
			lineThickness: dims.lineThickness,
			markerSize: dims.markerSize,
		}));

		this.chart.render();
	}

	_createNewChart(dataSeries) {
		const dims = this._getResponsiveDimensions();

		this.chart = new CanvasJS.Chart(this.chartId, {
			animationEnabled: true,
			animationDuration: 400,
			theme: "light1",
			height: dims.height,

			title: {
				text: "",
				fontSize: 0,
			},

			axisX: {
				title: "Time of Day",
				titleFontSize: dims.fontSize + 2,
				labelFontSize: dims.fontSize,
				labelFontColor: "#64748b",
				lineColor: "#e2e8f0",
				tickColor: "#e2e8f0",
				interval: 2,
			},

			axisY: {
				title: "Water Level (centimeters)",
				titleFontSize: dims.fontSize + 2,
				labelFontSize: dims.fontSize,
				labelFontColor: "#64748b",
				lineColor: "#e2e8f0",
				tickColor: "#e2e8f0",
				gridColor: "#f1f5f9",
				gridThickness: 1,
				minimum: 0,
				maximum: 1200,
				suffix: " cm",
				stripLines: this._createThresholdLines(),
			},

			toolTip: {
				shared: true,
				contentFormatter: (e) => this._formatTooltip(e),
				borderThickness: 0,
				borderColor: "transparent",
				cornerRadius: 12,
				backgroundColor: "transparent",
				animationEnabled: false,
			},

			legend: {
				cursor: "pointer",
				itemclick: function (e) {
					e.dataSeries.visible =
						typeof e.dataSeries.visible === "undefined"
							? false
							: !e.dataSeries.visible;
					e.chart.render();
				},
				fontSize: dims.fontSize,
				fontWeight: 500,
				fontColor: "#475569",
				horizontalAlign: "center",
				verticalAlign: "bottom",
				markerType: "circle",
				markerMargin: 8,
			},

			data: dataSeries.map((series) => ({
				...series,
				lineThickness: dims.lineThickness,
				markerSize: dims.markerSize,
			})),
		});

		this.chart.render();

		if (this._isMobile()) {
			this._setupTouchGestures();
		}
	}

	_createThresholdLines() {
		return [
			{
				value: this.thresholds.advisory,
				color: "#3b82f6",
				label: "Advisory (700cm)",
				labelFontColor: "#3b82f6",
				labelFontSize: 11,
				labelAlign: "far",
				thickness: 2,
				lineDashType: "dot",
			},
			{
				value: this.thresholds.alert,
				color: "#eab308",
				label: "Alert (800cm)",
				labelFontColor: "#eab308",
				labelFontSize: 11,
				labelAlign: "far",
				thickness: 2,
				lineDashType: "dash",
			},
			{
				value: this.thresholds.warning,
				color: "#f97316",
				label: "Warning (900cm)",
				labelFontColor: "#f97316",
				labelFontSize: 11,
				labelAlign: "far",
				thickness: 2,
				lineDashType: "dash",
			},
			{
				value: this.thresholds.critical,
				color: "#dc2626",
				label: "Critical (1000cm)",
				labelFontColor: "#dc2626",
				labelFontSize: 11,
				labelAlign: "far",
				thickness: 3,
				lineDashType: "solid",
			},
		];
	}

	// =========================================================================
	// NAVIGATION
	// =========================================================================

	async slidePrev() {
		if (this.currentPage > 0) {
			this.currentPage--;
			this._renderChart(this.chartData);
		} else {
			await this._slideToPreviousDate();
		}
	}

	async slideNext() {
		if (this.currentPage < this.totalPages - 1) {
			this.currentPage++;
			this._renderChart(this.chartData);
		} else {
			await this._slideToNextDate();
		}
	}

	async _slideToPreviousDate() {
		if (!this.dateRange || !this.chartData) return;

		const currentDate = new Date(this.chartData.date);
		const prevDate = new Date(currentDate);
		prevDate.setDate(prevDate.getDate() - 1);
		const prevDateStr = this._formatDate(prevDate);

		if (prevDateStr < this.dateRange.earliest) return;

		await this._loadWaterLevelData(prevDateStr);
		this.currentPage = this.totalPages - 1;
		this._renderChart(this.chartData);
	}

	async _slideToNextDate() {
		if (!this.dateRange || !this.chartData) return;

		const currentDate = new Date(this.chartData.date);
		const nextDate = new Date(currentDate);
		nextDate.setDate(nextDate.getDate() + 1);
		const nextDateStr = this._formatDate(nextDate);

		if (nextDateStr > this.dateRange.latest) return;

		await this._loadWaterLevelData(nextDateStr);
		this.currentPage = 0;
		this._renderChart(this.chartData);
	}

	_formatDate(date) {
		const year = date.getFullYear();
		const month = String(date.getMonth() + 1).padStart(2, "0");
		const day = String(date.getDate()).padStart(2, "0");
		return `${year}-${month}-${day}`;
	}

	_updateNavigationButtons() {
		const prevBtn = document.getElementById("btn-water-prev-day");
		const nextBtn = document.getElementById("btn-water-next-day");

		if (!prevBtn || !nextBtn) return;

		const isMobile = this._isMobile();

		if (isMobile) {
			const atEarliestDate = this.chartData.date <= this.dateRange.earliest;
			const atLatestDate = this.chartData.date >= this.dateRange.latest;

			const canGoPrev = !(atEarliestDate && this.currentPage === 0);
			const canGoNext = !(
				atLatestDate && this.currentPage === this.totalPages - 1
			);

			prevBtn.style.display = canGoPrev ? "flex" : "none";
			nextBtn.style.display = canGoNext ? "flex" : "none";
		} else {
			if (this.dateRange && this.chartData) {
				const currentDate = this.chartData.date;
				prevBtn.disabled = currentDate <= this.dateRange.earliest;
				nextBtn.disabled = currentDate >= this.dateRange.latest;
			}
		}
	}

	_setupTouchGestures() {
		const chartElement = document.getElementById(this.chartId);
		if (!chartElement) return;

		let touchStartX = 0;
		let touchEndX = 0;

		chartElement.addEventListener(
			"touchstart",
			(e) => {
				touchStartX = e.changedTouches[0].screenX;
			},
			{ passive: true }
		);

		chartElement.addEventListener(
			"touchend",
			(e) => {
				touchEndX = e.changedTouches[0].screenX;
				this._handleSwipe(touchStartX, touchEndX);
			},
			{ passive: true }
		);
	}

	_handleSwipe(startX, endX) {
		const swipeThreshold = 50;
		const diff = startX - endX;

		if (Math.abs(diff) < swipeThreshold) return;

		if (diff > 0) {
			this.slideNext();
		} else {
			this.slidePrev();
		}
	}

	// =========================================================================
	// TOOLTIP
	// =========================================================================

	_formatTooltip(e) {
		if (!e.entries || e.entries.length === 0) return "";

		const width = window.innerWidth;
		let tooltipWidth = "280px";
		if (width < 480) {
			tooltipWidth = "180px";
		} else if (width < 768) {
			tooltipWidth = "200px";
		}

		const firstPoint = e.entries[0].dataPoint;
		const timeLabel = firstPoint.actualLabel || firstPoint.label;
		const dayLabel = firstPoint.day || "Today";

		const valueGroups = new Map();
		e.entries.forEach((entry) => {
			const level = entry.dataPoint.y;
			const roundedValue = level.toFixed(2); // Use 2 decimals for comparison

			if (!valueGroups.has(roundedValue)) {
				valueGroups.set(roundedValue, []);
			}
			valueGroups.get(roundedValue).push(entry);
		});

		// Find if any value has duplicates
		let maxDuplicateCount = 0;
		let duplicateValue = null;

		valueGroups.forEach((entries, value) => {
			if (entries.length > 1 && entries.length > maxDuplicateCount) {
				maxDuplicateCount = entries.length;
				duplicateValue = value;
			}
		});

		// Determine highest alert level
		let highestAlertLevel = "normal";
		e.entries.forEach((entry) => {
			const level = entry.dataPoint.y;
			const alertLevel = this._getAlertLevel(level);

			if (alertLevel === "critical") {
				highestAlertLevel = "critical";
			} else if (alertLevel === "warning" && highestAlertLevel !== "critical") {
				highestAlertLevel = "warning";
			} else if (
				alertLevel === "alert" &&
				!["critical", "warning"].includes(highestAlertLevel)
			) {
				highestAlertLevel = "alert";
			} else if (
				alertLevel === "advisory" &&
				!["critical", "warning", "alert"].includes(highestAlertLevel)
			) {
				highestAlertLevel = "advisory";
			}
		});

		const headerColors = {
			critical: "#dc2626",
			warning: "#f97316",
			alert: "#eab308",
			advisory: "#3b82f6",
			normal: "#409ac7",
		};

		const headerColor = headerColors[highestAlertLevel];

		let html = `<div class="water-tooltip" style="width: ${tooltipWidth};">`;

		html += `
			<div class="water-tooltip__header" style="background: ${headerColor};">
				${dayLabel} ${timeLabel}
			</div>
		`;

		// Show warning if multiple stations have identical values
		if (maxDuplicateCount > 1) {
			html += `
				<div class="water-tooltip__warning">
					<i class="fas fa-exclamation-triangle"></i>
					<span>${maxDuplicateCount} stations reporting identical values</span>
				</div>
			`;
		}

		if (highestAlertLevel !== "normal") {
			const alertLabels = {
				critical: "CRITICAL FLOOD LEVEL",
				warning: "FLOOD WARNING",
				alert: "FLOOD ALERT",
				advisory: "FLOOD ADVISORY",
			};

			html += `
				<div class="water-tooltip__alert water-tooltip__alert--${highestAlertLevel}">
					${alertLabels[highestAlertLevel]}
				</div>
			`;
		}

		html += `<div class="water-tooltip__body">`;

		e.entries.forEach((entry) => {
			const color = entry.dataSeries.color;
			const name = entry.dataPoint.stationName || entry.dataSeries.name;
			const level = entry.dataPoint.y;
			const alertLevel = this._getAlertLevel(level);

			const valueColor =
				alertLevel !== "normal" ? headerColors[alertLevel] : color;

			html += `
				<div class="water-tooltip__station">
					<div class="water-tooltip__station-left">
						<span class="water-tooltip__dot" style="background: ${color};"></span>
						<span class="water-tooltip__station-name">${name}:</span>
					</div>
					<span class="water-tooltip__value" style="color: ${valueColor};">
						${level.toFixed(1)} cm
					</span>
				</div>
			`;
		});

		html += `</div></div>`;
		return html;
	}

	// =========================================================================
	// UI STATE
	// =========================================================================

	_showLoading() {
		if (this.elements.loading) {
			this.elements.loading.classList.remove("hidden");
		}
		this._hideError();
	}

	_hideLoading() {
		if (this.elements.loading) {
			this.elements.loading.classList.add("hidden");
		}
	}

	_showError(message) {
		if (this.elements.errorMessage) {
			this.elements.errorMessage.textContent = message;
		}
		if (this.elements.error) {
			this.elements.error.classList.add("show");
		}
		if (this.elements.chartContainer) {
			this.elements.chartContainer.style.display = "none";
		}
		this._hideLoading();
	}

	_hideError() {
		if (this.elements.error) {
			this.elements.error.classList.remove("show");
		}
		if (this.elements.chartContainer) {
			this.elements.chartContainer.style.display = "block";
		}
	}
}

// Export
if (typeof module !== "undefined" && module.exports) {
	module.exports = WaterLevelChart;
} else {
	window.WaterLevelChart = WaterLevelChart;
}
