const API_CONFIG = {
  useMockData: false, 
  baseUrl: "http://127.0.0.1:5001",
  endpoints: {
    dashboard: "/dashboard",
    photos: "/photos/latest",
  },
  timeoutMs: 7000,
};

const MOCK_STATE = {
  plant: {
    type: "Manjericão Genovês",
    cultivar: "Folha larga",
    stage: "Vegetativo",
    bed: "Bancada A",
    plantedAt: "2026-05-08",
  },
  environment: {
    temperature: {
      label: "Temperatura",
      current: 25.8,
      ideal: { min: 22, max: 28 },
      unit: "°C",
    },
    humidity: {
      label: "Umidade",
      current: 68,
      ideal: { min: 60, max: 75 },
      unit: "%",
    },
  },
  devices: [
    { name: "Raspberry Pi 3", status: "online", detail: "Coleta e API local" },
    { name: "ESP-CAM", status: "online", detail: "720p, última foto há 4 min" },
    { name: "Irrigação", status: "standby", detail: "Último ciclo 08:20" },
  ],
  history: [
    { time: "08:00", temperature: 23.8, humidity: 64 },
    { time: "09:00", temperature: 24.2, humidity: 65 },
    { time: "10:00", temperature: 25.0, humidity: 66 },
    { time: "11:00", temperature: 25.7, humidity: 67 },
    { time: "12:00", temperature: 26.1, humidity: 69 },
    { time: "13:00", temperature: 25.8, humidity: 68 },
  ],
  photos: [
    {
      url: "./assets/esp32_cam/esp32_cam_mock_01.png",
      title: "Visão frontal",
      capturedAt: "2026-06-26T13:25:00-03:00",
    },
    {
      url: "./assets/esp32_cam/esp32_cam_mock_02.png",
      title: "Folhagem superior",
      capturedAt: "2026-06-26T12:55:00-03:00",
    },
    {
      url: "./assets/esp32_cam/esp32_cam_mock_03.png",
      title: "Borda da bancada",
      capturedAt: "2026-06-26T12:25:00-03:00",
    },
    {
      url: "./assets/esp32_cam/esp32_cam_mock_04.png",
      title: "Solo e caule",
      capturedAt: "2026-06-26T11:55:00-03:00",
    },
    {
      url: "./assets/esp32_cam/esp32_cam_mock_05.png",
      title: "Crescimento lateral",
      capturedAt: "2026-06-26T11:25:00-03:00",
    },
    {
      url: "./assets/esp32_cam/esp32_cam_mock_06.png",
      title: "Registro noturno",
      capturedAt: "2026-06-26T10:55:00-03:00",
    },
  ],
  events: [
    { time: "13:28", title: "Foto capturada", detail: "Imagem recebida da ESP-CAM." },
    { time: "13:05", title: "Ventilação ajustada", detail: "Temperatura aproximou do limite superior." },
    { time: "12:30", title: "Leitura gravada", detail: "Sensores sincronizados com o banco local." },
    { time: "08:20", title: "Irrigação concluída", detail: "Ciclo automático de 45 segundos." },
  ],
  updatedAt: "2026-06-26T13:29:00-03:00",
};

const state = {
  dashboard: null,
  selectedPhotoIndex: 0,
  chartMetric: "temperature",
  toastTimeout: null,
};

const elements = {
  connectionStatus: document.querySelector("#connectionStatus"),
  refreshButton: document.querySelector("#refreshButton"),
  themeToggle: document.querySelector("#themeToggle"),
  statusTitle: document.querySelector("#statusTitle"),
  statusSummary: document.querySelector("#statusSummary"),
  quickMetrics: document.querySelector("#quickMetrics"),
  plantCard: document.querySelector("#plantCard"),
  temperatureCard: document.querySelector("#temperatureCard"),
  humidityCard: document.querySelector("#humidityCard"),
  deviceCard: document.querySelector("#deviceCard"),
  photoTimestamp: document.querySelector("#photoTimestamp"),
  mainPlantPhoto: document.querySelector("#mainPlantPhoto"),
  mainPhotoCaption: document.querySelector("#mainPhotoCaption"),
  photoThumbnails: document.querySelector("#photoThumbnails"),
  chartBars: document.querySelector("#chartBars"),
  chartScale: document.querySelector("#chartScale"),
  chartButtons: document.querySelectorAll("[data-chart-metric]"),
  timelineList: document.querySelector("#timelineList"),
  toast: document.querySelector("#toast"),
};

function cloneMockState() {
  return JSON.parse(JSON.stringify(MOCK_STATE));
}

