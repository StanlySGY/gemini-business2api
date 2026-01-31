<template>
  <div class="space-y-5">
    <section class="grid grid-cols-2 gap-3 md:grid-cols-2 xl:grid-cols-4">
      <div
        v-for="stat in stats"
        :key="stat.label"
        class="rounded-3xl border border-border bg-card p-4"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <p class="text-xs uppercase tracking-[0.3em] text-muted-foreground">{{ stat.label }}</p>
            <p class="mt-2 text-2xl font-semibold text-foreground tabular-nums">{{ stat.value }}</p>
            <p class="mt-1.5 text-xs leading-relaxed text-muted-foreground">{{ stat.caption }}</p>
          </div>
          <div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full" :class="stat.iconBg">
            <Icon :icon="stat.icon" class="h-4 w-4" :class="stat.iconColor" />
          </div>
        </div>
      </div>
    </section>

    <section class="grid grid-cols-1 gap-4">
      <div class="rounded-3xl border border-border bg-card p-5">
        <div class="flex items-center justify-between mb-4">
          <p class="text-sm font-medium text-foreground">模型请求分布</p>
          <div class="flex items-center gap-1">
            <button
              v-for="range in timeRanges"
              :key="range.value"
              @click="timeRangeHourlyRequests = range.value"
              :class="timeRangeHourlyRequests === range.value
                ? 'bg-accent text-foreground border-primary/50 font-semibold'
                : 'bg-transparent text-muted-foreground hover:bg-accent/50 hover:text-foreground border-border'"
              class="rounded-lg px-3 py-1.5 text-xs font-medium transition-all border"
            >
              {{ range.label }}
            </button>
          </div>
        </div>
        <div ref="hourlyRequestsChartRef" class="h-72 w-full px-2"></div>
      </div>
    </section>

    <section class="grid grid-cols-1 gap-4">
      <div class="rounded-3xl border border-border bg-card p-5">
        <div class="flex items-center justify-between mb-4">
          <p class="text-sm font-medium text-foreground">调用趋势</p>
          <div class="flex items-center gap-1">
            <button
              v-for="range in timeRanges"
              :key="range.value"
              @click="timeRangeTrend = range.value"
              :class="timeRangeTrend === range.value
                ? 'bg-accent text-foreground border-primary/50 font-semibold'
                : 'bg-transparent text-muted-foreground hover:bg-accent/50 hover:text-foreground border-border'"
              class="rounded-lg px-3 py-1.5 text-xs font-medium transition-all border"
            >
              {{ range.label }}
            </button>
          </div>
        </div>
        <div ref="trendChartRef" class="h-56 w-full"></div>
      </div>
    </section>

    <section class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div class="rounded-3xl border border-border bg-card p-5">
        <div class="flex items-center justify-between mb-4">
          <p class="text-sm font-medium text-foreground">成功率趋势</p>
          <div class="flex items-center gap-1">
            <button
              v-for="range in timeRanges"
              :key="range.value"
              @click="timeRangeSuccessRate = range.value"
              :class="timeRangeSuccessRate === range.value
                ? 'bg-accent text-foreground border-primary/50 font-semibold'
                : 'bg-transparent text-muted-foreground hover:bg-accent/50 hover:text-foreground border-border'"
              class="rounded-lg px-3 py-1.5 text-xs font-medium transition-all border"
            >
              {{ range.label }}
            </button>
          </div>
        </div>
        <div ref="successRateChartRef" class="h-56 w-full"></div>
      </div>

      <div class="rounded-3xl border border-border bg-card p-5">
        <div class="flex items-center justify-between mb-4">
          <p class="text-sm font-medium text-foreground">平均响应时间</p>
          <div class="flex items-center gap-1">
            <button
              v-for="range in timeRanges"
              :key="range.value"
              @click="timeRangeResponseTime = range.value"
              :class="timeRangeResponseTime === range.value
                ? 'bg-accent text-foreground border-primary/50 font-semibold'
                : 'bg-transparent text-muted-foreground hover:bg-accent/50 hover:text-foreground border-border'"
              class="rounded-lg px-3 py-1.5 text-xs font-medium transition-all border"
            >
              {{ range.label }}
            </button>
          </div>
        </div>
        <div ref="responseTimeChartRef" class="h-56 w-full"></div>
      </div>
    </section>

    <section class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div class="rounded-3xl border border-border bg-card p-5">
        <div class="flex items-center justify-between mb-4">
          <p class="text-sm font-medium text-foreground">模型调用占比</p>
          <div class="flex items-center gap-1">
            <button
              v-for="range in timeRanges"
              :key="range.value"
              @click="timeRangeModel = range.value"
              :class="timeRangeModel === range.value
                ? 'bg-accent text-foreground border-primary/50 font-semibold'
                : 'bg-transparent text-muted-foreground hover:bg-accent/50 hover:text-foreground border-border'"
              class="rounded-lg px-3 py-1.5 text-xs font-medium transition-all border"
            >
              {{ range.label }}
            </button>
          </div>
        </div>
        <div ref="modelChartRef" class="h-56 w-full"></div>
      </div>

      <div class="rounded-3xl border border-border bg-card p-5">
        <div class="flex items-center justify-between mb-4">
          <p class="text-sm font-medium text-foreground">模型使用排行</p>
          <div class="flex items-center gap-1">
            <button
              v-for="range in timeRanges"
              :key="range.value"
              @click="timeRangeModelRank = range.value"
              :class="timeRangeModelRank === range.value
                ? 'bg-accent text-foreground border-primary/50 font-semibold'
                : 'bg-transparent text-muted-foreground hover:bg-accent/50 hover:text-foreground border-border'"
              class="rounded-lg px-3 py-1.5 text-xs font-medium transition-all border"
            >
              {{ range.label }}
            </button>
          </div>
        </div>
        <div ref="modelRankChartRef" class="h-56 w-full"></div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Icon } from '@iconify/vue'
