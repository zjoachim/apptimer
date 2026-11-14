async function get(method, params = {}) {
  const qs = Object.entries(params)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&')
  const url = qs ? `/api/${method}?${qs}` : `/api/${method}`
  const r = await fetch(url)
  return r.json()
}

async function post(method, data = {}) {
  const r = await fetch(`/api/${method}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return r.json()
}

export default {
  getSnapshot:       () => get('get_snapshot'),
  getTrend:          (app, days) => get('get_trend', { app, days }),
  getAllDates:       () => get('get_all_dates'),
  getHistory:        (date) => get('get_history', { date }),
  getCategoryStats:  () => get('get_category_stats'),
  getStartupStatus:  () => get('get_startup_status'),
  saveSettings:      (s) => post('save_settings', s),
  saveCategories:    (c) => post('save_categories', c),
  saveGoals:         (g) => post('save_goals', g),
  setStartup:        (enabled) => post('set_startup', { enabled }),
  openDataFolder:    () => post('open_folder'),
  quitApp:           () => post('quit'),
  exportPdf:         () => post('export_pdf'),
  exportCsv:         () => post('export_csv'),
  exportCumulativeCsv: () => post('export_cumulative_csv'),
  uninstall:         (deleteData) => post('uninstall', { delete_data: deleteData }),
}
