/** Chart.js rendering for product page. */
(function () {
  if (typeof chartPayload === "undefined" || !chartPayload.labels) return;

  const ctx = document.getElementById("mainChart");
  if (!ctx) return;

  const type = chartPayload.type;
  const weekCount = () =>
    (chartPayload.isoWeeks && chartPayload.isoWeeks.length) || chartPayload.labels.length;

  function medianForWeeks(yearSeries, activeYears, n) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const vals = activeYears
        .map((y) => yearSeries[y] && yearSeries[y][i])
        .filter((v) => v != null && !Number.isNaN(v));
      if (vals.length === 0) {
        out.push(null);
      } else {
        vals.sort((a, b) => a - b);
        const mid = Math.floor(vals.length / 2);
        out.push(vals.length % 2 ? vals[mid] : (vals[mid - 1] + vals[mid]) / 2);
      }
    }
    return out;
  }

  function activeYears(chart) {
    return chart.data.datasets
      .map((d, i) => ({ d, i }))
      .filter(({ d, i }) => d.isYear && !chart.getDatasetMeta(i).hidden)
      .map(({ d }) => d.label);
  }

  function fmtNum(n, decimals) {
    if (n == null || Number.isNaN(n)) return "—";
    const fixed = Number(n).toFixed(decimals);
    const [intPart, fracPart] = fixed.split(".");
    const spaced = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return fracPart != null && decimals > 0 ? `${spaced},${fracPart}` : spaced;
  }

  function fmtQty(v) {
    if (v == null || Number.isNaN(v)) return "—";
    return fmtNum(v, Number.isInteger(v) ? 0 : 1);
  }

  function seasonTooltipTitle(items) {
    const idx = items[0].dataIndex;
    const iso = chartPayload.isoWeeks?.[idx];
    const axisDate = chartPayload.dateLabels?.[idx] || chartPayload.labels[idx];
    if (iso != null) {
      return `Неделя ${iso} · ${axisDate}`;
    }
    return String(axisDate);
  }

  function seasonTooltipLabel(ctx) {
    const val = ctx.parsed.y;
    if (val == null || Number.isNaN(val)) return null;
    const name = ctx.dataset.label;
    if (ctx.dataset.isAverage) {
      return `Средняя: ${fmtQty(val)}`;
    }
    const dates = chartPayload.yearWeekDates?.[name];
    const date = dates?.[ctx.dataIndex];
    return date ? `${name} · ${date}: ${fmtQty(val)}` : `${name}: ${fmtQty(val)}`;
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  let metricsTimer = null;

  function updateProductMetrics(chart) {
    if (type !== "season" || !chartPayload.productKey) return;
    const years = activeYears(chart);
    if (!years.length) return;
    clearTimeout(metricsTimer);
    metricsTimer = setTimeout(async () => {
      const params = new URLSearchParams();
      years.forEach((y) => params.append("years", y));
      try {
        const resp = await fetch(
          `/api/product/${chartPayload.productKey}/metrics?${params}`,
        );
        if (!resp.ok) return;
        const m = await resp.json();
        const wc = fmtNum(m.weekly_consumption, 1);
        const urgent = !!m.is_urgent;
        const qty = urgent ? fmtNum(m.recommended_order_qty, 0) : "—";
        const dep = m.depletion_date || "—";
        const reo = m.reorder_date || "—";
        const rop = m.reorder_point != null ? fmtNum(m.reorder_point, 0) : "—";
        setText("metric-consumption", wc);
        setText("metric-depletion", dep);
        setText("metric-qty", qty);
        setText("metric-rop", rop);
        setText("summary-consumption", wc);
        setText("summary-depletion", dep);
        setText("summary-qty", qty);
        setText("summary-reorder", reo);
        const policyEl = document.getElementById("policy-note");
        if (policyEl && m.policy_note) {
          policyEl.innerHTML = `Точка заказа (ROP): <b id="metric-rop">${rop}</b> · ${m.policy_note}`;
        }
        const summaryPolicy = document.getElementById("summary-policy");
        if (summaryPolicy && m.policy_note) summaryPolicy.textContent = m.policy_note;
        const orderLine = document.getElementById("summary-order-line");
        if (orderLine) orderLine.classList.toggle("hidden", !urgent);
        const costEl = document.getElementById("summary-cost");
        if (costEl) {
          if (urgent && m.cost_gel) {
            costEl.textContent = m.cost_gel;
            costEl.classList.remove("hidden");
          } else {
            costEl.classList.add("hidden");
          }
        }
      } catch (_) {
        /* ignore network errors */
      }
    }, 150);
  }

  function updateSeasonAverage(chart) {
    if (!chartPayload.yearSeries) return;
    const avgIdx = chart.data.datasets.findIndex((d) => d.isAverage);
    if (avgIdx < 0) return;
    const visible = activeYears(chart);
    if (visible.length >= 2) {
      chart.data.datasets[avgIdx].data = medianForWeeks(
        chartPayload.yearSeries,
        visible,
        weekCount(),
      );
      chart.data.datasets[avgIdx].hidden = false;
      chart.data.datasets[avgIdx].order = 100;
    } else {
      chart.data.datasets[avgIdx].hidden = true;
    }
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "bottom",
        labels: { boxWidth: 12, font: { size: 10 } },
        onClick: (e, legendItem, legend) => {
          const idx = legendItem.datasetIndex;
          const chart = legend.chart;
          if (chart.data.datasets[idx].isAverage) return;
          const meta = chart.getDatasetMeta(idx);
          meta.hidden = meta.hidden === null ? !chart.data.datasets[idx].hidden : null;
          if (type === "season") {
            updateSeasonAverage(chart);
            updateProductMetrics(chart);
          }
          chart.update();
        },
      },
      tooltip: type === "season"
        ? {
            callbacks: {
              title: seasonTooltipTitle,
              label: seasonTooltipLabel,
            },
          }
        : {},
    },
    scales: {
      x: {
        grid: { color: "#f0ede9" },
        ticks: {
          maxTicksLimit: type === "season" ? 12 : 8,
          font: { size: 9 },
          maxRotation: 45,
          minRotation: 0,
        },
        title: type === "season"
          ? { display: true, text: "Неделя года (понедельник)", font: { size: 10 } }
          : undefined,
      },
      y: {
        grid: { color: "#f0ede9" },
        beginAtZero: type === "season",
        title: type === "season"
          ? { display: true, text: "Продажи", font: { size: 10 } }
          : undefined,
      },
    },
  };

  const chart = new Chart(ctx, {
    type: "line",
    data: { labels: chartPayload.labels, datasets: chartPayload.datasets },
    options,
  });

  if (type === "forecast" && chartPayload.rop != null) {
    [chartPayload.rop, chartPayload.safety, 0].forEach((val, i) => {
      if (val == null) return;
      const colors = ["#875208", "#ba1a1a", "#82746d"];
      chart.data.datasets.push({
        type: "line",
        borderColor: colors[i],
        borderDash: i < 2 ? [4, 4] : [],
        borderWidth: 1,
        label: ["ROP", "Страх.", "0"][i],
        data: chartPayload.labels.map(() => val),
        pointRadius: 0,
        order: 1,
      });
    });
    chart.update();
  }

  if (type === "stock" && chartPayload.inflowIndexes) {
    const ds = chart.data.datasets[0];
    ds.pointRadius = chartPayload.labels.map((_, i) =>
      chartPayload.inflowIndexes.includes(i) ? 6 : 0
    );
    ds.pointStyle = chartPayload.labels.map((_, i) =>
      chartPayload.inflowIndexes.includes(i) ? "triangle" : "circle"
    );
    ds.pointBackgroundColor = "#006332";
    chart.update();
  }

  if (type === "season") {
    updateProductMetrics(chart);
  }
})();