function getMockDashboardState(shouldDrift = false) {
  const mock = cloneMockState();
  const now = new Date();

  if (shouldDrift) {
    const temperatureShift = randomBetween(-0.6, 0.7);
    const humidityShift = randomBetween(-2.2, 2.2);

    mock.environment.temperature.current = roundTo(mock.environment.temperature.current + temperatureShift, 1);
    mock.environment.humidity.current = Math.round(mock.environment.humidity.current + humidityShift);

    const lastReading = mock.history[mock.history.length - 1];
    lastReading.temperature = mock.environment.temperature.current;
    lastReading.humidity = mock.environment.humidity.current;
    lastReading.time = now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  }

  mock.updatedAt = now.toISOString();
  mock.photos = mock.photos.map((photo, index) => ({
    ...photo,
    capturedAt: new Date(now.getTime() - index * 30 * 60 * 1000).toISOString(),
  }));

  return mock;
}

async function fetchDashboardState(options = {}) {
  if (API_CONFIG.useMockData) {
    await wait(180);
    return getMockDashboardState(options.shouldDrift);
  }

  return fetchJson(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.dashboard}`);
}

async function fetchLatestPhotos() {
  if (API_CONFIG.useMockData) {
    return getMockDashboardState().photos;
  }

  return fetchJson(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.photos}`);
}