import { statsApi } from '@/api'
import {
  getLineChartTheme,
  getPieChartTheme,
  createLineSeries,
  createPieDataItem,
  chartColors,
  getModelColor,
  filterValidModels,
} from '@/lib/chartTheme'

type ChartInstance = {
  setOption: (option: unknown) => void
  resize: () => void
  dispose: () => void
}

// 时间范围选择
const timeRanges = [
  { label: '24小时', value: '24h' },
  { label: '7天', value: '7d' },
  { label: '30天', value: '30d' },
]

// 每个图表独立的时间范围
const timeRangeHourlyRequests = ref('24h')
const timeRangeTrend = ref('24h')
const timeRangeSuccessRate = ref('24h')
const timeRangeModel = ref('24h')
const timeRangeModelRank = ref('24h')
const timeRangeResponseTime = ref('24h')

// 创建图表监听器的工厂函数
function createChartWatcher(chartType: string, updateFn: () => void) {
  return async (newVal: string) => {
    await loadChartData(chartType, newVal)
    updateFn()
  }
}

// 监听各图表时间范围变化 - 只更新对应图表
watch(timeRangeHourlyRequests, createChartWatcher('hourlyRequests', updateHourlyRequestsChart))
watch(timeRangeTrend, createChartWatcher('trend', updateTrendChart))
watch(timeRangeSuccessRate, createChartWatcher('successRate', updateSuccessRateChart))
watch(timeRangeModel, createChartWatcher('model', updateModelChart))
watch(timeRangeModelRank, createChartWatcher('modelRank', updateModelRankChart))
watch(timeRangeResponseTime, createChartWatcher('responseTime', updateResponseTimeChart))

const stats = ref([
  {
    label: '账号总数',
    value: '0',
    caption: '账号池中的总数量',
    icon: 'lucide:database',
    iconBg: 'bg-sky-100',
    iconColor: 'text-sky-600'
  },
  {
    label: '活跃账号',
    value: '0',
    caption: '正常运行中，可随时调用',
    icon: 'lucide:check-circle',
    iconBg: 'bg-emerald-100',
    iconColor: 'text-emerald-600'
  },
  {
    label: '失败账号',
    value: '0',
    caption: '已禁用或过期，需要处理',
    icon: 'lucide:alert-circle',
    iconBg: 'bg-red-100',
    iconColor: 'text-red-600'
  },
  {
    label: '限流账号',
    value: '0',
    caption: '触发限流，正在冷却中',
    icon: 'lucide:clock',
    iconBg: 'bg-amber-100',
    iconColor: 'text-amber-600'
  },
])

// 每个图表独立的数据状态
const chartData = ref({
  hourlyRequests: {
    labels: [] as string[],
    modelRequests: {} as Record<string, number[]>,
  },
  trend: {
    labels: [] as string[],
    totalRequests: [] as number[],
    failedRequests: [] as number[],
    rateLimitedRequests: [] as number[],
    successRequests: [] as number[],
  },
  successRate: {
    labels: [] as string[],
    totalRequests: [] as number[],
    failedRequests: [] as number[],
  },
  model: {
    modelRequests: {} as Record<string, number[]>,
  },
  modelRank: {
    modelRequests: {} as Record<string, number[]>,
  },
  responseTime: {
    labels: [] as string[],
    modelTtfbTimes: {} as Record<string, number[]>,
    modelTotalTimes: {} as Record<string, number[]>,
  },
})

const trendChartRef = ref<HTMLDivElement | null>(null)
const modelChartRef = ref<HTMLDivElement | null>(null)
const successRateChartRef = ref<HTMLDivElement | null>(null)
const hourlyRequestsChartRef = ref<HTMLDivElement | null>(null)
const modelRankChartRef = ref<HTMLDivElement | null>(null)
const responseTimeChartRef = ref<HTMLDivElement | null>(null)

const charts = {
  trend: null as ChartInstance | null,
  model: null as ChartInstance | null,
  successRate: null as ChartInstance | null,
  hourlyRequests: null as ChartInstance | null,
  modelRank: null as ChartInstance | null,
  responseTime: null as ChartInstance | null,
}

function initChart(
  ref: HTMLDivElement | null,
  key: keyof typeof charts,
  updateFn: () => void
) {
  const echarts = (window as any).echarts as { init: (el: HTMLElement) => ChartInstance } | undefined
  if (!echarts || !ref) return
  charts[key] = echarts.init(ref)
  updateFn()
}

onMounted(async () => {
  // 加载账号统计
  await loadAccountStats()

  // 初始化所有图表（使用默认24h数据）
  await Promise.all([
    loadChartData('hourlyRequests', timeRangeHourlyRequests.value),
    loadChartData('trend', timeRangeTrend.value),
    loadChartData('successRate', timeRangeSuccessRate.value),
    loadChartData('model', timeRangeModel.value),
    loadChartData('modelRank', timeRangeModelRank.value),
    loadChartData('responseTime', timeRangeResponseTime.value),
  ])

  initChart(trendChartRef.value, 'trend', updateTrendChart)
  initChart(modelChartRef.value, 'model', updateModelChart)
  initChart(successRateChartRef.value, 'successRate', updateSuccessRateChart)
  initChart(hourlyRequestsChartRef.value, 'hourlyRequests', updateHourlyRequestsChart)
  initChart(modelRankChartRef.value, 'modelRank', updateModelRankChart)
  initChart(responseTimeChartRef.value, 'responseTime', updateResponseTimeChart)
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  Object.values(charts).forEach(chart => chart?.dispose())
})