async function fetchJson(url) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), API_CONFIG.timeoutMs);

  try {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function loadDashboard(options = {}) {
  setLoading(true);

  try {
    const dashboard = await fetchDashboardState(options);
    if (!API_CONFIG.useMockData) {
      dashboard.photos = await fetchLatestPhotos();
    }
    state.dashboard = dashboard;
    state.selectedPhotoIndex = dashboard.photos.length
      ? Math.min(Math.max(state.selectedPhotoIndex, 0), dashboard.photos.length - 1)
      : 0;
    renderDashboard(dashboard);
    showToast(API_CONFIG.useMockData ? "Dados mockados carregados." : "Dados atualizados pela API.");
  } catch (error) {
    console.error(error);
    updateConnection("Falha na leitura", "danger");
    showToast("Não foi possível carregar os dados da estufa.");
  } finally {
    setLoading(false);
  }
}

function renderDashboard(dashboard) {
  renderHeaderSummary(dashboard);
  renderQuickMetrics(dashboard);
  renderPlantCard(dashboard.plant);
  renderMetricCard(elements.temperatureCard, dashboard.environment.temperature, "temperature");
  renderMetricCard(elements.humidityCard, dashboard.environment.humidity, "humidity");
  renderDeviceCard(dashboard.devices);
  renderPhotos(dashboard.photos);
  renderChart(dashboard.history);
  renderTimeline(dashboard.events);
  updateConnection(API_CONFIG.useMockData ? "Modo mock" : "API conectada", API_CONFIG.useMockData ? "warning" : "ok");
}

function renderHeaderSummary(dashboard) {
  const temperatureStatus = getMetricStatus(dashboard.environment.temperature);
  const humidityStatus = getMetricStatus(dashboard.environment.humidity);
  const statuses = [temperatureStatus, humidityStatus];
  const isStable = statuses.every((item) => item.tone === "ok");
  const updatedAt = formatDateTime(dashboard.updatedAt);

  elements.statusTitle.textContent = isStable
    ? "Condições dentro da faixa ideal"
    : "Atenção aos ajustes da estufa";
  elements.statusSummary.textContent = `${dashboard.plant.type} em ${dashboard.plant.stage.toLowerCase()}. Última sincronização: ${updatedAt}.`;
}

function renderQuickMetrics(dashboard) {
  const temperature = dashboard.environment.temperature;
  const humidity = dashboard.environment.humidity;
  const camera = dashboard.devices.find((device) => device.name === "ESP-CAM");
  const cameraStatus = camera ? camera.status : "offline";

  elements.quickMetrics.innerHTML = [
    quickMetricTemplate("Temp.", `${formatNumber(temperature.current)}${temperature.unit}`, "Atual"),
    quickMetricTemplate("Umidade", `${formatNumber(humidity.current)}${humidity.unit}`, "Atual"),
    quickMetricTemplate("Câmera", normalizeStatus(cameraStatus), "ESP-CAM"),
  ].join("");
}

function renderPlantCard(plant) {
  elements.plantCard.innerHTML = `
    <p class="card-label">Tipo da planta</p>
    <h2>${escapeHtml(plant.type)}</h2>
    <dl class="meta-list">
      ${metaRowTemplate("Cultivar", plant.cultivar)}
      ${metaRowTemplate("Fase", plant.stage)}
      ${metaRowTemplate("Local", plant.bed)}
      ${metaRowTemplate("Plantio", formatShortDate(plant.plantedAt))}
    </dl>
  `;
}

function renderMetricCard(container, metric, key) {
  const status = getMetricStatus(metric);
  const gauge = getGaugeModel(metric);

  container.className = `info-card metric-card tone-${status.tone}`;
  container.innerHTML = `
    <div class="section-heading section-heading--compact">
      <div>
        <p class="card-label">${escapeHtml(metric.label)}</p>
        <div class="metric-value">
          <strong>${formatNumber(metric.current)}</strong>
          <span>${escapeHtml(metric.unit)}</span>
        </div>
      </div>
      <span class="status-badge ${status.className}">${escapeHtml(status.label)}</span>
    </div>
    <p class="metric-range">Ideal: ${formatNumber(metric.ideal.min)}${escapeHtml(metric.unit)} a ${formatNumber(metric.ideal.max)}${escapeHtml(metric.unit)}</p>
    <div class="gauge" aria-label="${escapeHtml(metric.label)} atual em relação à faixa ideal">
      <span class="gauge__target" style="left: ${gauge.targetLeft}%; width: ${gauge.targetWidth}%"></span>
      <span class="gauge__marker" style="left: ${gauge.markerLeft}%"></span>
    </div>
    <div class="metric-footer">
      <span>${escapeHtml(status.message)}</span>
      <strong>${escapeHtml(getMetricTrendLabel(key))}</strong>
    </div>
  `;
}

function renderDeviceCard(devices) {
  elements.deviceCard.innerHTML = `
    <p class="card-label">Hardware local</p>
    <h2>Operação</h2>
    <dl class="device-list">
      ${devices.map(deviceRowTemplate).join("")}
    </dl>
  `;
}

function renderPhotos(photos) {
  if (!photos.length) {
    elements.mainPlantPhoto.removeAttribute("src");
    elements.mainPhotoCaption.textContent = "Nenhuma foto disponível.";
    elements.photoTimestamp.textContent = "Sem foto";
    elements.photoThumbnails.innerHTML = "";
    return;
  }

  const photo = photos[state.selectedPhotoIndex] || photos[0];

  elements.mainPlantPhoto.src = photo.url;
  elements.mainPlantPhoto.alt = `${photo.title} da planta`;
  elements.mainPhotoCaption.textContent = `${photo.title} registrada em ${formatDateTime(photo.capturedAt)}.`;
  elements.photoTimestamp.textContent = formatRelativeTime(photo.capturedAt);
  elements.photoThumbnails.innerHTML = photos
    .map((item, index) => `
      <button
        class="thumb-button ${index === state.selectedPhotoIndex ? "is-active" : ""}"
        type="button"
        data-photo-index="${index}"
        aria-label="Abrir foto ${index + 1}: ${escapeHtml(item.title)}"
      >
        <img src="${escapeAttribute(item.url)}" alt="${escapeAttribute(item.title)}" loading="lazy" />
      </button>
    `)
    .join("");
}

function renderChart(history) {
  const metric = state.chartMetric;
  const values = history.map((item) => Number(item[metric]));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const unit = metric === "temperature" ? "°C" : "%";

  elements.chartBars.innerHTML = history
    .map((item) => {
      const value = Number(item[metric]);
      const height = 28 + ((value - min) / range) * 72;

      return `
        <div class="chart-bar" style="height: ${height}%">
          <span>${formatNumber(value)}${unit}</span>
        </div>
      `;
    })
    .join("");

  elements.chartScale.innerHTML = history
    .map((item) => `<span>${escapeHtml(item.time)}</span>`)
    .join("");

  elements.chartButtons.forEach((button) => {
    const isActive = button.dataset.chartMetric === metric;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
}

function renderTimeline(events) {
  elements.timelineList.innerHTML = events
    .map((event) => `
      <li>
        <time>${escapeHtml(event.time)}</time>
        <span>
          <strong>${escapeHtml(event.title)}</strong>
          ${escapeHtml(event.detail)}
        </span>
      </li>
    `)
    .join("");
}

function getMetricStatus(metric) {
  const value = Number(metric.current);
  const min = Number(metric.ideal.min);
  const max = Number(metric.ideal.max);

  if (value < min) {
    return {
      label: "Baixa",
      tone: "warn",
      className: "is-warning",
      message: `Faltam ${formatNumber(min - value)}${metric.unit} para o ideal.`,
    };
  }

  if (value > max) {
    return {
      label: "Alta",
      tone: "danger",
      className: "is-danger",
      message: `${formatNumber(value - max)}${metric.unit} acima do ideal.`,
    };
  }

  return {
    label: "Ideal",
    tone: "ok",
    className: "",
    message: "Faixa operacional estável.",
  };
}

function getGaugeModel(metric) {
  const min = Number(metric.ideal.min);
  const max = Number(metric.ideal.max);
  const value = Number(metric.current);
  const padding = Math.max((max - min) * 0.8, 1);
  const scaleMin = min - padding;
  const scaleMax = max + padding;
  const scaleRange = scaleMax - scaleMin;
  const targetLeft = ((min - scaleMin) / scaleRange) * 100;
  const targetWidth = ((max - min) / scaleRange) * 100;
  const markerLeft = clamp(((value - scaleMin) / scaleRange) * 100, 2, 98);

  return { targetLeft, targetWidth, markerLeft };
}

function getMetricTrendLabel(metric) {
  const history = state.dashboard ? state.dashboard.history : [];

  if (history.length < 2) {
    return "Sem tendência";
  }

  const previous = Number(history[history.length - 2][metric]);
  const current = Number(history[history.length - 1][metric]);
  const diff = roundTo(current - previous, 1);

  if (Math.abs(diff) < 0.2) {
    return "Estável";
  }

  return diff > 0 ? `+${formatNumber(diff)}` : formatNumber(diff);
}

function updateConnection(label, tone) {
  elements.connectionStatus.textContent = label;
  elements.connectionStatus.classList.toggle("is-warning", tone === "warning");
  elements.connectionStatus.classList.toggle("is-danger", tone === "danger");
}

function setLoading(isLoading) {
  elements.refreshButton.disabled = isLoading;
  elements.refreshButton.textContent = isLoading ? "Atualizando" : "Atualizar dados";
}

function showToast(message) {
  window.clearTimeout(state.toastTimeout);
  elements.toast.textContent = message;
  elements.toast.classList.add("is-visible");
  state.toastTimeout = window.setTimeout(() => {
    elements.toast.classList.remove("is-visible");
  }, 2400);
}

function setupEvents() {
  elements.refreshButton.addEventListener("click", () => {
    loadDashboard({ shouldDrift: true });
  });

  elements.themeToggle.addEventListener("click", () => {
    const root = document.documentElement;
    const nextTheme = root.dataset.theme === "light" ? "dark" : "light";
    root.dataset.theme = nextTheme;
    window.localStorage.setItem("greenhouse-theme", nextTheme);
  });

  elements.photoThumbnails.addEventListener("click", (event) => {
    const button = event.target.closest("[data-photo-index]");

    if (!button) {
      return;
    }

    state.selectedPhotoIndex = Number(button.dataset.photoIndex);
    renderPhotos(state.dashboard.photos);
  });

  elements.chartButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.chartMetric = button.dataset.chartMetric;
      renderChart(state.dashboard.history);
    });
  });
}