function updateTrendChart() {
  if (!charts.trend) return

  const theme = getLineChartTheme()

  charts.trend.setOption({
    ...theme,
    xAxis: {
      ...theme.xAxis,
      data: chartData.value.trend.labels,
    },
    series: [
      createLineSeries('成功(总请求)', chartData.value.trend.successRequests, chartColors.primary, {
        areaOpacity: 0.25,
        zIndex: 1,
      }),
      createLineSeries('失败', chartData.value.trend.failedRequests, chartColors.danger, {
        areaOpacity: 0.3,
        zIndex: 2,
      }),
      createLineSeries('限流', chartData.value.trend.rateLimitedRequests, chartColors.warning, {
        areaOpacity: 0.3,
        zIndex: 2,
      }),
    ],
  })
  requestAnimationFrame(() => charts.trend?.resize())
}

function getModelTotals() {
  return Object.entries(chartData.value.model.modelRequests)
    .map(([model, data]) => ({
      model,
      data: createPieDataItem(model, data.reduce((sum, item) => sum + item, 0), getModelColor(model)),
      total: data.reduce((sum, item) => sum + item, 0),
    }))
    .filter(item => item.total > 0)
}

function updateModelChart() {
  if (!charts.model) return

  const isMobile = window.innerWidth < 768
  const theme = getPieChartTheme(isMobile)
  const modelData = getModelTotals().map(item => item.data)

  charts.model.setOption({
    ...theme,
    tooltip: {
      ...theme.tooltip,
      formatter: (params: { name: string; value: number; percent: number }) =>
        `${params.name}: ${params.value} 次 (${params.percent}%)`,
    },
    legend: {
      ...theme.legend,
      data: modelData.map(item => item.name),
    },
    series: [
      {
        ...theme.series,
        center: ['50%', '50%'],
        data: modelData,
      },
    ],
  })
  requestAnimationFrame(() => charts.model?.resize())
}

function handleResize() {
  Object.entries(charts).forEach(([key, chart]) => {
    if (chart) {
      if (key === 'model') {
        updateModelChart()
      } else {
        chart.resize()
      }
    }
  })
}

// 加载账号统计数据
async function loadAccountStats() {
  try {
    const overview = await statsApi.overview('24h')
    stats.value[0].value = (overview.total_accounts ?? 0).toString()
    stats.value[1].value = (overview.active_accounts ?? 0).toString()
    stats.value[2].value = (overview.failed_accounts ?? 0).toString()
    stats.value[3].value = (overview.rate_limited_accounts ?? 0).toString()
  } catch (error) {
    console.error('Failed to load account stats:', error)
  }
}

// 为指定图表加载数据
async function loadChartData(chartType: string, timeRange: string) {
  try {
    const overview = await statsApi.overview(timeRange)
    const trend = overview.trend || {
      labels: [],
      total_requests: [],
      failed_requests: [],
      rate_limited_requests: [],
      model_requests: {},
      model_ttfb_times: {},
      model_total_times: {}
    }

    const failed = trend.failed_requests || []
    const limited = trend.rate_limited_requests || []
    const failureSeries = (trend.total_requests || []).map((_, idx) => (failed[idx] || 0) + (limited[idx] || 0))
    const successSeries = (trend.total_requests || []).map(item => Math.max(item, 0))

    // 根据图表类型更新对应的数据
    switch (chartType) {
      case 'hourlyRequests':
        chartData.value.hourlyRequests.labels = trend.labels || []
        chartData.value.hourlyRequests.modelRequests = filterValidModels(trend.model_requests || {})
        break
      case 'trend':
        chartData.value.trend.labels = trend.labels || []
        chartData.value.trend.totalRequests = trend.total_requests || []
        chartData.value.trend.failedRequests = failed
        chartData.value.trend.rateLimitedRequests = limited
        chartData.value.trend.successRequests = successSeries
        break
      case 'successRate':
        chartData.value.successRate.labels = trend.labels || []
        chartData.value.successRate.totalRequests = trend.total_requests || []
        chartData.value.successRate.failedRequests = failureSeries
        break
      case 'model':
        chartData.value.model.modelRequests = filterValidModels(trend.model_requests || {})
        break
      case 'modelRank':
        chartData.value.modelRank.modelRequests = filterValidModels(trend.model_requests || {})
        break
      case 'responseTime':
        chartData.value.responseTime.labels = trend.labels || []
        chartData.value.responseTime.modelTtfbTimes = filterValidModels(trend.model_ttfb_times || {})
        chartData.value.responseTime.modelTotalTimes = filterValidModels(trend.model_total_times || {})
        break
    }
  } catch (error) {
    console.error(`Failed to load ${chartType} data:`, error)
  }
}


function updateSuccessRateChart() {
  if (!charts.successRate) return

  const theme = getLineChartTheme()
  const successRates = chartData.value.successRate.totalRequests.map((total, idx) => {
    const failure = chartData.value.successRate.failedRequests[idx] || 0
    return total > 0 ? Math.round(((total - failure) / total) * 100) : 100
  })

  charts.successRate.setOption({
    ...theme,
    tooltip: {
      ...theme.tooltip,
      trigger: 'axis',
      formatter: (params: any) => {
        if (!params || params.length === 0) return ''
        const param = params[0]
        return `<div style="font-weight: 600; margin-bottom: 4px;">${param.axisValue}</div>
          <div style="display: flex; justify-content: space-between; gap: 16px; align-items: center;">
            <span>${param.marker} ${param.seriesName}</span>
            <span style="font-weight: 600;">${param.value}%</span>
          </div>`
      },
    },
    grid: {
      ...theme.grid,
      top: 32,
      bottom: 32,
    },
    xAxis: {
      ...theme.xAxis,
      data: chartData.value.successRate.labels,
    },
    yAxis: {
      ...theme.yAxis,
      max: 100,
      axisLabel: {
        ...theme.yAxis.axisLabel,
        formatter: '{value}%',
      },
    },
    series: [
      {
        name: '成功率',
        type: 'line',
        data: successRates,
        smooth: true,
        showSymbol: false,
        lineStyle: {
          width: 3,
        },
        areaStyle: {
          opacity: 0.3,
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: chartColors.success },
              { offset: 1, color: 'rgba(16, 185, 129, 0.1)' },
            ],
          },
        },
        itemStyle: {
          color: chartColors.success,
        },
      },
    ],
  })
  requestAnimationFrame(() => charts.successRate?.resize())
}

function updateHourlyRequestsChart() {
  if (!charts.hourlyRequests) return

  const theme = getLineChartTheme()
  const modelNames = Object.keys(chartData.value.hourlyRequests.modelRequests)

  if (modelNames.length === 0) {
    charts.hourlyRequests.setOption({
      ...theme,
      grid: {
        ...theme.grid,
        top: 32,
        bottom: 32,
      },
      xAxis: {
        ...theme.xAxis,
        data: chartData.value.hourlyRequests.labels,
      },
      yAxis: {
        ...theme.yAxis,
      },
      series: [
        {
          name: '总请求',
          type: 'bar',
          data: [],
          barWidth: '60%',
          itemStyle: {
            color: chartColors.primary,
            borderRadius: [4, 4, 0, 0],
          },
        },
      ],
    })
    requestAnimationFrame(() => charts.hourlyRequests?.resize())
    return
  }

  const series = modelNames.map((modelName, index) => ({
    name: modelName,
    type: 'bar',
    stack: 'total',
    data: chartData.value.hourlyRequests.modelRequests[modelName],
    itemStyle: {
      color: getModelColor(modelName),
      borderRadius: index === modelNames.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0],
    },
  }))

  charts.hourlyRequests.setOption({
    ...theme,
    tooltip: {
      ...theme.tooltip,
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
      },
      formatter: (params: any) => {
        if (!params || params.length === 0) return ''
        let result = `<div style="font-weight: 600; margin-bottom: 4px;">${params[0].axisValue}</div>`
        let total = 0
        params.forEach((item: any) => {
          total += item.value || 0
          result += `<div style="display: flex; justify-content: space-between; gap: 16px; align-items: center;">
            <span>${item.marker} ${item.seriesName}</span>
            <span style="font-weight: 600;">${item.value || 0}</span>
          </div>`
        })
        result += `<div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid #e5e5e5; font-weight: 600;">
          总计: ${total}
        </div>`
        return result
      },
    },
    legend: {
      ...theme.legend,
      data: modelNames,
      top: 0,
      right: 0,
      type: 'scroll',
      pageIconSize: 10,
      pageTextStyle: {
        fontSize: 10,
      },
    },
    grid: {
      ...theme.grid,
      top: modelNames.length > 5 ? 56 : 48,
      bottom: 32,
    },
    xAxis: {
      ...theme.xAxis,
      data: chartData.value.hourlyRequests.labels,
    },
    yAxis: {
      ...theme.yAxis,
    },
    series: series,
  })

  requestAnimationFrame(() => charts.hourlyRequests?.resize())
}