function restoreTheme() {
  const savedTheme = window.localStorage.getItem("greenhouse-theme");

  if (savedTheme === "light" || savedTheme === "dark") {
    document.documentElement.dataset.theme = savedTheme;
  }
}

function quickMetricTemplate(label, value, hint) {
  return `
    <div class="quick-metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <span>${escapeHtml(hint)}</span>
    </div>
  `;
}

function metaRowTemplate(label, value) {
  return `
    <div class="meta-row">
      <dt>${escapeHtml(label)}</dt>
      <dd><strong>${escapeHtml(value)}</strong></dd>
    </div>
  `;
}

function deviceRowTemplate(device) {
  const statusClass = device.status === "online" ? "" : device.status === "standby" ? "is-warning" : "is-danger";

  return `
    <div class="device-row">
      <dt>
        <span class="device-status ${statusClass}">${escapeHtml(device.name)}</span>
      </dt>
      <dd><strong>${escapeHtml(device.detail)}</strong></dd>
    </div>
  `;
}

function normalizeStatus(status) {
  const labels = {
    online: "Online",
    standby: "Pronta",
    offline: "Offline",
  };

  return labels[status] || status;
}

function formatNumber(value) {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value);
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parseDate(value));
}

function formatShortDate(value) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(parseDate(value));
}

function formatRelativeTime(value) {
  const diffMs = Date.now() - parseDate(value).getTime();
  const diffMinutes = Math.max(0, Math.round(diffMs / 60000));

  if (diffMinutes < 1) {
    return "Agora";
  }

  if (diffMinutes < 60) {
    return `${diffMinutes} min atrás`;
  }

  const hours = Math.round(diffMinutes / 60);
  return `${hours} h atrás`;
}

function parseDate(value) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const parts = value.split("-").map(Number);
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  return new Date(value);
}

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/`/g, "&#096;");
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function randomBetween(min, max) {
  return Math.random() * (max - min) + min;
}

function roundTo(value, decimals) {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

restoreTheme();
setupEvents();
loadDashboard();