function updateModelRankChart() {
  if (!charts.modelRank) return

  const theme = getLineChartTheme()
  const modelTotals = Object.entries(chartData.value.modelRank.modelRequests)
    .map(([model, data]) => ({
      model,
      total: data.reduce((sum, item) => sum + item, 0),
    }))
    .filter(item => item.total > 0)
    .sort((a, b) => b.total - a.total)

  const modelNames = modelTotals.map(item => item.model)
  const modelValues = modelTotals.map(item => item.total)
  const modelColors = modelNames.map(name => getModelColor(name))

  charts.modelRank.setOption({
    ...theme,
    grid: {
      left: 12,
      right: 60,
      top: 16,
      bottom: 16,
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        ...theme.xAxis.axisLabel,
        fontSize: 10,
      },
      splitLine: {
        lineStyle: {
          color: '#e5e5e5',
          type: 'solid',
        },
      },
    },
    yAxis: {
      type: 'category',
      data: modelNames,
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        ...theme.yAxis.axisLabel,
        fontSize: 11,
      },
    },
    series: [
      {
        type: 'bar',
        data: modelValues.map((value, idx) => ({
          value,
          itemStyle: {
            color: modelColors[idx],
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barWidth: '50%',
        label: {
          show: true,
          position: 'right',
          fontSize: 11,
          color: '#6b6b6b',
          formatter: '{c}',
        },
      },
    ],
  })
  requestAnimationFrame(() => charts.modelRank?.resize())
}

function updateResponseTimeChart() {
  if (!charts.responseTime) return

  const theme = getLineChartTheme()
  const modelNames = Object.keys(chartData.value.responseTime.modelTtfbTimes)

  if (modelNames.length === 0) {
    charts.responseTime.setOption({
      ...theme,
      grid: {
        ...theme.grid,
        top: 32,
        bottom: 32,
      },
      xAxis: {
        ...theme.xAxis,
        data: chartData.value.responseTime.labels,
      },
      yAxis: {
        ...theme.yAxis,
        axisLabel: {
          ...theme.yAxis.axisLabel,
          formatter: '{value}s',
        },
      },
      series: [],
    })
    requestAnimationFrame(() => charts.responseTime?.resize())
    return
  }

  // 构建系列：每个模型两条线（完成实线 + 首响虚线）
  const series: any[] = []
  const legendData: string[] = []

  modelNames.forEach((modelName) => {
    const color = getModelColor(modelName)
    legendData.push(modelName)

    // 将毫秒转换为秒
    const ttfbInSeconds = chartData.value.responseTime.modelTtfbTimes[modelName].map((ms: number) => Number((ms / 1000).toFixed(2)))
    const totalInSeconds = chartData.value.responseTime.modelTotalTimes[modelName].map((ms: number) => Number((ms / 1000).toFixed(2)))

    // 完成时间 - 实线（主线，显示在图例中）
    series.push(
      createLineSeries(modelName, totalInSeconds, color, {
        smooth: true,
        areaOpacity: 0.15,
        zIndex: 2,
      })
    )

    // 首响时间 - 虚线（不显示在图例中，但跟随主线的显示状态）
    const ttfbSeries = createLineSeries(modelName, ttfbInSeconds, color, {
      smooth: true,
      areaOpacity: 0,
      zIndex: 1,
      lineStyle: {
        type: 'dashed',
        width: 2,
      },
    })
    // 修改name以区分，但使用相同的legendName来关联
    ttfbSeries.name = `${modelName}-ttfb`
    series.push(ttfbSeries)
  })

  charts.responseTime.setOption({
    ...theme,
    tooltip: {
      ...theme.tooltip,
      trigger: 'axis',
      formatter: (params: any) => {
        if (!params || params.length === 0) return ''
        let result = `<div style="font-weight: 600; margin-bottom: 4px;">${params[0].axisValue}</div>`

        // 按模型分组显示
        const modelMap = new Map<string, { total?: number, ttfb?: number, color?: string }>()
        params.forEach((item: any) => {
          const seriesName = item.seriesName
          if (seriesName.endsWith('-ttfb')) {
            const modelName = seriesName.replace('-ttfb', '')
            const data = modelMap.get(modelName) || {}
            data.ttfb = item.value
            data.color = item.color
            modelMap.set(modelName, data)
          } else {
            const data = modelMap.get(seriesName) || {}
            data.total = item.value
            data.color = item.color
            modelMap.set(seriesName, data)
          }
        })

        modelMap.forEach((data, modelName) => {
          const marker = `<span style="display:inline-block;margin-right:4px;border-radius:10px;width:10px;height:10px;background-color:${data.color};"></span>`
          result += `<div style="margin-top: 4px;">
            <div style="font-weight: 600; margin-bottom: 2px;">${marker}${modelName}</div>
            <div style="display: flex; justify-content: space-between; gap: 16px; padding-left: 14px;">
              <span style="color: #6b6b6b;">完成时间</span>
              <span style="font-weight: 600;">${data.total || 0}s</span>
            </div>
            <div style="display: flex; justify-content: space-between; gap: 16px; padding-left: 14px;">
              <span style="color: #6b6b6b;">首响时间</span>
              <span style="font-weight: 600;">${data.ttfb || 0}s</span>
            </div>
          </div>`
        })
        return result
      },
    },
    legend: {
      ...theme.legend,
      data: legendData,
      top: 0,
      right: 0,
      type: 'scroll',
      pageIconSize: 10,
      pageTextStyle: {
        fontSize: 10,
      },
      selectedMode: 'multiple',
    },
    grid: {
      ...theme.grid,
      top: modelNames.length > 3 ? 56 : 48,
      bottom: 32,
    },
    xAxis: {
      ...theme.xAxis,
      data: chartData.value.responseTime.labels,
    },
    yAxis: {
      ...theme.yAxis,
      axisLabel: {
        ...theme.yAxis.axisLabel,
        formatter: '{value}s',
      },
    },
    series: series,
  })

  // 监听图例选择事件，同步控制首响时间线的显示/隐藏
  charts.responseTime.off('legendselectchanged')
  charts.responseTime.on('legendselectchanged', (params: any) => {
    const selected = params.selected

    // 遍历所有模型，控制对应的ttfb线
    Object.keys(selected).forEach((modelName) => {
      const ttfbSeriesName = `${modelName}-ttfb`
      const isSelected = selected[modelName]

      // 使用dispatchAction来控制series的显示/隐藏
      charts.responseTime.dispatchAction({
        type: isSelected ? 'legendSelect' : 'legendUnSelect',
        name: ttfbSeriesName,
      })
    })
  })

  requestAnimationFrame(() => charts.responseTime?.resize())
}

</script>
